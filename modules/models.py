"""Shared data models for the PathWise perception and hazard pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    """A detected and tracked road actor in camera coordinates."""

    track_id: int
    bbox: tuple[int, int, int, int]
    class_id: int
    class_name: str
    confidence: float
    bottom_center: tuple[int, int]

    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]

    @property
    def center(self) -> tuple[int, int]:
        return (
            (self.bbox[0] + self.bbox[2]) // 2,
            (self.bbox[1] + self.bbox[3]) // 2,
        )


@dataclass(frozen=True)
class TrackedActor:
    """A detection enriched with relative position and motion estimates."""

    track_id: int
    detection: Detection
    distance_m: float
    lateral_distance_m: float
    velocity_mps: float
    velocity_kmh: float
    lateral_velocity_mps: float
    lateral_velocity_kmh: float
    bev_position: tuple[float, float]
