"""Off-network Gemma 4 12B checkpoint preflight and internal text execution.

This is an offline *low-level* adapter, not an approved Production runtime.
No public API, model promotion, GPU sizing, downloading, or training occurs here.
"""

from __future__ import annotations

import hashlib
import re
from importlib import import_module
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Never, Protocol
from uuid import UUID

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
