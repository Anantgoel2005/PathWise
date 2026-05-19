"""
PathWise — Perspective Transform Module
Bird's-Eye View (BEV) homography for monocular distance estimation.
"""

import cv2
import numpy as np

import config


class PerspectiveTransformer:
    """
    Computes and applies a homography matrix to warp camera-view points
    into a Bird's-Eye View (BEV) coordinate system.

    The BEV maps the road plane to a top-down view where pixel distances
    are proportional to real-world distances (assuming flat ground).
    """

    def __init__(
        self,
        src_points: np.ndarray = None,
        dst_points: np.ndarray = None,
        bev_size: tuple = None,
    ):
        self.src_points = (
            src_points if src_points is not None else config.BEV_SRC_POINTS
        )
        self.dst_points = (
            dst_points if dst_points is not None else config.BEV_DST_POINTS
        )
        self.bev_size = bev_size or (config.BEV_WIDTH, config.BEV_HEIGHT)

        # Compute the perspective transform matrix (camera → BEV)
        self.M = cv2.getPerspectiveTransform(self.src_points, self.dst_points)
        # Inverse matrix (BEV → camera) for reverse mapping
        self.M_inv = cv2.getPerspectiveTransform(self.dst_points, self.src_points)

        # Ego-vehicle reference point in BEV space
        self.ego_bev = self.transform_point(config.FRAME_WIDTH / 2, config.FRAME_HEIGHT)

        print("[Perspective] Homography matrix computed")
        print(f"[Perspective] BEV canvas: {self.bev_size[0]}x{self.bev_size[1]}px")
        print(
            f"[Perspective] Ego reference in BEV: ({self.ego_bev[0]:.0f}, {self.ego_bev[1]:.0f})"
        )

    def transform_point(self, x: float, y: float) -> tuple:
        """
        Transform a single (x, y) point from camera view to BEV coordinates.

        Args:
            x, y: Pixel coordinates in the camera frame.

        Returns:
            (bev_x, bev_y) tuple in BEV pixel space.
        """
        point = np.float32([[[x, y]]])
        transformed = cv2.perspectiveTransform(point, self.M)
        bev_x = float(transformed[0][0][0])
        bev_y = float(transformed[0][0][1])
        return (bev_x, bev_y)

    def transform_points(self, points: np.ndarray) -> np.ndarray:
        """
        Transform an array of points from camera view to BEV.

        Args:
            points: np.float32 array of shape (N, 1, 2)

        Returns:
            Transformed points array of same shape.
        """
        if len(points) == 0:
            return points
        return cv2.perspectiveTransform(points, self.M)

    def warp_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Warp the entire camera frame into a BEV image (for debug visualization).

        Args:
            frame: BGR image from camera.

        Returns:
            BEV-warped image.
        """
        return cv2.warpPerspective(
            frame,
            self.M,
            self.bev_size,
            flags=cv2.INTER_LINEAR,
        )

    def pixel_distance_to_meters(self, pixel_dist: float) -> float:
        """Convert BEV pixel distance to real-world meters."""
        return pixel_dist / config.PIXELS_PER_METER

    def draw_roi_on_frame(self, frame: np.ndarray) -> np.ndarray:
        """Draw the source ROI trapezoid on the camera frame (for calibration debug)."""
        overlay = frame.copy()
        pts = self.src_points.astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(overlay, [pts], isClosed=True, color=(0, 255, 255), thickness=2)
        # Draw corner circles
        for pt in self.src_points:
            cv2.circle(overlay, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1)
        return overlay
