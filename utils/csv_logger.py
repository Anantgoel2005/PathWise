"""
PathWise — CSV Data Logger
Exports per-frame tracking data with hazard flags to timestamped CSV files.
"""

import csv
import os
from datetime import datetime


class CSVLogger:
    """
    Logs tracking + hazard data to a CSV file for benchmarking and analysis.

    CSV Columns:
        Timestamp, Frame, ObjectID, ClassName, Distance_m, Speed_kmh,
        LateralSpeed_kmh, TTC_s, HazardLevel, CutInFlag, CutInDirection

    Flushes to disk periodically to reduce I/O overhead.
    """

    COLUMNS = [
        "Timestamp",
        "Frame",
        "ObjectID",
        "ClassName",
        "Distance_m",
        "Speed_kmh",
        "LateralSpeed_kmh",
        "TTC_s",
        "HazardLevel",
        "CutInFlag",
        "CutInDirection",
    ]

    def __init__(self, output_dir: str = None, flush_interval: int = 30):
        """
        Args:
            output_dir: Directory to write CSV files. Defaults to output/logs/.
            flush_interval: Flush to disk every N frames.
        """
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "output", "logs"
        )
        os.makedirs(self.output_dir, exist_ok=True)

        self.flush_interval = flush_interval
        self._frame_counter = 0
        self._row_buffer = []

        # Create timestamped filename
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = os.path.join(self.output_dir, f"log_{ts}.csv")

        # Open file and write header
        self._file = open(self.filepath, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(self.COLUMNS)

        print(f"[CSVLogger] Logging to: {self.filepath}")

    def log_frame(self, frame_num: int, assessments: list):
        """
        Log all assessments for a single frame.

        Args:
            frame_num: Current frame number.
            assessments: List of HazardAssessment objects.
        """
        timestamp = datetime.now().isoformat(timespec="milliseconds")

        for ha in assessments:
            row = [
                timestamp,
                frame_num,
                ha.actor.track_id,
                ha.actor.detection.class_name,
                f"{ha.actor.distance_m:.2f}",
                f"{ha.actor.velocity_kmh:.1f}",
                f"{ha.actor.lateral_velocity_kmh:.1f}",
                f"{ha.ttc:.2f}" if ha.ttc is not None else "",
                ha.hazard_level.value,
                ha.is_cutin,
                ha.cutin_direction or "",
            ]
            self._writer.writerow(row)

        self._frame_counter += 1

        # Periodic flush
        if self._frame_counter % self.flush_interval == 0:
            self._file.flush()

    def close(self):
        """Flush and close the CSV file."""
        try:
            self._file.flush()
            self._file.close()
            print(f"[CSVLogger] Closed log file: {self.filepath}")
        except Exception:
            pass

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
