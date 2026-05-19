"""
PathWise — Dashboard Overlay Module
Composite-frame layout: camera feed (left) + dark sidebar panel (right).
"""

import datetime
import math
import time

import cv2
import numpy as np

import config
from modules.hazard import HazardAssessment, HazardLevel, HazardEngine

# ── Sidebar / BEV constants ────────────────────────────────────────────────────
SIDEBAR_W   = 280          # sidebar pixel width
BEV_W       = 248          # BEV panel width inside sidebar
BEV_H       = 260          # BEV panel height
MM_SCALE    = 5.0          # pixels per real-world metre (5 → ~45 m forward view)
EGO_MARGIN  = 38           # pixels of space below ego marker


class DashboardOverlay:

    def __init__(self):
        self._frame_count   = 0
        self._flash_state   = False
        self._flash_time    = 0.0

    # ── Public entry ──────────────────────────────────────────────────────────
    def render(
        self,
        frame: np.ndarray,
        assessments: list[HazardAssessment],
        fps: float = 0.0,
        show_minimap: bool = True,   # kept for API compat; always shown in sidebar
    ) -> np.ndarray:
        self._frame_count += 1
        fh, fw = frame.shape[:2]

        # 1 — Draw on camera frame
        self._draw_boxes(frame, assessments)
        self._draw_labels(frame, assessments)
        self._draw_top_bar(frame, fw)

        cutins = HazardEngine.has_active_cutins(assessments)
        if cutins:
            self._draw_cutin_banner(frame, cutins, fw, fh)

        critical = HazardEngine.get_most_critical(assessments)
        if critical and critical.hazard_level == HazardLevel.CRITICAL:
            self._draw_vignette(frame, critical, fw, fh)

        # 2 — Skip sidebar rendering (handled by web dashboard now)
        # 3 — Return clean frame
        return frame

    # ── Bounding boxes ─────────────────────────────────────────────────────────
    def _draw_boxes(self, frame, assessments):
        for ha in assessments:
            x1, y1, x2, y2 = ha.actor.detection.bbox
            col = ha.bbox_color
            is_crit = ha.hazard_level == HazardLevel.CRITICAL

            if is_crit:
                pulse = abs(math.sin(self._frame_count * 0.15))
                glow  = frame.copy()
                cv2.rectangle(glow, (x1-3, y1-3), (x2+3, y2+3), (0, 0, 255), 5)
                cv2.addWeighted(glow, 0.12 + pulse * 0.20, frame, 1.0, 0, frame)

            cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)

            # Corner brackets
            cl = min(14, (x2-x1)//4, (y2-y1)//4)
            for ax, ay, sx, sy in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
                cv2.line(frame, (ax, ay), (ax+sx*cl, ay),      col, 2)
                cv2.line(frame, (ax, ay), (ax,        ay+sy*cl), col, 2)

    # ── Labels ────────────────────────────────────────────────────────────────
    def _draw_labels(self, frame, assessments):
        font  = cv2.FONT_HERSHEY_SIMPLEX
        fscale = 0.40
        pad   = 3

        for ha in assessments:
            x1, y1, x2, y2 = ha.actor.detection.bbox
            col  = ha.bbox_color
            det  = ha.actor.detection

            line1 = f"{det.class_name} #{det.track_id}"
            line2 = f"{abs(ha.actor.velocity_kmh):.0f}km/h"
            if ha.ttc is not None:
                line2 += f"  {ha.ttc:.1f}s"

            (w1, th), _  = cv2.getTextSize(line1, font, fscale, 1)
            (w2,  _), _  = cv2.getTextSize(line2, font, fscale, 1)
            pw  = max(w1, w2) + pad * 2
            ph  = th * 2 + pad * 3

            py1 = max(0, y1 - ph - 3)
            py2 = py1 + ph
            px2 = min(frame.shape[1]-1, x1 + pw)

            roi = frame[py1:py2, x1:px2]
            if roi.size:
                bg = np.full_like(roi, (14, 16, 24))
                cv2.addWeighted(bg, 0.75, roi, 0.25, 0, roi)
                frame[py1:py2, x1:px2] = roi

            cv2.rectangle(frame, (x1, py1), (x1+2, py2), col, -1)
            cv2.putText(frame, line1, (x1+pad+3, py1+th+pad),   font, fscale, col,           1, cv2.LINE_AA)
            cv2.putText(frame, line2, (x1+pad+3, py2-pad-1),    font, fscale, (200,200,200), 1, cv2.LINE_AA)

            dist = f"{ha.actor.distance_m:.1f}m"
            cv2.putText(frame, dist, (x1+2, min(y2+13, frame.shape[0]-2)),
                        font, 0.35, col, 1, cv2.LINE_AA)

    # ── Minimal top watermark ─────────────────────────────────────────────────
    def _draw_top_bar(self, frame, fw):
        ov = frame.copy()
        cv2.rectangle(ov, (0,0), (fw, 32), (10,12,18), -1)
        cv2.addWeighted(ov, 0.70, frame, 0.30, 0, frame)
        cv2.line(frame, (0,32), (fw,32), (0,130,160), 1)
        cv2.putText(frame, "PATHWISE", (10,22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0,190,240), 2, cv2.LINE_AA)

    # ── Cut-in banner ─────────────────────────────────────────────────────────
    def _draw_cutin_banner(self, frame, cutins, fw, fh):
        now = time.time()
        if now - self._flash_time > 0.35:
            self._flash_state = not self._flash_state
            self._flash_time  = now
        if not self._flash_state:
            return
        bh = 40; by1 = fh - bh - 8
        ov = frame.copy()
        cv2.rectangle(ov, (8, by1), (fw-8, by1+bh), (0,0,160), -1)
        cv2.addWeighted(ov, 0.82, frame, 0.18, 0, frame)
        cv2.rectangle(frame, (8,by1), (fw-8,by1+bh), (30,30,255), 1)
        dirs = list({c.cutin_direction for c in cutins if c.cutin_direction})
        txt  = f"CUT-IN  {'  '.join(dirs)}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw,th),_ = cv2.getTextSize(txt, font, 0.68, 2)
        cv2.putText(frame, txt, ((fw-tw)//2, by1+(bh+th)//2), font, 0.68, (255,255,255), 2, cv2.LINE_AA)

    # ── Critical vignette ─────────────────────────────────────────────────────
    def _draw_vignette(self, frame, ha, fw, fh):
        pulse = abs(math.sin(self._frame_count * 0.13))
        alpha = 0.08 + pulse * 0.18
        bw = 10
        glow = frame.copy()
        for r in [(0,0,fw,bw),(0,fh-bw,fw,fh),(0,0,bw,fh),(fw-bw,0,fw,fh)]:
            cv2.rectangle(glow, (r[0],r[1]),(r[2],r[3]), (0,0,255), -1)
        cv2.addWeighted(glow, alpha, frame, 1-alpha, 0, frame)

    # ── Sidebar panel ─────────────────────────────────────────────────────────
    def _build_sidebar(self, assessments, fps, fh) -> np.ndarray:
        sb = np.zeros((fh, SIDEBAR_W, 3), dtype=np.uint8)
        sb[:] = (14, 16, 22)

        y = 0

        # — Header —
        header_h = 44
        cv2.rectangle(sb, (0,0), (SIDEBAR_W, header_h), (0, 120, 160), -1)
        cv2.putText(sb, "PATHWISE", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.70, (220, 240, 255), 2, cv2.LINE_AA)
        backend = config.MODEL_BACKEND.upper()
        bcol = (40,220,100) if config.MODEL_BACKEND == "idd" else (200,180,50)
        cv2.putText(sb, f"[{backend}]", (142, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, bcol, 1, cv2.LINE_AA)
        y = header_h

        # — Stats strip —
        stats_h = 30
        cv2.rectangle(sb, (0,y), (SIDEBAR_W, y+stats_h), (20,24,32), -1)
        fps_col = (50,255,120) if fps>=20 else (0,200,255) if fps>=10 else (0,80,255)
        cv2.putText(sb, f"FPS  {fps:.0f}", (10, y+20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.46, fps_col, 1, cv2.LINE_AA)
        cv2.line(sb, (80,y+6),(80,y+stats_h-6),(50,55,70),1)
        cv2.putText(sb, f"TRACKS  {len(assessments)}", (88, y+20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.46, (180,180,210), 1, cv2.LINE_AA)
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        (tw,_),_ = cv2.getTextSize(ts, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
        cv2.putText(sb, ts, (SIDEBAR_W-tw-8, y+20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (100,105,125), 1, cv2.LINE_AA)
        y += stats_h

        # — BEV Radar —
        bev_label_h = 22
        cv2.rectangle(sb, (0,y), (SIDEBAR_W, y+bev_label_h), (0,90,120), -1)
        cv2.putText(sb, "BEV  RADAR", (SIDEBAR_W//2 - 45, y+15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180,230,255), 1, cv2.LINE_AA)
        y += bev_label_h

        # Draw BEV
        bev_y_start = y
        bev_panel = self._draw_bev(assessments)
        bev_panel_h = bev_panel.shape[0]
        bev_panel_w = bev_panel.shape[1]
        x_off = (SIDEBAR_W - bev_panel_w) // 2
        sb[y:y+bev_panel_h, x_off:x_off+bev_panel_w] = bev_panel
        y += bev_panel_h + 8

        # — Hazard Table —
        if assessments and y + 20 < fh:
            table_label_h = 22
            cv2.rectangle(sb, (0,y), (SIDEBAR_W, y+table_label_h), (20,24,34), -1)
            cv2.putText(sb, "ACTOR SUMMARY", (8, y+15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (100,110,140), 1, cv2.LINE_AA)
            y += table_label_h

            # Column headers
            cv2.putText(sb, "ID   CLASS        DIST   SPD", (6, y+12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.32, (70,75,100), 1, cv2.LINE_AA)
            y += 16
            cv2.line(sb, (4,y),(SIDEBAR_W-4,y),(40,45,60),1)
            y += 4

            row_h = 22
            sorted_actors = sorted(assessments, key=lambda a: a.actor.distance_m)
            for ha in sorted_actors:
                if y + row_h > fh - 10:
                    break
                col = ha.bbox_color
                det = ha.actor.detection

                # Row background on critical/warning
                if ha.hazard_level == HazardLevel.CRITICAL:
                    cv2.rectangle(sb, (2,y), (SIDEBAR_W-2, y+row_h-2), (40,0,0), -1)
                elif ha.hazard_level == HazardLevel.WARNING:
                    cv2.rectangle(sb, (2,y), (SIDEBAR_W-2, y+row_h-2), (30,25,0), -1)

                # Hazard dot
                cv2.circle(sb, (10, y+11), 4, col, -1)

                # Text columns
                name = det.class_name[:7]
                dist = f"{ha.actor.distance_m:.1f}m"
                spd  = f"{abs(ha.actor.velocity_kmh):.0f}"
                ttc  = f" T{ha.ttc:.1f}" if ha.ttc else ""
                row  = f"#{det.track_id:<3} {name:<8} {dist:>5}  {spd:>3}km/h{ttc}"
                cv2.putText(sb, row, (20, y+14),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.32, (200,205,220), 1, cv2.LINE_AA)
                y += row_h

        # — Footer —
        cv2.rectangle(sb, (0, fh-24), (SIDEBAR_W, fh), (10,12,18), -1)
        cv2.line(sb, (0,fh-24),(SIDEBAR_W,fh-24),(0,80,100),1)
        cv2.putText(sb, "Edge-AI Road Safety System", (6, fh-8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.30, (55,60,80), 1, cv2.LINE_AA)

        return sb

    # ── BEV radar panel ───────────────────────────────────────────────────────
    def _draw_bev(self, assessments) -> np.ndarray:
        mm = np.zeros((BEV_H, BEV_W, 3), dtype=np.uint8)
        mm[:] = (14, 18, 26)

        ego_x = BEV_W // 2
        ego_y = BEV_H - EGO_MARGIN

        # Distance rings
        for dist_m, ring_col in [(10,(30,38,55)),(20,(38,46,65)),(30,(28,36,50))]:
            ry = ego_y - int(dist_m * MM_SCALE)
            if ry > 5:
                rx = int(dist_m * MM_SCALE * 0.55)
                cv2.ellipse(mm, (ego_x, ego_y), (rx, int(dist_m*MM_SCALE)),
                            0, 180, 360, ring_col, 1)
                lbl = f"{dist_m}m"
                (lw,_),_ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.26, 1)
                cv2.putText(mm, lbl, (ego_x - lw//2 - 1, ry - 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.26, (55,62,85), 1)

        # Lane lines — ego + adjacent (3.5m each side)
        for lat_m, is_ego in [(0,True),(-3.5,False),(3.5,False)]:
            lx = ego_x + int(lat_m * MM_SCALE)
            col = (65,70,100) if is_ego else (40,44,65)
            style = cv2.LINE_AA
            cv2.line(mm, (lx, 0), (lx, ego_y), col, 1 if is_ego else 1)

        # Actors
        for ha in assessments:
            lat  = ha.actor.lateral_distance_m
            dist = ha.actor.distance_m
            col  = ha.bbox_color
            is_crit = ha.hazard_level == HazardLevel.CRITICAL

            ax = ego_x + int(lat * MM_SCALE)
            ay = ego_y - int(dist * MM_SCALE)

            # Out of range — draw arrow at edge
            if ay < 4:
                ax_clamped = max(6, min(BEV_W-6, ax))
                cv2.arrowedLine(mm, (ax_clamped, 14), (ax_clamped, 4), col, 1, tipLength=0.5)
                cv2.putText(mm, f"#{ha.actor.track_id}", (ax_clamped+3, 14),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.25, col, 1)
                continue

            ax = max(6, min(BEV_W-6, ax))
            ay = max(6, min(ego_y-2, ay))

            # Glow for critical
            if is_crit:
                pulse = int(abs(math.sin(self._frame_count*0.15))*4)
                cv2.circle(mm, (ax,ay), 7+pulse, col, 1)

            # Actor dot
            r = 5 if is_crit else 4
            cv2.circle(mm, (ax,ay), r, col, -1)
            cv2.circle(mm, (ax,ay), r, (255,255,255), 1)   # white outline

            # Velocity arrow
            vpx = int(ha.actor.velocity_mps * MM_SCALE * 0.6)
            if abs(vpx) > 3:
                ay2 = max(4, min(BEV_H-4, ay - vpx))
                cv2.arrowedLine(mm, (ax,ay), (ax,ay2), col, 1, tipLength=0.4)

            # ID + distance tag
            tag = f"#{ha.actor.track_id} {dist:.0f}m"
            tx  = min(ax + 7, BEV_W - 40)
            cv2.putText(mm, tag, (tx, ay+3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.26, col, 1)

        # Ego triangle
        ev = np.array([[ego_x,ego_y-11],[ego_x-6,ego_y+7],[ego_x+6,ego_y+7]], np.int32)
        cv2.fillPoly(mm, [ev], (0,195,255))
        cv2.polylines(mm, [ev], True, (255,255,255), 1)
        cv2.putText(mm, "EGO", (ego_x-10, ego_y+20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0,155,190), 1)

        # Panel border
        cv2.rectangle(mm, (0,0), (BEV_W-1, BEV_H-1), (0,120,160), 1)

        return mm
