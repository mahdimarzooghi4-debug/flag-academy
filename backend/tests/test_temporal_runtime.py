import subprocess
import sys


def test_temporal_activity_process_loads_cross_domain_model_registry() -> None:
    script = """
from app.db import Base
from app.mission_runtime import temporal_activities  # noqa: F401
required = {
    "mission_design.mission_versions",
    "mission_runtime.mission_instances",
    "mission_runtime.scheduled_effects",
}
missing = required.difference(Base.metadata.tables)
raise SystemExit(1 if missing else 0)
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
