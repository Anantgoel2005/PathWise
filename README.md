# PathWise: Proactive Road Actor Behavior Prediction

![Architecture](https://img.shields.io/badge/Architecture-Edge--AI-blue)
![YOLOv10](https://img.shields.io/badge/Model-YOLOv10n-green)
![ByteTrack](https://img.shields.io/badge/Tracker-ByteTrack-orange)

**PathWise** is a high-performance computer vision system designed for real-time road actor behavior prediction in unstructured traffic environments. It integrates detection, tracking, and geometric distance estimation to identify hazards before they escalate.

## ✨ Key Features

- **🚀 Real-Time Detection**: Powered by YOLOv10 Nano for high-speed inference even on CPU.
- **🛰️ BEV Radar**: Translates monocular camera feeds into a stable 2D Bird's-Eye View (BEV) map.
- **⚡ Hazard Engine**: Calculates **Time-to-Collision (TTC)** and detects **Lateral Cut-ins** from adjacent lanes.
- **🛡️ Visual Alerts**: Intuitive dashboard overlay with color-coded safety indicators (RED/YELLOW/GREEN).
- **📊 Data Logging**: Comprehensive frame-by-frame CSV export for post-processing and benchmarking.

## 🛠️ Quick Start (Windows)

The project includes pre-configured batch files for zero-setup execution:

1. **Process Video**: Run `run_video.bat` and press **ENTER** to use the sample showcase video.
2. **Live Webcam**: Run `run_webcam.bat` to process a live feed (Source 0).

### Manual Setup
```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install requirements
pip install -r requirements.txt

# 3. Launch the pipeline
python main.py --source videoplayback.mp4 --show-bev
```

## 🏗️ System Architecture

PathWise follows a modular pipeline design:

1.  **Detector**: Identifies vehicles/pedestrians and maintains persistent identities via ByteTrack.
2.  **Estimator**: Uses homography to map pixel coordinates to real-world meters.
3.  **Hazard Engine**: Assesses longitudinal and lateral risk based on refined velocity profiles.
4.  **Overlay**: Renders the HUD, alerts, and BEV minimap.

## ⚙️ Configuration

Tune your environment in `config.py`:
- **TTC Thresholds**: Adjust `TTC_RED_THRESHOLD` and `TTC_YELLOW_THRESHOLD`.
- **BEV Calibration**: Refine `BEV_SRC_POINTS` to match your specific camera mounting angle.
- **Class Filtering**: Select target actors (default: Car, Truck, Bus, Motorcycle, Pedestrian).

## 📂 Project Structure

- `main.py`: Entry point for the PathWise pipeline.
- `modules/`: Core logic for detection, estimation, and hazard assessment.
- `utils/`: Calibration and presentation utilities.
- `output/`: Automatically generated logs and video recordings.

---
*Created for proactive road safety research.*
