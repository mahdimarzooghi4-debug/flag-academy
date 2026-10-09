"""Offline Gemma preflight is a secure adapter, not proof of a trained model."""

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.ai_control_plane import local_gemma
from app.ai_control_plane.local_gemma import (
    CheckpointFile,
    ExplicitTextGeneration,
    OfflineGemmaCheckpoint,
    attest_offline_checkpoint,
    attest_registered_offline_checkpoint,
    generate_offline_text,
)
from app.errors import AppError


def checkpoint(tmp_path: Path) -> OfflineGemmaCheckpoint:
    root = tmp_path / "private-gemma-checkpoint"
    root.mkdir()
    # Test bytes are not genuine model weights; this verifies attestation only.
    files = {
        "config.json": b'{"model_type":"gemma4_unified"}',
        "tokenizer.json": b'{"version":"1.0"}',
        "weights/model.safetensors": b"fixture-not-real-model-weights",
    }
    manifest = []
    for name, data in files.items():
        local = root / name
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(data)
        manifest.append(CheckpointFile(name, sha256(data).hexdigest(), len(data)))
    return OfflineGemmaCheckpoint(
        model_version_id=UUID(int=101),
        training_dataset_version_id=UUID(int=202),
        model_family="Gemma 4 12B Unified",
        checkpoint_revision="a" * 40,
        checkpoint_directory=str(root),
        files=tuple(manifest),
    )


def denial(checkpoint_value: OfflineGemmaCheckpoint) -> None:
    with pytest.raises(AppError) as exc:
        attest_offline_checkpoint(checkpoint_value)
    assert exc.value.code == "AI_LOCAL_CHECKPOINT_NOT_VERIFIED"
    assert exc.value.status_code == 409


def test_attested_checkpoint_binds_manifest_model_version_and_training_lineage(tmp_path):
    item = checkpoint(tmp_path)
    first = attest_offline_checkpoint(item)
    assert first.checkpoint.model_version_id == UUID(int=101)
    assert first.checkpoint.training_dataset_version_id == UUID(int=202)
    assert len(first.content_manifest_sha256) == 64
    assert first == attest_offline_checkpoint(item)
    changed_revision = replace(item, checkpoint_revision="b" * 40)
    assert attest_offline_checkpoint(changed_revision).content_manifest_sha256 != first.content_manifest_sha256


def test_invalid_model_revision_or_lineage_fails_closed(tmp_path):
    item = checkpoint(tmp_path)
    denial(replace(item, model_family="different-family"))
    denial(replace(item, checkpoint_revision="main"))
    denial(replace(item, model_version_id=UUID(int=0)))
    denial(replace(item, training_dataset_version_id=UUID(int=0)))
    denial(replace(item, checkpoint_directory="."))
    denial(replace(item, checkpoint_directory="/"))
    denial(replace(item, files=()))


def test_checkpoint_rejects_modified_missing_extra_or_unattested_weights(tmp_path):
    item = checkpoint(tmp_path)
    root = Path(item.checkpoint_directory)
    (root / "config.json").write_bytes(b"tampered")
    denial(item)
    (root / "config.json").write_bytes(b'{"model_type":"gemma4_unified"}')
    (root / "new-config.json").write_text("{}")
    denial(item)
    (root / "new-config.json").unlink()
    (root / "weights/model.safetensors").unlink()
    denial(item)


def test_manifest_rejects_path_escape_duplicate_and_unsafe_formats(tmp_path):
    item = checkpoint(tmp_path)
    first = item.files[0]
    denial(replace(item, files=item.files + (first,)))
    denial(replace(item, files=(replace(first, path="../steal"),) + item.files[1:]))
    denial(replace(item, files=(replace(first, path="/tmp/x"),) + item.files[1:]))
    denial(replace(item, files=(replace(first, sha256="NOTSHA"),) + item.files[1:]))
    denial(replace(item, files=(replace(first, byte_size=-1),) + item.files[1:]))
    denial(replace(item, files=(replace(first, path="script.py"),) + item.files[1:]))


def test_private_checkpoint_symlink_is_forbidden(tmp_path):
    item = checkpoint(tmp_path)
    root = Path(item.checkpoint_directory)
    (root / "shortcut").symlink_to(root / "config.json")
    denial(item)


class FakeBackend:
    def __init__(self, answer: str = "پاسخ آزمایشی"):
        self.calls: list[tuple[str, ExplicitTextGeneration]] = []
        self.answer = answer

    def generate(self, prompt: str, policy: ExplicitTextGeneration) -> str:
        self.calls.append((prompt, policy))
        return self.answer


def test_explicit_local_generation_only_after_attestation(tmp_path):
    item = checkpoint(tmp_path)
    backend = FakeBackend()
    policy = ExplicitTextGeneration(max_new_tokens=8, do_sample=False)
    assert generate_offline_text(
        checkpoint=item, prompt="تصمیم را توضیح بده", policy=policy, backend=backend
    ) == "پاسخ آزمایشی"
    assert backend.calls == [("تصمیم را توضیح بده", policy)]
    Path(item.checkpoint_directory, "config.json").write_text("tampered after first use")
    with pytest.raises(AppError) as exc:
        generate_offline_text(checkpoint=item, prompt="سلام", policy=policy, backend=backend)
    assert exc.value.code == "AI_LOCAL_CHECKPOINT_NOT_VERIFIED"
    assert len(backend.calls) == 1


def test_invalid_prompt_limits_missing_backend_and_empty_output_fail_closed(tmp_path):
    item = checkpoint(tmp_path)
    policy = ExplicitTextGeneration(max_new_tokens=8, do_sample=False)
    backend = FakeBackend()
    for prompt, generation_policy in [
        ("", policy), ("hello", ExplicitTextGeneration(0, False)),
        ("hello", ExplicitTextGeneration(-1, False)),
    ]:
        with pytest.raises(AppError) as exc:
            generate_offline_text(
                checkpoint=item, prompt=prompt, policy=generation_policy, backend=backend
            )
        assert exc.value.code == "AI_LOCAL_INPUT_INVALID"
    assert not backend.calls
    with pytest.raises(AppError) as exc:
        generate_offline_text(checkpoint=item, prompt="hello", policy=policy)
    assert exc.value.code == "AI_LOCAL_CHECKPOINT_NOT_VERIFIED"
    with pytest.raises(AppError) as exc:
        generate_offline_text(
            checkpoint=item, prompt="hello", policy=policy, backend=FakeBackend(" ")
        )
    assert exc.value.code == "AI_LOCAL_GENERATION_FAILED"


def test_no_public_inference_or_training_api_was_added():
    from app.main import app

    assert not any(
        "gemma" in path or "/inference" in path or "/generate" in path
        for path in app.openapi()["paths"]
    )
    adapter_source = Path("app/ai_control_plane/local_gemma.py").read_text()
    assert "local_files_only=True" in adapter_source
    assert "trust_remote_code=False" in adapter_source
    assert "use_safetensors=True" in adapter_source
    assert 'import_module("transformers")' in adapter_source
    assert "AutoModelForMultimodalLM" in adapter_source
    assert "https://" not in adapter_source
    assert "train(" not in adapter_source



def registered_fixture(tmp_path: Path):
    checkpoint_value = checkpoint(tmp_path)
    manifest_path = tmp_path / "registered-gemma-manifest.json"
    records = {
        "schema_version": 1,
        "training_run_id": str(UUID(int=303)),
        "training_dataset_version_id": str(checkpoint_value.training_dataset_version_id),
        "model_family": checkpoint_value.model_family,
        "checkpoint_revision": checkpoint_value.checkpoint_revision,
        "files": [
            {"path": f.path, "sha256": f.sha256, "byte_size": f.byte_size}
            for f in checkpoint_value.files
        ],
    }
    raw = json.dumps(records, sort_keys=True).encode("utf-8")
    manifest_path.write_bytes(raw)
    run = SimpleNamespace(
        id=UUID(int=303),
        dataset_version_id=checkpoint_value.training_dataset_version_id,
        model_family=checkpoint_value.model_family,
    )
    artifact = SimpleNamespace(
        id=UUID(int=404),
        training_run_id=run.id,
        artifact_format="GEMMA4_CHECKPOINT_MANIFEST_V1",
        artifact_reference=str(manifest_path),
        content_sha256=sha256(raw).hexdigest(),
        byte_size=len(raw),
    )
    version = SimpleNamespace(
        id=checkpoint_value.model_version_id,
        model_artifact_id=artifact.id,
        training_run_id=run.id,
        dataset_version_id=run.dataset_version_id,
        model_family=checkpoint_value.model_family,
        attestation_sha256=artifact.content_sha256,
        attestation_byte_size=artifact.byte_size,
    )
    return checkpoint_value, version, artifact, run, records, manifest_path


def assert_registry_denied(*, version, artifact, run, checkpoint_directory):
    with pytest.raises(AppError) as error:
        local_gemma._checkpoint_from_registered_artifact(
            version=version,
            artifact=artifact,
            run=run,
            checkpoint_directory=checkpoint_directory,
        )
    assert error.value.code == "AI_LOCAL_REGISTRY_ARTIFACT_NOT_VERIFIED"


def test_registered_manifest_binds_registry_and_checkpoint(tmp_path):
    source, version, artifact, run, _, _ = registered_fixture(tmp_path)
    resolved = _checkpoint_from_registered_artifact(
        version=version,
        artifact=artifact,
        run=run,
        checkpoint_directory=source.checkpoint_directory,
    )
    assert resolved == source
    assert attest_offline_checkpoint(resolved).checkpoint == source


def test_registered_manifest_rejects_substitution_and_tampering(tmp_path):
    source, version, artifact, run, document, path = registered_fixture(tmp_path)
    kwargs = {
        "version": version,
        "artifact": artifact,
        "run": run,
        "checkpoint_directory": source.checkpoint_directory,
    }
    assert_registry_denied(**{**kwargs, "artifact": SimpleNamespace(
        **{**vars(artifact), "artifact_format": "safetensors"}
    )})
    assert_registry_denied(**{**kwargs, "version": SimpleNamespace(
        **{**vars(version), "attestation_sha256": "0" * 64}
    )})
    assert_registry_denied(**{**kwargs, "run": SimpleNamespace(
        **{**vars(run), "dataset_version_id": UUID(int=909)}
    )})
    path.write_text(json.dumps({**document, "files": []}))
    assert_registry_denied(**kwargs)
    path.write_text(json.dumps(document))
    assert_registry_denied(**kwargs)
    path.unlink()
    path.symlink_to(Path(source.checkpoint_directory) / "config.json")
    assert_registry_denied(**kwargs)


def test_registered_manifest_strict_schema_and_duplicates(tmp_path):
    source, version, artifact, run, document, path = registered_fixture(tmp_path)

    def rejected(contents: bytes) -> None:
        path.write_bytes(contents)
        changed_artifact = SimpleNamespace(
            **{**vars(artifact), "content_sha256": sha256(contents).hexdigest(),
               "byte_size": len(contents)}
        )
        changed_version = SimpleNamespace(
            **{**vars(version), "attestation_sha256": changed_artifact.content_sha256,
               "attestation_byte_size": len(contents)}
        )
        assert_registry_denied(
            version=changed_version, artifact=changed_artifact, run=run,
            checkpoint_directory=source.checkpoint_directory,
        )

    rejected(b'{"schema_version":1,"schema_version":1}')
    rejected(json.dumps({**document, "unexpected": "x"}).encode())
    rejected(json.dumps({**document, "schema_version": True}).encode())
    rejected(json.dumps({**document, "training_run_id": str(UUID(int=1))}).encode())
    rejected(json.dumps({**document, "checkpoint_revision": "main"}).encode())
    rejected(json.dumps({**document, "files": [
        {**document["files"][0], "byte_size": True}
    ]}).encode())
    rejected(b"not-json")


class _QueryResult:
    def __init__(self, row):
        self.row = row

    def one_or_none(self):
        return self.row

    def scalar_one_or_none(self):
        return self.row


class _RegistryDB:
    def __init__(self, lineage, state):
        self.lineage = lineage
        self.state = state
        self.calls = 0

    async def execute(self, query):
        self.calls += 1
        return _QueryResult(self.lineage if self.calls == 1 else self.state)


@pytest.mark.asyncio
async def test_registry_preflight_requires_scoped_version_and_succeeded_run(tmp_path):
    source, version, artifact, run, _, _ = registered_fixture(tmp_path)
    kwargs = {
        "organization_context_id": UUID(int=505),
        "model_version_id": version.id,
        "checkpoint_directory": source.checkpoint_directory,
    }
    approved = _RegistryDB((version, artifact, run), SimpleNamespace(state="SUCCEEDED"))
    result = await attest_registered_offline_checkpoint(approved, **kwargs)
    assert result.checkpoint == source
    assert approved.calls == 2
    for db in [
        _RegistryDB(None, None),
        _RegistryDB((version, artifact, run), None),
        _RegistryDB((version, artifact, run), SimpleNamespace(state="REQUESTED")),
        _RegistryDB((version, artifact, run), SimpleNamespace(state="FAILED")),
    ]:
        with pytest.raises(AppError) as error:
            await attest_registered_offline_checkpoint(db, **kwargs)
        assert error.value.code == "AI_LOCAL_REGISTRY_ARTIFACT_NOT_VERIFIED"
    source_text = Path("app/ai_control_plane/local_gemma.py").read_text()
    assert "AIDataset.organization_context_id == organization_context_id" in source_text
    assert "AITrainingRun.organization_context_id == organization_context_id" in source_text
    assert "AIModelVersion.id == model_version_id" in source_text


def test_registry_bridge_read_only_no_public_inference():
    from app.main import app

    assert not any("gemma" in route for route in app.openapi()["paths"])
    source_text = Path("app/ai_control_plane/local_gemma.py").read_text()
    assert "await db.commit()" not in source_text
    assert "record_event(" not in source_text
    assert "httpx" not in source_text
