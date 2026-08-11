from modules.hazard import HazardEngine, HazardLevel
from modules.models import Detection, TrackedActor


def actor(
    track_id: int,
    *,
    distance: float,
    velocity: float,
    lateral: float = 0.0,
    lateral_velocity: float = 0.0,
) -> TrackedActor:
    detection = Detection(
        track_id=track_id,
        bbox=(10, 10, 50, 50),
        class_id=2,
        class_name="Car",
        confidence=0.9,
        bottom_center=(30, 50),
    )
    return TrackedActor(
        track_id=track_id,
        detection=detection,
        distance_m=distance,
        lateral_distance_m=lateral,
        velocity_mps=velocity,
        velocity_kmh=velocity * 3.6,
        lateral_velocity_mps=lateral_velocity,
        lateral_velocity_kmh=lateral_velocity * 3.6,
        bev_position=(lateral, distance),
    )


def test_ttc_thresholds_apply_to_actors_in_the_ego_lane():
    engine = HazardEngine(ttc_red=2.5, ttc_yellow=4.0)
    assessments = engine.assess(
        [
            actor(1, distance=5.0, velocity=-2.0),
            actor(2, distance=7.0, velocity=-2.0),
            actor(3, distance=10.0, velocity=-2.0),
        ]
    )

    assert [item.hazard_level for item in assessments] == [
        HazardLevel.CRITICAL,
        HazardLevel.WARNING,
        HazardLevel.SAFE,
    ]
    assert [item.ttc for item in assessments] == [2.5, 3.5, 5.0]


def test_low_ttc_outside_the_path_is_not_escalated():
    assessment = HazardEngine().assess(
        [actor(1, distance=4.0, velocity=-2.0, lateral=4.5)]
    )[0]

    assert assessment.ttc == 2.0
    assert assessment.hazard_level is HazardLevel.SAFE


def test_nearby_lateral_cut_in_creates_a_warning():
    assessment = HazardEngine().assess(
        [
            actor(
                1,
                distance=10.0,
                velocity=0.0,
                lateral=-3.0,
                lateral_velocity=4.5,
            )
        ]
    )[0]

    assert assessment.is_cutin is True
    assert assessment.cutin_direction == "RIGHT"
    assert assessment.hazard_level is HazardLevel.WARNING


def test_most_critical_uses_the_lowest_computed_ttc():
    assessments = HazardEngine().assess(
        [actor(1, distance=9.0, velocity=-2.0), actor(2, distance=4.0, velocity=-2.0)]
    )

    assert HazardEngine.get_most_critical(assessments).actor.track_id == 2
