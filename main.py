"""
PathWise — Main Pipeline Entry Point
Orchestrates the full detection → tracking → estimation → hazard → overlay pipeline.

Usage:
    python main.py                           # Webcam (default)
    python main.py --source video.mp4        # Video file
    python main.py --source 0 --record       # Webcam + save output
    python main.py --source video.mp4 --show-bev --no-display  # Headless + BEV debug
"""

import argparse
import os
import sys
import time

import cv2
import numpy as np

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from modules.detector import Detector
from modules.perspective import PerspectiveTransformer
from modules.estimator import VelocityEstimator
from modules.hazard import HazardEngine
from modules.overlay import DashboardOverlay
from utils.csv_logger import CSVLogger
from modules.web_server import PathWiseWebServer


def parse_args():
    parser = argparse.ArgumentParser(
        description="PathWise: Edge-AI Road Actor Behavior Prediction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                              # Run with webcam
  python main.py --source traffic.mp4         # Run with video file
  python main.py --source 0 --record          # Webcam + record output
  python main.py --source video.mp4 --show-bev  # Show BEV debug window
        """,
    )

    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Video source: webcam index (0,1,...) or path to .mp4 file. "
        "Defaults to config.VIDEO_SOURCE.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=config.MODEL_PATH,
        help=f"YOLO model path (default: {config.MODEL_PATH})",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        default=config.OUTPUT_VIDEO,
        help="Save annotated video to output/recordings/",
    )
    parser.add_argument(
        "--no-csv", action="store_true", help="Disable CSV data logging"
    )
    parser.add_argument(
        "--show-bev",
        action="store_true",
        default=config.SHOW_BEV_DEBUG,
        help="Show BEV debug window",
    )
    parser.add_argument(
        "--no-display", action="store_true", help="Run headless (no display window)"
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=config.CONFIDENCE_THRESHOLD,
        help=f"Detection confidence threshold (default: {config.CONFIDENCE_THRESHOLD})",
    )

    return parser.parse_args()


def resolve_source(source_arg):
    """Resolve video source from CLI arg or config."""
    if source_arg is None:
        return config.VIDEO_SOURCE

    # Check if it's a numeric webcam index
    try:
        return int(source_arg)
    except ValueError:
        pass

    # It's a file path
    if not os.path.exists(source_arg):
        print(f"[ERROR] Video file not found: {source_arg}")
        sys.exit(1)

    return source_arg


def main():
    args = parse_args()

    # ─── Banner ────────────────────────────────────────────────────────────────
    print("=" * 60)
    print("  PathWise: Edge-AI Road Actor Behavior Prediction")
    print("  Real-time TTC & Cut-In Detection System")
    print("=" * 60)
    print()

    # ─── Resolve video source ──────────────────────────────────────────────────
    source = resolve_source(args.source)
    print(f"[Main] Video source: {source}")

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Failed to open video source: {source}")
        sys.exit(1)

    # Get video properties
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    input_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[Main] Resolution: {frame_w}x{frame_h} @ {input_fps:.0f} FPS")
    if total_frames > 0:
        duration = total_frames / input_fps
        print(f"[Main] Duration: {duration:.1f}s ({total_frames} frames)")
    print()

    # ─── Update config for actual resolution ───────────────────────────────────
    # Scale BEV source points if resolution differs from config defaults
    scale_x = frame_w / config.FRAME_WIDTH
    scale_y = frame_h / config.FRAME_HEIGHT
    if abs(scale_x - 1.0) > 0.01 or abs(scale_y - 1.0) > 0.01:
        print(
            f"[Main] Scaling BEV points for {frame_w}x{frame_h} (config was {config.FRAME_WIDTH}x{config.FRAME_HEIGHT})"
        )
        config.BEV_SRC_POINTS[:, 0] *= scale_x
        config.BEV_SRC_POINTS[:, 1] *= scale_y
        config.FRAME_WIDTH = frame_w
        config.FRAME_HEIGHT = frame_h
        config.EGO_REF_POINT = np.float32([[frame_w / 2, frame_h]])

    # ─── Initialize Pipeline Components ────────────────────────────────────────
    print("[Main] Initializing pipeline...")

    detector = Detector(
        model_path=args.model,
        confidence=args.confidence,
    )

    perspective = PerspectiveTransformer()
    estimator = VelocityEstimator(perspective=perspective)
    hazard_engine = HazardEngine()
    overlay = DashboardOverlay()

    # Initialize and start Web Server
    web_server = PathWiseWebServer(port=5000)
    web_server.start()

    csv_logger = None
    if config.OUTPUT_CSV and not args.no_csv:
        csv_logger = CSVLogger()

    # ─── Video Writer (optional) ───────────────────────────────────────────────
    video_writer = None
    if args.record:
        from datetime import datetime

        rec_dir = os.path.join(os.path.dirname(__file__), "output", "recordings")
        os.makedirs(rec_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        rec_path = os.path.join(rec_dir, f"pathwise_{ts}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(rec_path, fourcc, input_fps, (frame_w, frame_h))
        print(f"[Main] Recording to: {rec_path}")

    print()
    print("[Main] Pipeline ready. Press 'q' to quit.")
    print("-" * 60)

    # ─── Main Processing Loop ──────────────────────────────────────────────────
    frame_num = 0
    fps = 0.0
    fps_start = time.time()
    fps_frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                if isinstance(source, str):
                    print("\n[Main] End of video file reached.")
                else:
                    print("\n[Main] Camera feed lost.")
                break

            frame_num += 1
            frame_time = time.time()

            # ── Step 1: Detect & Track ──
            detections = detector.process(frame)

            # ── Step 2: Estimate Distance & Velocity ──
            actors = estimator.update(detections, timestamp=frame_time)

            # ── Step 3: Assess Hazards ──
            assessments = hazard_engine.assess(actors)

            # ── Step 4: Render Overlay ──
            display_frame = overlay.render(frame.copy(), assessments, fps=fps, show_minimap=True)

            # ── Step 4.5: Update Web Dashboard ──
            web_server.update_frame(display_frame)
            web_server.broadcast_telemetry(assessments, fps, estimator.active_track_count, config.MODEL_BACKEND)

            # ── Step 5: Log Data ──
            if csv_logger and assessments:
                csv_logger.log_frame(frame_num, assessments)

            # ── Step 6: Record ──
            if video_writer:
                video_writer.write(display_frame)

            # ── Step 7: Display ──
            if not args.no_display:
                cv2.imshow("PathWise", display_frame)

                # Optional BEV debug window
                if args.show_bev:
                    bev_frame = perspective.warp_frame(frame)
                    cv2.imshow("PathWise BEV", bev_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:  # q or ESC
                    print("\n[Main] User quit.")
                    break

            # ── FPS Calculation ──
            fps_frame_count += 1
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                fps = fps_frame_count / elapsed
                fps_frame_count = 0
                fps_start = time.time()

            # ── Progress (for video files) ──
            if total_frames > 0 and frame_num % 100 == 0:
                progress = (frame_num / total_frames) * 100
                print(
                    f"  Frame {frame_num}/{total_frames} ({progress:.0f}%) | "
                    f"FPS: {fps:.1f} | Tracks: {estimator.active_track_count}"
                )

    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user.")

    finally:
        # ─── Cleanup ──────────────────────────────────────────────────────────
        print("\n[Main] Shutting down...")
        cap.release()

        if video_writer:
            video_writer.release()
            print("[Main] Recording saved.")

        if csv_logger:
            csv_logger.close()

        cv2.destroyAllWindows()

        print("[Main] PathWise terminated.")
        print("=" * 60)


if __name__ == "__main__":
    main()
