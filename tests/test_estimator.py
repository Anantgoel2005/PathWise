import pytest

from modules.estimator import VelocityEstimator
from modules.models import Detection


class FakePerspective:
    ego_bev = (0.0, 100.0)

    @staticmethod
    def transform_point(x: float, y: float) -> tuple[float, float]:
        return float(x), float(y)

    @staticmethod
    def pixel_distance_to_meters(distance: float) -> float:
        return distance / 10.0


def detection(track_id: int, x: int, y: int) -> Detection:
    return Detection(
        track_id=track_id,
        bbox=(x - 10, y - 20, x + 10, y),
        class_id=2,
        class_name="Car",
        confidence=0.95,
        bottom_center=(x, y),
    )


def test_velocity_estimator_uses_track_history_and_prunes_stale_tracks():
    estimator = VelocityEstimator(FakePerspective(), buffer_size=4)

    first = estimator.update([detection(5, 0, 80)], timestamp=10.0)[0]
    second = estimator.update([detection(5, 10, 90)], timestamp=11.0)[0]

    assert first.distance_m == pytest.approx(2.0)
    assert first.velocity_mps == 0.0
    assert second.distance_m == pytest.approx(1.0)
    assert second.velocity_mps == pytest.approx(-1.0)
    assert second.lateral_velocity_mps == pytest.approx(1.0)
    assert estimator.active_track_count == 1

    assert estimator.update([], timestamp=12.0) == []
    assert estimator.active_track_count == 0
    assert 5 not in estimator._buffers
