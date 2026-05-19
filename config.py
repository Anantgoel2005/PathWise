"""
PathWise — Central Configuration
All tunable parameters for detection, tracking, estimation, and hazard logic.
"""

import numpy as np

# ==============================================================================
#  MODEL SELECTION
#  Set MODEL_BACKEND to "idd" to use the India Driving Dataset pretrained model,
#  or "coco" to use the standard YOLOv10n COCO model.
# ==============================================================================
MODEL_BACKEND = "idd"   # "idd" | "coco"

MODEL_PATH = "idd_model.pt" if MODEL_BACKEND == "idd" else "yolov10n.pt"
TRACKER_CONFIG = "bytetrack.yaml"
CONFIDENCE_THRESHOLD = 0.35        # Slightly lower to catch more in dense traffic
IOU_THRESHOLD = 0.5

# ==============================================================================
#  CLASS DEFINITIONS — IDD (India Driving Dataset)
#  15 classes, trained on unstructured Indian road conditions.
# ==============================================================================
IDD_TARGET_CLASSES = [0, 1, 2, 3, 4, 6, 7, 8, 13]   # exclude infra/fallback classes

IDD_CLASS_NAMES = {
    0:  "Animal",
    1:  "Autorickshaw",
    2:  "Bicycle",
    3:  "Bus",
    4:  "Car",
    5:  "Caravan",
    6:  "Motorcycle",
    7:  "Person",
    8:  "Rider",
    9:  "Traffic Light",
    10: "Traffic Sign",
    11: "Trailer",
    12: "Train",
    13: "Truck",
    14: "Vehicle",
}

# BGR colors per IDD class
IDD_CLASS_COLORS = {
    0:  (180, 100, 255),  # Animal       — purple
    1:  (0,   200, 255),  # Autorickshaw — cyan (IDD-unique)
    2:  (50,  255,  50),  # Bicycle      — green
    3:  (200,  50, 255),  # Bus          — pink
    4:  (255, 150,  50),  # Car          — blue-ash
    5:  (100, 180, 200),  # Caravan      — teal
    6:  ( 50, 100, 255),  # Motorcycle   — orange-red
    7:  (255, 200,  50),  # Person       — gold
    8:  (255, 130,  80),  # Rider        — warm orange
    9:  (100, 255, 200),  # Traffic Light
    10: (150, 150, 200),  # Traffic Sign
    11: ( 80, 180, 255),  # Trailer
    12: (200, 200,  50),  # Train        — yellow
    13: (100, 200, 200),  # Truck        — tan
    14: (160, 160, 160),  # Vehicle fallback — grey
}

# ==============================================================================
#  CLASS DEFINITIONS — COCO (fallback)
# ==============================================================================
COCO_TARGET_CLASSES = [0, 1, 2, 3, 5, 7]

COCO_CLASS_NAMES = {
    0: "Pedestrian",
    1: "Bicycle",
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck",
}

COCO_CLASS_COLORS = {
    0: (255, 200, 50),
    1: (50,  255, 50),
    2: (255, 150, 50),
    3: (50,  100, 255),
    5: (200,  50, 255),
    7: (100, 200, 200),
}

# ==============================================================================
#  ACTIVE CLASS CONFIG (resolved from MODEL_BACKEND)
# ==============================================================================
if MODEL_BACKEND == "idd":
    TARGET_CLASSES  = IDD_TARGET_CLASSES
    CLASS_NAMES     = IDD_CLASS_NAMES
    CLASS_COLORS    = IDD_CLASS_COLORS
else:
    TARGET_CLASSES  = COCO_TARGET_CLASSES
    CLASS_NAMES     = COCO_CLASS_NAMES
    CLASS_COLORS    = COCO_CLASS_COLORS

# ==============================================================================
#  HAZARD ENGINE THRESHOLDS
# ==============================================================================
TTC_RED_THRESHOLD      = 2.5    # seconds — TTC ≤ 2.5s → CRITICAL (RED)
TTC_YELLOW_THRESHOLD   = 4.0    # seconds — 2.5s < TTC ≤ 4.0s → WARNING (YELLOW)
LATERAL_CUTIN_THRESHOLD = 15.0  # km/h    — lateral velocity for cut-in detection
LANE_WIDTH_THRESHOLD   = 2.0    # meters  — lateral distance threshold for ego-lane

# ==============================================================================
#  VELOCITY ESTIMATION
# ==============================================================================
VELOCITY_BUFFER_SIZE      = 12   # Frames of distance history per track ID
VELOCITY_SMOOTHING_WINDOW = 5    # Frames for moving-average speed smoothing

# ==============================================================================
#  BIRD'S-EYE VIEW (BEV) PERSPECTIVE TRANSFORM
# ==============================================================================
BEV_SRC_POINTS = np.float32(
    [
        [500, 400],
        [780, 400],
        [1250, 720],
        [30,  720],
    ]
)

BEV_WIDTH  = 400
BEV_HEIGHT = 600
BEV_DST_POINTS = np.float32(
    [
        [100, 0],
        [BEV_WIDTH - 100, 0],
        [BEV_WIDTH - 100, BEV_HEIGHT],
        [100, BEV_HEIGHT],
    ]
)

PIXELS_PER_METER = 50.0
FRAME_WIDTH  = 1280
FRAME_HEIGHT = 720

# ==============================================================================
#  SYSTEM IO & DISPLAY
# ==============================================================================
VIDEO_SOURCE   = 0
OUTPUT_CSV     = True
OUTPUT_VIDEO   = False
SHOW_BEV_DEBUG = False
DISPLAY_SCALE  = 1.0

BEV_MINIMAP_SIZE   = (160, 200)
OVERLAY_FONT_SCALE = 0.55
OVERLAY_THICKNESS  = 2
