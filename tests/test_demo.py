import json

from demo import run_demo


def test_demo_produces_deterministic_metrics_and_telemetry(tmp_path):
    metrics = run_demo(tmp_path, frames=210, fps=30, write_video=False)

    assert metrics["scenario"] == "deterministic-synthetic-v1"
    assert metrics["actor_samples"] == 630
    assert metrics["cut_in_frames"] > 0
    assert metrics["frames_with_level"]["CRITICAL"] > 0
    assert metrics["minimum_ttc_seconds"] <= 2.5
    assert metrics["video"] is None
    assert (tmp_path / "telemetry.csv").is_file()
    assert json.loads((tmp_path / "metrics.json").read_text())["frames"] == 210
