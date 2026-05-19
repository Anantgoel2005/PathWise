"""
PathWise — BEV Calibration Utility
Draws the current BEV ROI trapezoid on a target video frame to help with calibration.
"""

import cv2
import argparse
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import config
from modules.perspective import PerspectiveTransformer

def main():
    parser = argparse.ArgumentParser(description="Visualize BEV ROI trapezoid on a frame.")
    parser.add_argument("--source", type=str, default="videoplayback.mp4", help="Video source")
    parser.add_argument("--out", type=str, default="roi_calibration.png", help="Output filename")
    parser.add_argument("--time", type=float, default=25000, help="Time in ms to capture frame")
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"[Error] Source not found: {args.source}")
        return

    cap = cv2.VideoCapture(args.source)
    cap.set(cv2.CAP_PROP_POS_MSEC, args.time)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("[Error] Failed to read frame")
        return

    # Initialize transformer to get mapping
    transformer = PerspectiveTransformer()

    # Draw ROI trapezoid
    result = transformer.draw_roi_on_frame(frame)

    # Add labels for points
    for i, pt in enumerate(config.BEV_SRC_POINTS):
        cv2.putText(result, f"P{i}: {int(pt[0])}, {int(pt[1])}", 
                    (int(pt[0]) + 10, int(pt[1]) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    cv2.imwrite(args.out, result)
    print(f"[Success] Saved ROI visualization to: {args.out}")

if __name__ == "__main__":
    main()
