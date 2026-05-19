"""
PathWise — Distance & Velocity Estimator Module
Maintains per-track velocity buffers and computes real-world speed from BEV coordinates.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass


import config
from modules.detector import Detection
from modules.perspective import PerspectiveTransformer


@dataclass
class TrackedActor:
    """Enriched detection with distance, velocity, and BEV position."""

    track_id: int
    detection: Detection
    distance_m: float  # Distance from ego vehicle (meters)
    lateral_distance_m: float  # Lateral offset from ego vehicle center (meters)
    velocity_mps: float  # Longitudinal relative velocity (m/s, negative = approaching)
    velocity_kmh: float  # Longitudinal speed (km/h)
    lateral_velocity_mps: float  # Lateral velocity (m/s)
    lateral_velocity_kmh: float  # Lateral speed (km/h)
    bev_position: tuple  # (bev_x, bev_y) in BEV pixel space


class VelocityEstimator:
    """
    Tracks per-object distance history and computes smoothed velocities.

    For each active track ID, maintains a circular buffer of
    (timestamp, distance, bev_x, bev_y) tuples. Velocity is computed
    as the slope over the buffer window for noise reduction.
    """

    def __init__(
        self,
        perspective: PerspectiveTransformer,
        buffer_size: int = config.VELOCITY_BUFFER_SIZE,
    ):
        self.perspective = perspective
        self.buffer_size = buffer_size

        # track_id → deque of (timestamp, distance_m, bev_x, bev_y)
        self._buffers: dict[int, deque] = defaultdict(
            lambda: deque(maxlen=self.buffer_size)
        )

        # Track which IDs are still alive this frame
        self._active_ids: set = set()

    def update(
        self, detections: list[Detection], timestamp: float = None
    ) -> list[TrackedActor]:
        """
        Process a batch of detections for a single frame.

        Args:
            detections: List of Detection objects from the detector.
            timestamp: Frame timestamp in seconds (defaults to time.time()).

        Returns:
            List of TrackedActor objects with distance and velocity filled in.
        """
        if timestamp is None:
            timestamp = time.time()

        current_ids = set()
        tracked_actors = []

        for det in detections:
            tid = det.track_id
            current_ids.add(tid)

            # --- Transform bottom_center to BEV ---
            bev_x, bev_y = self.perspective.transform_point(
                det.bottom_center[0], det.bottom_center[1]
            )

            # --- Compute distance from ego reference in BEV space ---
            ego_bev = self.perspective.ego_bev
            dx_px = bev_x - ego_bev[0]
            dy_px = bev_y - ego_bev[1]  # negative = in front of ego

            # Use longitudinal distance (pure forward) to correctly handle actors beside us.
            longitudinal_px = -dy_px  # positive = in front of ego, 0 = beside ego
            distance_m = self.perspective.pixel_distance_to_meters(longitudinal_px)
            lateral_distance_m = self.perspective.pixel_distance_to_meters(dx_px)

            # --- Append to velocity buffer ---
            self._buffers[tid].append((timestamp, distance_m, bev_x, bev_y))

            # --- Compute velocities ---
            velocity_mps = 0.0
            lateral_velocity_mps = 0.0

            buf = self._buffers[tid]
            if len(buf) >= 2:
                # Use oldest and newest entries for smoothed velocity
                t_old, d_old, bx_old, by_old = buf[0]
                t_new, d_new, bx_new, by_new = buf[-1]
                dt = t_new - t_old

                if dt > 0.001:  # Avoid division by near-zero
                    # Longitudinal velocity (distance change rate)
                    # Negative = object getting closer (approaching)
                    velocity_mps = (d_new - d_old) / dt

                    # Lateral velocity in BEV space (converted to meters)
                    lateral_px = bx_new - bx_old
                    lateral_velocity_mps = (
                        self.perspective.pixel_distance_to_meters(lateral_px) / dt
                    )

            velocity_kmh = velocity_mps * 3.6
            lateral_velocity_kmh = lateral_velocity_mps * 3.6

            tracked_actors.append(
                TrackedActor(
                    track_id=tid,
                    detection=det,
                    distance_m=distance_m,
                    lateral_distance_m=lateral_distance_m,
                    velocity_mps=velocity_mps,
                    velocity_kmh=velocity_kmh,
                    lateral_velocity_mps=lateral_velocity_mps,
                    lateral_velocity_kmh=lateral_velocity_kmh,
                    bev_position=(bev_x, bev_y),
                )
            )

        # --- Prune stale track buffers ---
        stale_ids = set(self._buffers.keys()) - current_ids
        for sid in stale_ids:
            del self._buffers[sid]

        self._active_ids = current_ids
        return tracked_actors

    @property
    def active_track_count(self) -> int:
        return len(self._active_ids)
