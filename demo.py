"""Generate a deterministic, model-free PathWise hazard demonstration.

The demo exercises the risk engine and presentation layer without accessing a
camera, downloading model weights, or starting a network service. It is a
reproducibility aid, not a perception benchmark.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from modules.hazard import HazardEngine, HazardLevel
from modules.models import Detection, TrackedActor
from modules.overlay import DashboardOverlay

WIDTH = 1280
HEIGHT = 720


def _detection(
    track_id: int,
    class_name: str,
    distance_m: float,
    lateral_m: float,
) -> Detection:
    """Place a synthetic actor on the road using an approximate pinhole layout."""
    center_x = int(WIDTH / 2 + lateral_m * 62)
    ground_y = int(HEIGHT - 72 - distance_m * 12.5)
    box_width = int(max(52, 158 - distance_m * 3.6))
    box_height = int(box_width * (0.72 if class_name == "Motorcycle" else 0.60))
    bbox = (
        center_x - box_width // 2,
        ground_y - box_height,
        center_x + box_width // 2,
        ground_y,
    )
    return Detection(
        track_id=track_id,
        bbox=bbox,
        class_id=track_id,
        class_name=class_name,
        confidence=0.99,
        bottom_center=(center_x, ground_y),
    )


def _actor(
    track_id: int,
    class_name: str,
    distance_m: float,
    lateral_m: float,
    velocity_mps: float,
    lateral_velocity_mps: float,
) -> TrackedActor:
    detection = _detection(track_id, class_name, distance_m, lateral_m)
    return TrackedActor(
        track_id=track_id,
        detection=detection,
        distance_m=distance_m,
        lateral_distance_m=lateral_m,
        velocity_mps=velocity_mps,
        velocity_kmh=velocity_mps * 3.6,
        lateral_velocity_mps=lateral_velocity_mps,
        lateral_velocity_kmh=lateral_velocity_mps * 3.6,
        bev_position=(lateral_m, distance_m),
    )


def scenario_actors(frame_index: int, fps: int) -> list[TrackedActor]:
    """Return three deterministic trajectories for one simulation frame."""
    seconds = frame_index / fps

    lead_distance = max(5.0, 24.0 - 3.0 * seconds)
    lead = _actor(7, "Car", lead_distance, 0.2, -3.0, 0.0)

    cut_start = int(1.7 * fps)
    cut_end = int(2.8 * fps)
    if frame_index < cut_start:
        cut_lateral = -4.8
        cut_lateral_velocity = 0.0
    elif frame_index < cut_end:
        cut_lateral_velocity = 4.5
        cut_lateral = min(0.0, -4.8 + (frame_index - cut_start) * 4.5 / fps)
    else:
        cut_lateral = 0.0
        cut_lateral_velocity = 0.0
    cut_distance = max(6.0, 17.0 - 0.9 * seconds)
    cutter = _actor(
        12,
        "Motorcycle",
        cut_distance,
        cut_lateral,
        -0.9,
        cut_lateral_velocity,
    )

    bus = _actor(21, "Bus", 14.0 + 0.6 * seconds, 4.2, 0.6, 0.0)
    return [lead, cutter, bus]


def _road_frame(frame_index: int) -> np.ndarray:
    frame = np.full((HEIGHT, WIDTH, 3), (22, 25, 31), dtype=np.uint8)
    horizon = 205
    cv2.rectangle(frame, (0, 0), (WIDTH, horizon), (38, 43, 54), -1)
    road = np.array([[470, horizon], [810, horizon], [1180, HEIGHT], [100, HEIGHT]])
    cv2.fillConvexPoly(frame, road, (48, 51, 58))
    cv2.line(frame, (470, horizon), (100, HEIGHT), (83, 88, 96), 3)
    cv2.line(frame, (810, horizon), (1180, HEIGHT), (83, 88, 96), 3)

    offset = (frame_index * 18) % 120
    for y in range(horizon + offset, HEIGHT, 120):
        progress = (y - horizon) / (HEIGHT - horizon)
        x_left = int(640 - 82 * progress)
        x_right = int(640 + 82 * progress)
        length = int(18 + 38 * progress)
        cv2.line(
            frame, (x_left, y), (x_left, min(HEIGHT, y + length)), (180, 181, 178), 4
        )
        cv2.line(
            frame, (x_right, y), (x_right, min(HEIGHT, y + length)), (180, 181, 178), 4
        )

    cv2.putText(
        frame,
        "DETERMINISTIC SYNTHETIC HAZARD DEMO",
        (18, HEIGHT - 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (160, 166, 176),
        1,
        cv2.LINE_AA,
    )
    return frame


def _draw_demo_hud(
    frame: np.ndarray,
    assessments: list,
    frame_index: int,
    fps: int,
) -> None:
    """Add an explicit scenario panel so the generated artifact is self-explanatory."""
    panel = frame.copy()
    cv2.rectangle(panel, (930, 52), (1254, 240), (10, 13, 19), -1)
    cv2.addWeighted(panel, 0.88, frame, 0.12, 0, frame)
    cv2.rectangle(frame, (930, 52), (1254, 240), (0, 190, 240), 1)
    cv2.putText(
        frame,
        "HAZARD ENGINE TELEMETRY",
        (950, 82),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.53,
        (0, 200, 255),
        1,
        cv2.LINE_AA,
    )

    most_critical = HazardEngine.get_most_critical(assessments)
    active_cutin = any(item.is_cutin for item in assessments)
    rank = {HazardLevel.SAFE: 0, HazardLevel.WARNING: 1, HazardLevel.CRITICAL: 2}
    highest = max(assessments, key=lambda item: rank[item.hazard_level]).hazard_level
    risk_color = {
        HazardLevel.SAFE: (0, 220, 100),
        HazardLevel.WARNING: (0, 200, 255),
        HazardLevel.CRITICAL: (0, 0, 255),
    }[highest]
    risk_label = highest.value
    if active_cutin and highest is HazardLevel.SAFE:
        risk_label = "CUT-IN"
        risk_color = (0, 200, 255)
    rows = [
        ("SCENARIO", "SYNTHETIC / FIXED"),
        ("FRAME", f"{frame_index + 1:03d}"),
        ("CUT-IN", "ACTIVE" if active_cutin else "CLEAR"),
        ("MIN TTC", "N/A" if most_critical is None else f"{most_critical.ttc:.2f} s"),
    ]
    for row, (label, value) in enumerate(rows):
        y = 112 + row * 27
        cv2.putText(
            frame,
            label,
            (950, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            (140, 148, 160),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            value,
            (1055, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (226, 232, 240),
            1,
            cv2.LINE_AA,
        )
    cv2.putText(
        frame,
        "RISK",
        (950, 224),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (140, 148, 160),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        risk_label,
        (1055, 224),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        risk_color,
        2,
        cv2.LINE_AA,
    )

    cv2.rectangle(frame, (1100, 6), (1264, 27), (28, 32, 40), -1)
    cv2.putText(
        frame,
        f"MODEL-FREE  {fps} FPS",
        (1113, 21),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.38,
        (180, 188, 198),
        1,
        cv2.LINE_AA,
    )


def run_demo(
    output_dir: Path,
    frames: int = 180,
    fps: int = 30,
    write_video: bool = True,
) -> dict:
    """Run the deterministic scenario and return its summary metrics."""
    if frames < 1 or fps < 1:
        raise ValueError("frames and fps must be positive")

    output_dir.mkdir(parents=True, exist_ok=True)
    engine = HazardEngine()
    overlay = DashboardOverlay()
    video_path = output_dir / "pathwise-synthetic-demo.mp4"
    telemetry_path = output_dir / "telemetry.csv"
    metrics_path = output_dir / "metrics.json"

    writer = None
    if write_video:
        writer = cv2.VideoWriter(
            str(video_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (WIDTH, HEIGHT),
        )
        if not writer.isOpened():
            raise RuntimeError("OpenCV could not initialize the MP4 writer")

    hazard_frames: Counter[str] = Counter()
    actor_samples = 0
    minimum_ttc: float | None = None
    cutin_frames = 0

    with telemetry_path.open("w", newline="", encoding="utf-8") as handle:
        csv_writer = csv.writer(handle)
        csv_writer.writerow(
            [
                "frame",
                "track_id",
                "class_name",
                "distance_m",
                "lateral_m",
                "closing_speed_mps",
                "ttc_s",
                "hazard_level",
                "cut_in",
            ]
        )

        for frame_index in range(frames):
            assessments = engine.assess(scenario_actors(frame_index, fps))
            actor_samples += len(assessments)
            levels = {assessment.hazard_level.value for assessment in assessments}
            for level in levels:
                hazard_frames[level] += 1
            if any(assessment.is_cutin for assessment in assessments):
                cutin_frames += 1

            for assessment in assessments:
                if assessment.ttc is not None:
                    minimum_ttc = (
                        assessment.ttc
                        if minimum_ttc is None
                        else min(minimum_ttc, assessment.ttc)
                    )
                actor = assessment.actor
                csv_writer.writerow(
                    [
                        frame_index,
                        actor.track_id,
                        actor.detection.class_name,
                        f"{actor.distance_m:.3f}",
                        f"{actor.lateral_distance_m:.3f}",
                        f"{-actor.velocity_mps:.3f}",
                        "" if assessment.ttc is None else f"{assessment.ttc:.3f}",
                        assessment.hazard_level.value,
                        assessment.is_cutin,
                    ]
                )

            if writer:
                rendered = overlay.render(
                    _road_frame(frame_index),
                    assessments,
                    fps=float(fps),
                )
                _draw_demo_hud(rendered, assessments, frame_index, fps)
                writer.write(rendered)

    if writer:
        writer.release()

    metrics = {
        "scenario": "deterministic-synthetic-v1",
        "frames": frames,
        "fps": fps,
        "duration_seconds": round(frames / fps, 3),
        "actor_samples": actor_samples,
        "cut_in_frames": cutin_frames,
        "minimum_ttc_seconds": None if minimum_ttc is None else round(minimum_ttc, 3),
        "frames_with_level": dict(sorted(hazard_frames.items())),
        "video": video_path.name if write_video else None,
        "telemetry": telemetry_path.name,
        "disclaimer": "Synthetic hazard-engine demonstration; not a perception benchmark.",
    }
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output/demo"))
    parser.add_argument("--frames", type=int, default=180)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--no-video", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = run_demo(args.output, args.frames, args.fps, not args.no_video)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
