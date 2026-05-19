"""
PathWise — Live Web Server Module
Streams the video feed (MJPEG) and broadcasts real-time telemetry (WebSocket).
"""

import threading
import time
import cv2
import json
import logging
from flask import Flask, Response, send_from_directory, request
from flask_socketio import SocketIO

# Suppress standard werkzeug/flask logging for a cleaner console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

class PathWiseWebServer:
    def __init__(self, host="0.0.0.0", port=5000, static_folder="../dashboard"):
        self.host = host
        self.port = port
        self.app = Flask(__name__, static_folder=static_folder, static_url_path="")
        
        # Use simple-websocket or threading async mode
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')
        
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route("/")
        def index():
            return self.app.send_static_file("index.html")

        @self.app.route("/video_feed")
        def video_feed():
            return Response(self._generate_frames(),
                            mimetype="multipart/x-mixed-replace; boundary=frame")

    def _generate_frames(self):
        """Generator that constantly yields the latest encoded frame for the MJPEG stream."""
        while True:
            with self.frame_lock:
                if self.current_frame is None:
                    time.sleep(0.01)
                    continue
                
                # Encode frame to JPEG
                ret, buffer = cv2.imencode('.jpg', self.current_frame)
                if not ret:
                    time.sleep(0.01)
                    continue
                
                frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Control frame rate slightly to avoid overwhelming network
            time.sleep(0.02)

    def update_frame(self, frame):
        """Update the latest frame to be streamed to clients."""
        with self.frame_lock:
            self.current_frame = frame

    def broadcast_telemetry(self, assessments, fps, active_tracks, backend):
        """Broadcast live tracking data to all connected WebSocket clients."""
        
        # Serialize assessments to JSON
        actors_data = []
        cutin_warnings = []
        
        for ha in assessments:
            actor = ha.actor
            actors_data.append({
                "track_id": actor.track_id,
                "class_name": actor.detection.class_name,
                "distance_m": round(actor.distance_m, 1),
                "lat_distance_m": round(actor.lateral_distance_m, 1),
                "speed_kmh": round(actor.velocity_kmh, 1),
                "lat_speed_kmh": round(actor.lateral_velocity_kmh, 1),
                "ttc_s": round(ha.ttc, 1) if ha.ttc is not None else None,
                "hazard_level": ha.hazard_level.value,
                "is_cutin": ha.is_cutin
            })
            
            if ha.is_cutin and ha.cutin_direction:
                cutin_warnings.append(ha.cutin_direction)
                
        payload = {
            "system": {
                "fps": round(fps, 1),
                "tracks": active_tracks,
                "backend": backend
            },
            "actors": actors_data,
            "cutins": list(set(cutin_warnings))
        }
        
        self.socketio.emit("telemetry", payload)

    def start(self):
        """Start the server in a daemon thread."""
        def run_server():
            print(f"[WebServer] Starting Live Dashboard at http://localhost:{self.port}")
            self.socketio.run(self.app, host=self.host, port=self.port, allow_unsafe_werkzeug=True)
            
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
