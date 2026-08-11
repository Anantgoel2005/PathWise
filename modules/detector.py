"""
PathWise — Detector Module
YOLOv10 detection + ByteTrack multi-object tracking wrapper.
Supports both COCO and IDD (India Driving Dataset) model backends.
"""

import numpy as np
from ultralytics import YOLO

import config
from modules.models import Detection


class Detector:
    """
    Wraps ultralytics YOLO + ByteTrack for persistent multi-object tracking.

    Supports two model backends via config.MODEL_BACKEND:
        - "coco" : Standard YOLOv10n (80 COCO classes)
        - "idd"  : IDD pretrained model (15 Indian road classes)

    Usage:
        detector = Detector()
        detections = detector.process(frame)
    """

    def __init__(
        self,
        model_path: str = config.MODEL_PATH,
        tracker_config: str = config.TRACKER_CONFIG,
        confidence: float = config.CONFIDENCE_THRESHOLD,
        target_classes: list[int] | None = None,
    ):
        self.model = YOLO(model_path)
        self.tracker_config = tracker_config
        self.confidence = confidence
        self.target_classes = target_classes or config.TARGET_CLASSES
        self.backend = config.MODEL_BACKEND

        print(f"[Detector] Backend  : {self.backend.upper()} ({model_path})")
        print(f"[Detector] Tracker  : {tracker_config}")
        print(
            f"[Detector] Classes  : {[config.CLASS_NAMES.get(c, c) for c in self.target_classes]}"
        )
        print(f"[Detector] Conf thr : {confidence}")

        # Build a fast lookup for class name resolution
        self._class_names = config.CLASS_NAMES

    def process(self, frame: np.ndarray) -> list[Detection]:
        """
        Run detection + tracking on a single BGR frame.

        Args:
            frame: BGR image (H, W, 3) from cv2.VideoCapture

        Returns:
            List of Detection dataclass objects with persistent track IDs.
        """
        results = self.model.track(
            source=frame,
            tracker=self.tracker_config,
            persist=True,
            classes=self.target_classes,
            conf=self.confidence,
            verbose=False,
        )

        detections = []

        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes

            if boxes is None or boxes.id is None:
                return detections

            track_ids = boxes.id.int().cpu().numpy()
            bboxes = boxes.xyxy.int().cpu().numpy()
            class_ids = boxes.cls.int().cpu().numpy()
            confidences = boxes.conf.cpu().numpy()

            for i in range(len(track_ids)):
                tid = int(track_ids[i])
                x1, y1, x2, y2 = (
                    int(bboxes[i][0]),
                    int(bboxes[i][1]),
                    int(bboxes[i][2]),
                    int(bboxes[i][3]),
                )
                cid = int(class_ids[i])
                conf = float(confidences[i])

                bottom_center = ((x1 + x2) // 2, y2)
                class_name = self._class_names.get(cid, f"Class_{cid}")

                detections.append(
                    Detection(
                        track_id=tid,
                        bbox=(x1, y1, x2, y2),
                        class_id=cid,
                        class_name=class_name,
                        confidence=conf,
                        bottom_center=bottom_center,
                    )
                )

        return detections
