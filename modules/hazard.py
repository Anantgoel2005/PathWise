"""
PathWise — Hazard Assessment Module
Computes Time-to-Collision (TTC) and detects lateral cut-in maneuvers.
"""

from dataclasses import dataclass
from enum import Enum

import config
from modules.models import TrackedActor


class HazardLevel(Enum):
    CRITICAL = "CRITICAL"  # TTC ≤ 2.5s — RED
    WARNING = "WARNING"  # 2.5s < TTC ≤ 4.0s — YELLOW
    SAFE = "SAFE"  # TTC > 4.0s or not approaching — GREEN


# BGR colors for OpenCV
HAZARD_COLORS = {
    HazardLevel.CRITICAL: (0, 0, 255),  # Red
    HazardLevel.WARNING: (0, 200, 255),  # Yellow-orange
    HazardLevel.SAFE: (0, 220, 100),  # Green
}


@dataclass
class HazardAssessment:
    """Complete hazard assessment for a single tracked actor."""

    actor: TrackedActor
    ttc: float | None  # Time-to-Collision in seconds (None if diverging)
    hazard_level: HazardLevel
    bbox_color: tuple  # BGR color for overlay
    is_cutin: bool  # True if lateral velocity exceeds threshold
    cutin_direction: str | None  # "LEFT" or "RIGHT" if cut-in detected


class HazardEngine:
    """
    Evaluates hazard risk for each tracked actor.

    Computes:
        - TTC = Distance / |Relative Velocity| (only when approaching)
        - Cut-in detection based on lateral velocity threshold
    """

    def __init__(
        self,
        ttc_red: float = config.TTC_RED_THRESHOLD,
        ttc_yellow: float = config.TTC_YELLOW_THRESHOLD,
        lateral_threshold: float = config.LATERAL_CUTIN_THRESHOLD,
    ):
        self.ttc_red = ttc_red
        self.ttc_yellow = ttc_yellow
        self.lateral_threshold = lateral_threshold  # km/h
        self.lane_width = getattr(config, "LANE_WIDTH_THRESHOLD", 2.0)

        print(f"[Hazard] TTC thresholds: RED <= {ttc_red}s | YELLOW <= {ttc_yellow}s")
        print(f"[Hazard] Cut-in lateral velocity threshold: {lateral_threshold} km/h")
        print(f"[Hazard] Ego lane width threshold: +/-{self.lane_width} m")

    def assess(self, actors: list[TrackedActor]) -> list[HazardAssessment]:
        """
        Evaluate hazard for a list of tracked actors.

        Args:
            actors: List of TrackedActor objects from the estimator.

        Returns:
            List of HazardAssessment objects with TTC, hazard level, and cut-in flags.
        """
        assessments = []

        for actor in actors:
            # ─── TTC Calculation ───────────────────────────────────
            ttc = None
            hazard_level = HazardLevel.SAFE

            # ─── Cut-In Detection ──────────────────────────────────
            is_cutin = False
            cutin_direction = None
            abs_lateral = abs(actor.lateral_velocity_kmh)

            if abs_lateral > self.lateral_threshold:
                is_cutin = True
                cutin_direction = "LEFT" if actor.lateral_velocity_kmh < 0 else "RIGHT"

            # Check if object is in our lane OR if it's moving laterally towards us
            is_moving_towards_ego = (
                actor.lateral_distance_m > 0 and actor.lateral_velocity_kmh < -2.0
            ) or (actor.lateral_distance_m < 0 and actor.lateral_velocity_kmh > 2.0)
            in_ego_lane = abs(actor.lateral_distance_m) <= self.lane_width

            is_longitudinal_hazard = in_ego_lane or is_moving_towards_ego or is_cutin

            # velocity_mps < 0 means the object is getting CLOSER (approaching)
            if actor.velocity_mps < -0.1 and actor.distance_m > 0:  # Only if in front!
                closing_speed = abs(actor.velocity_mps)
                if closing_speed > 0:
                    ttc = actor.distance_m / closing_speed

                    # Only escalate hazard if it's actually in our path or cutting into it
                    if is_longitudinal_hazard:
                        if ttc <= self.ttc_red:
                            hazard_level = HazardLevel.CRITICAL
                        elif ttc <= self.ttc_yellow:
                            hazard_level = HazardLevel.WARNING
                        else:
                            hazard_level = HazardLevel.SAFE

            # If cutting in AND nearby (slightly behind/beside to 15m ahead)
            if (
                is_cutin
                and -2.0 <= actor.distance_m < 15.0
                and hazard_level == HazardLevel.SAFE
            ):
                hazard_level = HazardLevel.WARNING

            # ─── Determine box color ──────────────────────────────
            bbox_color = HAZARD_COLORS[hazard_level]

            assessments.append(
                HazardAssessment(
                    actor=actor,
                    ttc=ttc,
                    hazard_level=hazard_level,
                    bbox_color=bbox_color,
                    is_cutin=is_cutin,
                    cutin_direction=cutin_direction,
                )
            )

        return assessments

    @staticmethod
    def get_most_critical(
        assessments: list[HazardAssessment],
    ) -> HazardAssessment | None:
        """Return the assessment with the lowest TTC (most urgent)."""
        critical = [a for a in assessments if a.ttc is not None]
        if not critical:
            return None
        return min(critical, key=lambda a: a.ttc)

    @staticmethod
    def has_active_cutins(
        assessments: list[HazardAssessment],
    ) -> list[HazardAssessment]:
        """Return all assessments where a cut-in is detected."""
        return [a for a in assessments if a.is_cutin]
