"""
PathWise — TensorRT Export Utility
Exports the YOLO model to TensorRT .engine format for Jetson deployment.

Usage:
    python utils/export_tensorrt.py [--model yolov10n.pt] [--half] [--imgsz 640]

NOTE: This should be run ON the target Jetson device for architecture-specific
      optimization. The generated .engine file is NOT portable across GPU architectures.
"""

import argparse
import sys
import os

# Add parent dir to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def export_tensorrt(model_path: str, half: bool = True, imgsz: int = 640):
    """
    Export a YOLO model to TensorRT engine format.

    Args:
        model_path: Path to the .pt model weights.
        half: Use FP16 quantization (recommended for Jetson).
        imgsz: Input image size for the engine.
    """
    from ultralytics import YOLO

    print(f"[TensorRT Export] Loading model: {model_path}")
    model = YOLO(model_path)

    print(f"[TensorRT Export] Exporting to TensorRT (half={half}, imgsz={imgsz})...")
    print("[TensorRT Export] This may take several minutes on Jetson hardware.")

    engine_path = model.export(
        format="engine",
        half=half,
        imgsz=imgsz,
        device=0,
    )

    print(f"[TensorRT Export] Engine saved to: {engine_path}")
    print("[TensorRT Export] Update config.MODEL_PATH to use this engine file.")
    return engine_path


def main():
    parser = argparse.ArgumentParser(description="Export YOLO model to TensorRT")
    parser.add_argument(
        "--model", type=str, default="yolov10n.pt", help="Path to .pt model weights"
    )
    parser.add_argument(
        "--half",
        action="store_true",
        default=True,
        help="Use FP16 quantization (default: True)",
    )
    parser.add_argument("--no-half", action="store_true", help="Disable FP16, use FP32")
    parser.add_argument(
        "--imgsz", type=int, default=640, help="Input image size (default: 640)"
    )

    args = parser.parse_args()

    use_half = args.half and not args.no_half
    export_tensorrt(args.model, half=use_half, imgsz=args.imgsz)


if __name__ == "__main__":
    main()
