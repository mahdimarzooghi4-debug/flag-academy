"""Off-network Gemma 4 12B checkpoint preflight and internal text execution.

This is an offline *low-level* adapter, not an approved Production runtime.
No public API, model promotion, GPU sizing, downloading, or training occurs here.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Never, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_control_plane.domain import TrainingRunState
from app.ai_control_plane.models import (
    AIDataset,
    AIDatasetVersion,
    AIModelArtifact,
    AIModelVersion,
    AITrainingRun,
    AITrainingRunState,
)
from app.errors import AppError

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_BLOCKED_SUFFIXES = {".py", ".sh", ".bin", ".pt", ".pth", ".pkl", ".pickle", ".so", ".dll", ".dylib", ".exe"}
_MODEL_FAMILY = "Gemma 4 12B Unified"


def _deny(reason: str) -> Never:
    raise AppError("AI_LOCAL_CHECKPOINT_NOT_VERIFIED", reason, status_code=409)


@dataclass(frozen=True)
class CheckpointFile:
    """Pinned digest supplied from separately trusted, versioned infrastructure evidence."""

    path: str
    sha256: str
    byte_size: int


@dataclass(frozen=True)
class OfflineGemmaCheckpoint:
    model_version_id: UUID
    training_dataset_version_id: UUID
    model_family: str
    checkpoint_revision: str
    checkpoint_directory: str
    files: tuple[CheckpointFile, ...]


@dataclass(frozen=True)
class AttestedGemmaCheckpoint:
    """Result is process-local; it is NOT a model-promotion or runtime authorization."""

    checkpoint: OfflineGemmaCheckpoint
    content_manifest_sha256: str


def attest_offline_checkpoint(checkpoint: OfflineGemmaCheckpoint) -> AttestedGemmaCheckpoint:
    """Verify every byte on a private checkpoint mount without fetching any files."""
    if checkpoint.model_family != _MODEL_FAMILY:
        _deny("The checkpoint model family is not the approved Gemma 4 12B Unified baseline.")
    if checkpoint.model_version_id.int == 0 or checkpoint.training_dataset_version_id.int == 0:
        _deny("Model and training dataset version lineage must be explicit.")
    if not _REVISION.fullmatch(checkpoint.checkpoint_revision):
        _deny("A pinned 40-character checkpoint revision is required.")

    root = Path(checkpoint.checkpoint_directory)
    if not root.is_absolute() or root == Path("/") or root.is_symlink() or not root.is_dir():
        _deny("Checkpoint must be a non-root, absolute, existing private directory.")
    if root.resolve(strict=True) != root:
        _deny("Checkpoint directory cannot traverse symlinks or use noncanonical paths.")
    if not checkpoint.files:
        _deny("A manifest with exact pinned content digests is required.")

    manifest: dict[str, CheckpointFile] = {}
    for item in checkpoint.files:
        candidate = Path(item.path)
        if (
            not item.path or candidate.is_absolute() or ".." in candidate.parts
            or "." in candidate.parts or candidate.as_posix() != item.path
            or item.path in manifest or any(part.startswith(".") for part in candidate.parts)
            or candidate.suffix.lower() in _BLOCKED_SUFFIXES
            or not _SHA256.fullmatch(item.sha256) or item.byte_size < 0
        ):
            _deny("Checkpoint manifest contains an invalid, duplicate or unsafe file.")
        manifest[item.path] = item

    if "config.json" not in manifest or not any(
        name.endswith(".safetensors") for name in manifest
    ):
        _deny("An attested config.json and safetensors weight file are required.")
    if not ({"tokenizer.json", "tokenizer.model"} & manifest.keys()):
        _deny("An attested local tokenizer is required.")

    observed: set[str] = set()
    for path in root.rglob("*"):
        # Never follow a link outside the private, read-only artifact boundary.
        if path.is_symlink():
            _deny("Symlinks are forbidden inside the checkpoint.")
        if path.is_dir():
            continue
        if not path.is_file():
            _deny("Non-regular files are forbidden inside the checkpoint.")
        name = path.relative_to(root).as_posix()
        observed.add(name)
        if name not in manifest:
            _deny("Unattested checkpoint files are forbidden.")
        stat_before = path.stat()
        if stat_before.st_size != manifest[name].byte_size:
            _deny("Checkpoint byte size does not match the pinned manifest.")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        stat_after = path.stat()
        if (
            (stat_after.st_dev, stat_after.st_ino, stat_after.st_size, stat_after.st_mtime_ns)
            != (stat_before.st_dev, stat_before.st_ino, stat_before.st_size, stat_before.st_mtime_ns)
            or digest.hexdigest() != manifest[name].sha256
        ):
            _deny("Checkpoint bytes changed or did not match the manifest.")
    if observed != manifest.keys():
        _deny("Checkpoint manifest references files that do not exist.")

    manifest_digest = hashlib.sha256()
    manifest_digest.update(checkpoint.checkpoint_revision.encode("ascii"))
    for name in sorted(manifest):
        record = manifest[name]
        manifest_digest.update(
            f"\n{name}\0{record.sha256}\0{record.byte_size}".encode()
        )
    return AttestedGemmaCheckpoint(checkpoint, manifest_digest.hexdigest())


@dataclass(frozen=True)
class ExplicitTextGeneration:
    """Caller must supply reviewed resource/generation limits; no invented defaults."""

    max_new_tokens: int
    do_sample: bool


class LocalTextBackend(Protocol):
    def generate(self, prompt: str, policy: ExplicitTextGeneration) -> str: ...


class TransformersLocalGemmaBackend:
    """Loads the Gemma 4 unified checkpoint locally, with no remote code or network."""

    def __init__(self, attestation: AttestedGemmaCheckpoint, *, device_map: str) -> None:
        if not device_map.strip():
            _deny("A deployment-benchmarked device map is required.")
        # Optional GPU dependencies are intentionally not part of default API/CI packages.
        try:
            transformers = import_module("transformers")
            model_class = transformers.AutoModelForMultimodalLM
            processor_class = transformers.AutoProcessor
        except (ImportError, AttributeError) as exc:
            raise AppError(
                "AI_LOCAL_RUNTIME_UNAVAILABLE",
                "Local Gemma runtime dependencies are not installed.",
                status_code=503,
            ) from exc
        path = attestation.checkpoint.checkpoint_directory
        self.processor: Any = processor_class.from_pretrained(
            path, local_files_only=True, trust_remote_code=False,
        )
        self.model: Any = model_class.from_pretrained(
            path, local_files_only=True, trust_remote_code=False,
            use_safetensors=True, device_map=device_map,
        )
        self.model.eval()

    def generate(self, prompt: str, policy: ExplicitTextGeneration) -> str:
        try:
            torch = import_module("torch")
        except ImportError as exc:
            raise AppError(
                "AI_LOCAL_RUNTIME_UNAVAILABLE",
                "The internal torch runtime is unavailable.",
                status_code=503,
            ) from exc
        inputs = self.processor.apply_chat_template(
            [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.model.device)
        with torch.inference_mode():
            generated = self.model.generate(
                **inputs, max_new_tokens=policy.max_new_tokens,
                do_sample=policy.do_sample,
            )
        prompt_tokens = inputs["input_ids"].shape[-1]
        return str(self.processor.decode(generated[0][prompt_tokens:], skip_special_tokens=True))


def generate_offline_text(
    *,
    checkpoint: OfflineGemmaCheckpoint,
    prompt: str,
    policy: ExplicitTextGeneration,
    backend: LocalTextBackend | None = None,
    device_map: str | None = None,
) -> str:
    """No public endpoint. No external API. No model invocation without fresh attestation.

    Supplying a test backend is supported for offline contract testing only.
    Caller-owned higher-level role, mode and purpose authorization must be designed
    and added before this can be exposed as an end-user AI capability.
    """
    if not prompt.strip():
        raise AppError("AI_LOCAL_INPUT_INVALID", "Prompt is required.", status_code=422)
    if policy.max_new_tokens <= 0 or type(policy.max_new_tokens) is not int:
        raise AppError(
            "AI_LOCAL_INPUT_INVALID",
            "An explicit positive max_new_tokens is required.",
            status_code=422,
        )
    attestation = attest_offline_checkpoint(checkpoint)
    if backend is None:
        if device_map is None:
            _deny("A benchmarked device map and local runtime are required.")
        backend = TransformersLocalGemmaBackend(attestation, device_map=device_map)
    result = backend.generate(prompt, policy)
    if not isinstance(result, str) or not result.strip():
        raise AppError(
            "AI_LOCAL_GENERATION_FAILED",
            "Internal model returned no usable text.",
            status_code=503,
        )
    return result


# V1 contract for the already-versioned ModelArtifact, not a second registry.
_REGISTERED_MANIFEST_FORMAT = "GEMMA4_CHECKPOINT_MANIFEST_V1"
_REGISTERED_MANIFEST_MAX_BYTES = 1024 * 1024
_REGISTERED_MANIFEST_MAX_FILES = 4096


def _registry_deny(reason: str) -> Never:
    raise AppError(
        "AI_LOCAL_REGISTRY_ARTIFACT_NOT_VERIFIED", reason, status_code=409
    )


def _unique_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            _registry_deny("Duplicate JSON keys are forbidden in registered manifests.")
        obj[key] = value
    return obj


def _checkpoint_from_registered_artifact(
    *,
    version: AIModelVersion,
    artifact: AIModelArtifact,
    run: AITrainingRun,
    checkpoint_directory: str,
) -> OfflineGemmaCheckpoint:
    """Read verified ModelVersion artifact bytes; mount path comes from the host."""
    if (
        artifact.artifact_format != _REGISTERED_MANIFEST_FORMAT
        or version.model_artifact_id != artifact.id
        or version.training_run_id != run.id
        or artifact.training_run_id != run.id
        or version.dataset_version_id != run.dataset_version_id
        or version.model_family != run.model_family
        or version.model_family != _MODEL_FAMILY
        or version.attestation_sha256 != artifact.content_sha256
        or version.attestation_byte_size != artifact.byte_size
    ):
        _registry_deny("Registry model, artifact and Training Run lineage are inconsistent.")
    if (
        not _SHA256.fullmatch(artifact.content_sha256)
        or artifact.byte_size <= 0
        or artifact.byte_size > _REGISTERED_MANIFEST_MAX_BYTES
    ):
        _registry_deny("Registered manifest attestation metadata is invalid.")

    path = Path(artifact.artifact_reference)
    try:
        if (
            "://" in artifact.artifact_reference
            or not path.is_absolute()
            or path == Path("/")
            or path.is_symlink()
            or path.resolve(strict=True) != path
            or not path.is_file()
        ):
            _registry_deny("Registered artifact must be a canonical local regular file.")
        before = path.stat()
        if before.st_size != artifact.byte_size:
            _registry_deny("Registered artifact byte size differs from the registry.")
        with path.open("rb") as stream:
            raw = stream.read(_REGISTERED_MANIFEST_MAX_BYTES + 1)
        after = path.stat()
    except OSError as exc:
        raise AppError(
            "AI_LOCAL_REGISTRY_ARTIFACT_NOT_VERIFIED",
            "Registered manifest is unavailable on its private mount.",
            status_code=409,
        ) from exc
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_size != after.st_size
        or len(raw) != artifact.byte_size
        or hashlib.sha256(raw).hexdigest() != artifact.content_sha256
    ):
        _registry_deny("Registered manifest bytes changed or failed SHA-256 attestation.")
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AppError(
            "AI_LOCAL_REGISTRY_ARTIFACT_NOT_VERIFIED",
            "Registered manifest must be valid UTF-8 JSON.",
            status_code=409,
        ) from exc

    required = {
        "schema_version",
        "training_run_id",
        "training_dataset_version_id",
        "model_family",
        "checkpoint_revision",
        "files",
    }
    if not isinstance(document, dict) or set(document) != required:
        _registry_deny("Registered manifest has missing or unknown schema fields.")
    if (
        type(document["schema_version"]) is not int
        or document["schema_version"] != 1
        or document["training_run_id"] != str(run.id)
        or document["training_dataset_version_id"] != str(run.dataset_version_id)
        or document["model_family"] != _MODEL_FAMILY
        or not isinstance(document["checkpoint_revision"], str)
        or not _REVISION.fullmatch(document["checkpoint_revision"])
    ):
        _registry_deny("Manifest schema, checkpoint revision or dataset lineage differs.")
    records = document["files"]
    if (
        not isinstance(records, list)
        or not records
        or len(records) > _REGISTERED_MANIFEST_MAX_FILES
    ):
        _registry_deny("Registered checkpoint file list is absent or too large.")
    files: list[CheckpointFile] = []
    for record in records:
        if (
            not isinstance(record, dict)
            or set(record) != {"path", "sha256", "byte_size"}
            or not isinstance(record["path"], str)
            or not isinstance(record["sha256"], str)
            or type(record["byte_size"]) is not int
        ):
            _registry_deny("Registered checkpoint file entry has an invalid schema.")
        files.append(CheckpointFile(**record))
    return OfflineGemmaCheckpoint(
        model_version_id=version.id,
        training_dataset_version_id=run.dataset_version_id,
        model_family=version.model_family,
        checkpoint_revision=document["checkpoint_revision"],
        checkpoint_directory=checkpoint_directory,
        files=tuple(files),
    )


async def attest_registered_offline_checkpoint(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    model_version_id: UUID,
    checkpoint_directory: str,
) -> AttestedGemmaCheckpoint:
    """Read-only tenant-scoped preflight, NEVER inference or Production admission."""
    lineage = (
        await db.execute(
            select(AIModelVersion, AIModelArtifact, AITrainingRun)
            .join(
                AIModelArtifact,
                AIModelArtifact.id == AIModelVersion.model_artifact_id,
            )
            .join(
                AITrainingRun,
                AITrainingRun.id == AIModelVersion.training_run_id,
            )
            .join(
                AIDatasetVersion,
                AIDatasetVersion.id == AIModelVersion.dataset_version_id,
            )
            .join(
                AIDataset,
                AIDataset.id == AIDatasetVersion.dataset_id,
            )
            .where(
                AIModelVersion.id == model_version_id,
                AITrainingRun.organization_context_id == organization_context_id,
                AIDataset.organization_context_id == organization_context_id,
                AIModelArtifact.training_run_id == AITrainingRun.id,
                AITrainingRun.dataset_version_id == AIModelVersion.dataset_version_id,
            )
        )
    ).one_or_none()
    if lineage is None:
        _registry_deny("A registered Model Version was not found for this organization.")
    version, artifact, run = lineage
    latest_state = (
        await db.execute(
            select(AITrainingRunState)
            .where(AITrainingRunState.training_run_id == run.id)
            .order_by(AITrainingRunState.sequence.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest_state is None or latest_state.state != TrainingRunState.SUCCEEDED.value:
        _registry_deny("Only a SUCCEEDED Training Run can provide a Gemma checkpoint.")
    checkpoint = await asyncio.to_thread(
        _checkpoint_from_registered_artifact,
        version=version,
        artifact=artifact,
        run=run,
        checkpoint_directory=checkpoint_directory,
    )
    return await asyncio.to_thread(attest_offline_checkpoint, checkpoint)
