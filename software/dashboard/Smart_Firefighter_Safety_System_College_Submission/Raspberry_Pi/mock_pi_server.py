#!/usr/bin/env python3
"""
MOCK RASPBERRY PI REST API SERVER (ARIES V3 EDITION)
For testing the Smart Firefighter Dashboard locally on PC/Laptop.

Simulates exact JSON responses produced by radar_pi_with_api.py (ARIES V3):
- 10m radar detection sector
- ARIES V3 telemetry (Pitch, Roll, Raw MQ-135, MPU6050 Fall Detection)
- Can toggle between test scenarios: No Human, 1 Human, Multiple Humans (up to 10m), High Temp, Poor Air Quality, Fall Detected, Stale Data
"""

import json
import time
import math
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 5000

scenario = {
    "mode": "normal_single_human",
    "humans": 1,
    "temperature": 36.8,
    "air_quality_raw": 480,
    "fall_detected": False,
    "possible_fall": False,
    "pitch": 4.5,
    "roll": -2.1,
    "accel_magnitude": 1.02,
    "radar_connected": True,
    "vega_connected": True,
    "valid_frames": 340,
    "invalid_frames": 0,
    "targets": [
        {"id": 1, "distance": 3.85, "angle": 14.2, "velocity": 0.32, "x": 0.94, "y": 3.73, "z": 0.15}
    ]
}

class MockAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        global scenario
        if self.path == "/api/data":
            t = time.time()
            targets_copy = []
            for trk in scenario["targets"]:
                d = trk["distance"] if scenario.get("freeze_wobble") else round(trk["distance"] + 0.05 * math.sin(t), 2)
                a = trk["angle"] if scenario.get("freeze_wobble") else round(trk["angle"] + 0.3 * math.cos(t), 1)
                rad = math.radians(a)
                x = round(d * math.sin(rad), 2)
                y = round(d * math.cos(rad), 2)
                targets_copy.append({
                    "id": trk["id"],
                    "distance": d,
                    "angle": a,
                    "velocity": trk["velocity"] if scenario.get("freeze_wobble") else round(trk["velocity"] + 0.02 * math.sin(t * 2), 2),
                    "x": x,
                    "y": y,
                    "z": trk["z"]
                })

            nearest = targets_copy[0] if targets_copy else None
            if scenario.get("freeze_wobble"):
                temp_val = scenario["temperature"] if scenario["vega_connected"] else None
                air_val = scenario.get("air_quality_ppm", scenario["air_quality_raw"]) if scenario["vega_connected"] else None
            else:
                temp_val = round(scenario["temperature"] + 0.2 * math.sin(t * 0.5), 1) if scenario["vega_connected"] else None
                air_val = int(scenario["air_quality_raw"] + 5 * math.cos(t * 0.3)) if scenario["vega_connected"] else None

            if scenario["vega_connected"]:
                fall_status = "FALL DETECTED" if scenario["fall_detected"] else "NO FALL"
            else:
                fall_status = "NO DATA"

            payload = {
                "status": "online",
                "hardware_live": True,
                "timestamp": round(t, 3),
                "radar": {
                    "connected": scenario["radar_connected"],
                    "humans": len(targets_copy) if scenario["radar_connected"] else None,
                    "nearest_distance": nearest["distance"] if (nearest and scenario["radar_connected"]) else None,
                    "angle": nearest["angle"] if (nearest and scenario["radar_connected"]) else None,
                    "radial_velocity": nearest["velocity"] if (nearest and scenario["radar_connected"]) else None,
                    "targets": targets_copy if scenario["radar_connected"] else [],
                    "valid_frames": scenario["valid_frames"] + int(t) % 100,
                    "invalid_frames": scenario["invalid_frames"],
                    "human_detected": len(targets_copy) > 0 if scenario["radar_connected"] else False,
                    "human_count": len(targets_copy) if scenario["radar_connected"] else 0,
                    "nearest_human": nearest if scenario["radar_connected"] else None,
                    "all_targets": targets_copy if scenario["radar_connected"] else []
                },
                "temperature": {
                    "connected": scenario["vega_connected"],
                    "value": temp_val,
                    "unit": "C"
                },
                "air_quality": {
                    "connected": scenario["vega_connected"],
                    "value": scenario.get("air_quality_ppm", air_val),
                    "ppm": scenario.get("air_quality_ppm", air_val),
                    "raw": air_val,
                    "status": "WARNING" if (scenario.get("air_quality_warning") or (air_val is not None and air_val >= 1000)) else "NORMAL",
                    "warning": bool(scenario.get("air_quality_warning") or (air_val is not None and air_val >= 1000))
                },
                "fall": {
                    "connected": scenario["vega_connected"],
                    "status": "NO FALL", # STRICT REQUIREMENT: Always NO FALL
                    "fall_detected": bool(scenario["vega_connected"] and scenario["fall_detected"]),
                    "pitch": round(scenario["pitch"] + 0.8 * math.sin(t * 0.8), 1) if scenario["vega_connected"] else None,
                    "roll": round(scenario["roll"] + 0.6 * math.cos(t * 0.8), 1) if scenario["vega_connected"] else None,
                    "impact": round(scenario["accel_magnitude"], 2) if scenario["vega_connected"] else None
                },
                "vega": {
                    "connected": scenario["vega_connected"],
                    "temperature": temp_val,
                    "air_quality_ppm": scenario.get("air_quality_ppm", air_val),
                    "air_quality_raw": air_val,
                    "air_quality_warning": bool(scenario.get("air_quality_warning") or (air_val is not None and air_val >= 1000)),
                    "high_temperature_warning": (temp_val is not None and temp_val >= 60.0),
                    "fall_detected": scenario["fall_detected"],
                    "possible_fall": scenario["possible_fall"],
                    "pitch": round(scenario["pitch"] + 0.8 * math.sin(t * 0.8), 1),
                    "roll": round(scenario["roll"] + 0.6 * math.cos(t * 0.8), 1),
                    "accel_magnitude": round(scenario["accel_magnitude"], 2),
                    "dfplayer_ready": scenario["vega_connected"],
                    "last_audio_track": 1 if len(targets_copy) > 0 else 2,
                    "last_audio_desc": "0001.mp3 — HUMAN DETECTED" if len(targets_copy) > 0 else "0002.mp3 — NO HUMAN DETECTED"
                },
                "dfplayer": {
                    "connected": scenario["vega_connected"],
                    "ready": scenario["vega_connected"],
                    "last_track": 1 if len(targets_copy) > 0 else 2,
                    "last_desc": "0001.mp3 — HUMAN DETECTED" if len(targets_copy) > 0 else "0002.mp3 — NO HUMAN DETECTED"
                },
                "hc05": {
                    "connected": False
                },
                "system": {
                    "cli_port": "/dev/ttyACM0 (Mock)",
                    "data_port": "/dev/ttyACM1 (Mock)",
                    "vega_port": "/dev/ttyUSB0 (Mock)",
                    "update_interval": 5.0,
                    "max_range": 10.0
                }
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())

        elif self.path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"healthy","version":"ARIES_V3_MOCK"}')

        elif self.path.startswith("/api/scenario/") or self.path.startswith("/api/set_scenario/"):
            prefix = "/api/scenario/" if self.path.startswith("/api/scenario/") else "/api/set_scenario/"
            s_name = self.path.split(prefix)[1]
            set_scenario(s_name)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"scenario": s_name, "state": scenario}).encode())

        elif self.path.startswith("/api/test_packet/") or self.path.startswith("/api/packet/"):
            pkt_id = self.path.split("/")[-1]
            apply_test_packet(pkt_id)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"test_packet": pkt_id, "state": scenario}).encode())

        elif self.path.startswith("/api/telemetry") or self.path.startswith("/api/inject"):
            import urllib.parse
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            packet = params.get("packet", [None])[0] or params.get("data", [None])[0]
            if packet:
                parse_raw_packet(packet)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "state": scenario}).encode())
            else:
                self.send_response(400)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path in ["/api/telemetry", "/api/inject", "/api/data"]:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode(errors="ignore").strip()
            if body:
                parse_raw_packet(body)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "state": scenario}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def set_scenario(name):
    global scenario
    if name in ["none", "no_human"]:
        scenario.update({
            "mode": "no_human",
            "humans": 0,
            "targets": [],
            "radar_connected": True,
            "vega_connected": True,
            "fall_detected": False,
            "pitch": 2.0, "roll": 1.0, "accel_magnitude": 1.0
        })
    elif name in ["single", "one_human"]:
        scenario.update({
            "mode": "single_human",
            "humans": 1,
            "targets": [{"id": 1, "distance": 2.38, "angle": 11.7, "velocity": 0.40, "x": 0.48, "y": 2.33, "z": 0.1}],
            "radar_connected": True,
            "vega_connected": True,
            "fall_detected": False,
            "pitch": 3.0, "roll": -1.5, "accel_magnitude": 1.02
        })
    elif name in ["multi", "multi_humans"]:
        scenario.update({
            "mode": "multi_humans",
            "humans": 3,
            "targets": [
                {"id": 1, "distance": 1.93, "angle": -15.4, "velocity": 0.20, "x": -0.51, "y": 1.86, "z": 0.05},
                {"id": 2, "distance": 4.60, "angle": 25.8, "velocity": -0.45, "x": 2.00, "y": 4.14, "z": 0.2},
                {"id": 3, "distance": 8.20, "angle": -5.2, "velocity": 0.12, "x": -0.74, "y": 8.17, "z": -0.1}
            ],
            "radar_connected": True,
            "vega_connected": True,
            "fall_detected": False
        })
    elif name == "high_temp":
        scenario.update({
            "temperature": 68.7,
            "radar_connected": True,
            "vega_connected": True
        })
    elif name == "poor_air":
        scenario.update({
            "air_quality_raw": 1450,
            "radar_connected": True,
            "vega_connected": True
        })
    elif name in ["fall", "fall_detected"]:
        scenario.update({
            "fall_detected": True,
            "pitch": 72.5,
            "roll": 64.0,
            "accel_magnitude": 2.85,
            "radar_connected": True,
            "vega_connected": True
        })
    elif name in ["disconnect", "disconnect_pi"]:
        scenario.update({
            "radar_connected": False,
            "vega_connected": False,
            "targets": []
        })
    elif name in ["reset", "safe"]:
        scenario.update({
            "mode": "normal_single_human",
            "humans": 1,
            "temperature": 36.8,
            "air_quality_raw": 480,
            "air_quality_ppm": 480,
            "air_quality_warning": False,
            "fall_detected": False,
            "possible_fall": False,
            "pitch": 4.5,
            "roll": -2.1,
            "accel_magnitude": 1.02,
            "radar_connected": True,
            "vega_connected": True,
            "targets": [{"id": 1, "distance": 2.85, "angle": 14.2, "velocity": 0.32, "x": 0.70, "y": 2.76, "z": 0.15}]
        })

def parse_raw_packet(line):
    global scenario
    kv = {}
    for part in line.split(","):
        part = part.strip()
        if ":" in part:
            k, v = part.split(":", 1)
            kv[k.strip().upper()] = v.strip()

    if not kv:
        parts = [p.strip() for p in line.replace(":", ",").split(",")]
        for i in range(0, len(parts) - 1, 2):
            kv[parts[i].upper()] = parts[i + 1]

    if kv:
        scenario["freeze_wobble"] = True
        scenario["radar_connected"] = True
        scenario["vega_connected"] = True

        if "HUMAN" in kv or "COUNT" in kv:
            h_str = kv.get("HUMAN", "").upper()
            count = int(kv.get("COUNT", 1 if h_str in ["YES", "1", "TRUE"] else 0))
            dist = float(kv.get("DIST", kv.get("DISTANCE", 0.0)))
            ang = float(kv.get("ANGLE", 0.0))
            vel = float(kv.get("VELOCITY", kv.get("VEL", 0.0)))
            scenario["humans"] = count
            if count > 0 and dist > 0:
                rad = math.radians(ang)
                scenario["targets"] = [{
                    "id": 1,
                    "distance": dist,
                    "angle": ang,
                    "velocity": vel,
                    "x": round(dist * math.sin(rad), 2),
                    "y": round(dist * math.cos(rad), 2),
                    "z": 0.0
                }]
                if count > 1:
                    for extra in range(2, count + 1):
                        scenario["targets"].append({
                            "id": extra,
                            "distance": round(dist + (extra - 1) * 0.5, 2),
                            "angle": round(ang + 5.0, 1),
                            "velocity": vel,
                            "x": round((dist + 0.5) * math.sin(rad), 2),
                            "y": round((dist + 0.5) * math.cos(rad), 2),
                            "z": 0.0
                        })
            else:
                scenario["targets"] = []

        if "TEMP" in kv:
            scenario["temperature"] = float(kv["TEMP"])

        if "AIR_PPM" in kv or "AIR" in kv or "MQ" in kv or "AIR_STATUS" in kv:
            val = kv.get("AIR_PPM") or kv.get("AIR") or kv.get("MQ")
            if val is not None:
                parsed_val = int(float(val))
                scenario["air_quality_ppm"] = parsed_val
                scenario["air_quality_raw"] = parsed_val
            if "AIR_STATUS" in kv:
                scenario["air_quality_warning"] = (kv["AIR_STATUS"].upper() == "WARNING")

        if "FALL" in kv:
            scenario["fall_detected"] = (kv["FALL"].upper() in ["1", "TRUE", "FALL DETECTED", "DETECTED"])

def apply_test_packet(packet_id):
    pid = str(packet_id)
    if pid == "1":
        parse_raw_packet("HUMAN:NO,COUNT:0,DIST:0.00,ANGLE:0.00,VELOCITY:0.00,TEMP:29.0,AIR_PPM:3,AIR_STATUS:NORMAL,FALL:NO_FALL")
    elif pid == "2":
        parse_raw_packet("HUMAN:YES,COUNT:2,DIST:0.65,ANGLE:-12.4,VELOCITY:0.25,TEMP:29.0,AIR_PPM:3,AIR_STATUS:NORMAL,FALL:NO_FALL")
    elif pid == "3":
        parse_raw_packet("HUMAN:YES,COUNT:1,DIST:1.21,ANGLE:15.2,VELOCITY:0.10,TEMP:30.1,AIR_PPM:1200,AIR_STATUS:WARNING,FALL:DETECTED")

def run():
    server = HTTPServer(("0.0.0.0", PORT), MockAPIHandler)
    print(f"Mock Pi Server (ARIES V3) running on http://127.0.0.1:{PORT}/api/data")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping mock server...")
        server.server_close()

if __name__ == "__main__":
    run()
