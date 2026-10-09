"""Offline Gemma preflight is a secure adapter, not proof of a trained model."""

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest

from app.ai_control_plane.local_gemma import (
    CheckpointFile,
    ExplicitTextGeneration,
    OfflineGemmaCheckpoint,
    attest_offline_checkpoint,
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
