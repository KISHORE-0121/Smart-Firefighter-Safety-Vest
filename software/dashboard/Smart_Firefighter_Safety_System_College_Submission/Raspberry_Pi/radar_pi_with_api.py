#!/usr/bin/env python3
"""
=============================================================================
SMART FIREFIGHTER SAFETY SYSTEM — RASPBERRY PI BACKEND & API GATEWAY
=============================================================================
Hardware Bridge:
  1. IWR6843AOP Radar (CLI @ 115200, DATA @ 921600)
  2. VEGA ARIES V3 (USB Serial @ 115200)
  3. Non-blocking CORS-enabled REST API on 0.0.0.0:5000

Features:
  - NEVER terminates or crashes if USB hardware is unplugged.
  - Auto-scans and hot-plugs radar and VEGA dynamically.
  - Strict hardware-only telemetry schema.
=============================================================================
"""

import serial
import serial.tools.list_ports
import time
import os
import struct
import math
import glob
import json
import threading
import sys
from collections import deque
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============================================================
# CONFIGURATION & BAUD RATES
# ============================================================

CLI_BAUD = 115200
DATA_BAUD = 921600
VEGA_BAUD = 115200

CONFIG_FILENAME = "AOP_6m_default.cfg"
UPDATE_INTERVAL = 5.0
MAX_HUMANS = 5

API_HOST = "0.0.0.0"
API_PORT = 5000

MAGIC_WORD = b'\x02\x01\x04\x03\x06\x05\x08\x07'

HEADER_SIZE = 40
PACKET_LENGTH_OFFSET = 12
NUM_TLVS_OFFSET = 32

TARGET_LIST_TLV = 1010
TARGET_SIZE = 112
PRESENCE_TLV = 1021
MAX_TLVS = 100

# Area Filter Bounds (10m sector)
X_MIN = -5.0
X_MAX = 5.0
Y_MIN = 0.1
Y_MAX = 10.0
Z_MIN = -2.0
Z_MAX = 3.0

# Outlier Rejection
MEDIAN_WINDOW = 5
MIN_HISTORY_FOR_REJECTION = 3
DISTANCE_MEDIAN_THRESHOLD = 1.0
distance_history = {}

# ============================================================
# LIVE HARDWARE SHARED STATE
# ============================================================

state_lock = threading.Lock()
radar_state = {
    "connected": False,
    "last_packet": 0,
    "valid_frames": 0,
    "invalid_frames": 0,
    "presence": False,
    "targets": []
}

vega_state_lock = threading.Lock()
vega_state = {
    "connected": False,
    "last_packet": 0,
    "temperature": None,
    "mlx_connected": False,
    "air_quality_raw": None,
    "air_quality_ppm": None,
    "air_quality_warning": False,
    "mq_connected": False,
    "fall_detected": False,
    "possible_fall": False,
    "pitch": 0.0,
    "roll": 0.0,
    "impact": 1.0,
    "mpu_connected": False,
    "dfplayer_ready": False,
    "last_track": 0,
    "last_desc": "Standby"
}

ports_info = {
    "cli_port": None,
    "data_port": None,
    "vega_port": None
}

running = True
cli_serial = None
radar_serial = None
vega_serial = None

# ============================================================
# PORT SCANNING & CONFIG UTILITIES
# ============================================================

def find_config_file():
    search_locations = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Radar", CONFIG_FILENAME),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "Radar", CONFIG_FILENAME),
        os.path.join(os.getcwd(), CONFIG_FILENAME),
        os.path.join(os.getcwd(), "Radar", CONFIG_FILENAME),
        os.path.expanduser(os.path.join("~", CONFIG_FILENAME))
    ]
    for path in search_locations:
        if os.path.isfile(path):
            return path
    for root in [os.path.dirname(os.path.abspath(__file__)), os.getcwd(), os.path.expanduser("~")]:
        try:
            for path in glob.glob(os.path.join(root, "**", CONFIG_FILENAME), recursive=True):
                if os.path.isfile(path):
                    return path
        except Exception:
            pass
    return None

def get_serial_ports():
    ports = []
    for p in serial.tools.list_ports.comports():
        device = p.device
        if (
            device.startswith("/dev/ttyUSB") or
            device.startswith("/dev/ttyACM") or
            device.startswith("/dev/ttyS") or
            device.startswith("/dev/ttyAMA") or
            device.startswith("/dev/serial/by-id/") or
            device.startswith("COM")
        ):
            ports.append(device)
    return ports

def check_cli_port(port):
    ser = None
    try:
        ser = serial.Serial(port, CLI_BAUD, timeout=0.5)
        time.sleep(0.15)
        ser.reset_input_buffer()
        ser.write(b"version\r\n")
        time.sleep(0.3)
        response = ser.read(500)
        text = response.decode(errors="ignore").lower()
        for keyword in ["version", "mmwave", "iwr6843", "demo"]:
            if keyword in text:
                return True
    except Exception:
        pass
    finally:
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass
    return False

def detect_cli_port():
    ports = get_serial_ports()
    for port in ports:
        if check_cli_port(port):
            return port
    return None

def check_data_port(port, wait_time=2.5):
    ser = None
    try:
        ser = serial.Serial(port, DATA_BAUD, timeout=0.1)
        start_time = time.time()
        buffer = b""
        while time.time() - start_time < wait_time:
            data = ser.read(ser.in_waiting or 1)
            if data:
                buffer += data
                if MAGIC_WORD in buffer:
                    return True
            time.sleep(0.001)
    except Exception:
        pass
    finally:
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass
    return False

def detect_data_port(cli_port):
    ports = get_serial_ports()
    for port in ports:
        if port == cli_port:
            continue
        if check_data_port(port, wait_time=2.5):
            return port
    return None

def find_vega_port(cli_port, data_port):
    ports = get_serial_ports()
    for port in ports:
        if port != cli_port and port != data_port:
            return port
    return None

def parse_sensor_line(line):
    """
    Robust parser for VEGA ARIES V3 sensor telemetry.
    Supports:
      1. V,temp,mq,fall,possibleFall,pitch,roll,impact,mlxOk,mpuOk,mqOk
      2. Key-Value: TEMP:xx,AIR:xx,FALL:xx,PITCH:xx,ROLL:xx,IMPACT:xx
      3. JSON: {"temp": xx, "mq": xx, "fall": "SAFE", ...}
      4. HC-05 format: HUMAN,count,dist,angle,vel,TEMP,temp,AIR,raw,FALL,fall,PITCH,pitch,ROLL,roll
    """
    global vega_state
    line = line.strip()
    if not line:
        return False

    with vega_state_lock:
        now = time.time()
        # 1. Format: V,temp,mq,fall,possibleFall,pitch,roll,impact,mlxOk,mpuOk,mqOk
        if line.startswith("V,"):
            parts = line.split(",")
            if len(parts) >= 3:
                vega_state["connected"] = True
                vega_state["last_packet"] = now

                # Temperature (MLX90614)
                try:
                    t_val = float(parts[1])
                    if -40.0 <= t_val <= 380.0:
                        vega_state["temperature"] = round(t_val, 1)
                        vega_state["mlx_connected"] = True
                    else:
                        vega_state["temperature"] = None
                        vega_state["mlx_connected"] = False
                except Exception:
                    vega_state["temperature"] = None
                    vega_state["mlx_connected"] = False

                # MQ-135 Gas / Air Quality
                try:
                    mq_val = int(float(parts[2]))
                    if 0 <= mq_val <= 1023:
                        vega_state["air_quality_raw"] = mq_val
                        vega_state["mq_connected"] = True
                    else:
                        vega_state["air_quality_raw"] = None
                        vega_state["mq_connected"] = False
                except Exception:
                    vega_state["air_quality_raw"] = None
                    vega_state["mq_connected"] = False

                # Fall Detection / MPU6050
                if len(parts) >= 4:
                    vega_state["fall_detected"] = (int(float(parts[3])) == 1)
                if len(parts) >= 5:
                    vega_state["possible_fall"] = (int(float(parts[4])) == 1)
                if len(parts) >= 8:
                    try:
                        vega_state["pitch"] = round(float(parts[5]), 1)
                        vega_state["roll"] = round(float(parts[6]), 1)
                        vega_state["impact"] = round(float(parts[7]), 2)
                        vega_state["mpu_connected"] = True
                    except Exception:
                        vega_state["mpu_connected"] = False

                # Health flags if provided
                if len(parts) >= 9:
                    vega_state["mlx_connected"] = (int(float(parts[8])) == 1) and (vega_state["temperature"] is not None)
                if len(parts) >= 10:
                    vega_state["mpu_connected"] = (int(float(parts[9])) == 1)
                if len(parts) >= 11:
                    flag = int(float(parts[10]))
                    vega_state["mq_connected"] = (flag == 1) or (vega_state["air_quality_raw"] is not None)
                return True

        # 2. Key-Value or HC-05 format: HUMAN:xx,COUNT:xx,DIST:xx,ANGLE:xx,VELOCITY:xx,TEMP:xx,AIR_PPM:xx,AIR_STATUS:xx,FALL:xx...
        if any(k in line.upper() for k in ["TEMP", "AIR", "MQ", "HUMAN", "COUNT"]):
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
                vega_state["connected"] = True
                vega_state["last_packet"] = now

                # Radar fields if present
                if "HUMAN" in kv or "COUNT" in kv:
                    try:
                        h_str = kv.get("HUMAN", "").upper()
                        count = int(kv.get("COUNT", 1 if h_str in ["YES", "1", "TRUE"] else 0))
                        dist = float(kv.get("DIST", kv.get("DISTANCE", 0.0)))
                        ang = float(kv.get("ANGLE", 0.0))
                        vel = float(kv.get("VELOCITY", kv.get("VEL", 0.0)))
                        with state_lock:
                            radar_state["connected"] = True
                            radar_state["last_packet"] = now
                            if count > 0 and dist > 0:
                                rad = math.radians(ang)
                                radar_state["targets"] = [{
                                    "id": 1,
                                    "distance": round(dist, 2),
                                    "angle": round(ang, 1),
                                    "velocity": round(vel, 2),
                                    "x": round(dist * math.sin(rad), 2),
                                    "y": round(dist * math.cos(rad), 2),
                                    "z": 0.0
                                }]
                            else:
                                radar_state["targets"] = []
                    except Exception:
                        pass

                if "TEMP" in kv:
                    try:
                        t_val = float(kv["TEMP"])
                        if -40.0 <= t_val <= 380.0:
                            vega_state["temperature"] = round(t_val, 1)
                            vega_state["mlx_connected"] = True
                    except Exception:
                        pass

                if "AIR_PPM" in kv or "AIR" in kv or "MQ" in kv or "AIR_STATUS" in kv:
                    try:
                        val = kv.get("AIR_PPM") or kv.get("AIR") or kv.get("MQ")
                        if val is not None:
                            val_num = int(float(val))
                            if val_num >= 0:
                                vega_state["air_quality_raw"] = val_num
                                vega_state["air_quality_ppm"] = val_num
                                vega_state["mq_connected"] = True
                        if "AIR_STATUS" in kv:
                            vega_state["mq_connected"] = True
                            vega_state["air_quality_warning"] = (kv["AIR_STATUS"].upper() == "WARNING")
                    except Exception:
                        pass

                if "PITCH" in kv and "ROLL" in kv:
                    try:
                        vega_state["pitch"] = round(float(kv["PITCH"]), 1)
                        vega_state["roll"] = round(float(kv["ROLL"]), 1)
                        vega_state["impact"] = round(float(kv.get("IMPACT", 1.0)), 2)
                        vega_state["mpu_connected"] = True
                    except Exception:
                        pass

                if "FALL" in kv:
                    val = kv["FALL"].upper()
                    if val in ["NO_DATA", "NO DATA", "DISCONNECTED"]:
                        vega_state["mpu_connected"] = False
                        vega_state["fall_detected"] = False
                        vega_state["possible_fall"] = False
                    else:
                        vega_state["mpu_connected"] = True
                        vega_state["fall_detected"] = (val in ["1", "TRUE", "FALL DETECTED", "DETECTED"])
                        vega_state["possible_fall"] = (val in ["POSSIBLE", "CHECKING", "POSSIBLE FALL"])
                return True

        # 3. JSON format: {"temp": 31.5, "mq": 642, ...}
        if line.startswith("{") and line.endswith("}"):
            try:
                js = json.loads(line)
                vega_state["connected"] = True
                vega_state["last_packet"] = now
                if "temp" in js:
                    vega_state["temperature"] = round(float(js["temp"]), 1)
                    vega_state["mlx_connected"] = True
                if "mq" in js or "air" in js:
                    vega_state["air_quality_raw"] = int(float(js.get("mq") or js.get("air")))
                    vega_state["mq_connected"] = True
                if "pitch" in js and "roll" in js:
                    vega_state["pitch"] = round(float(js["pitch"]), 1)
                    vega_state["roll"] = round(float(js["roll"]), 1)
                    vega_state["impact"] = round(float(js.get("impact", 1.0)), 2)
                    vega_state["mpu_connected"] = True
                if "fall" in js:
                    vega_state["fall_detected"] = (str(js["fall"]).upper() in ["1", "TRUE", "FALL DETECTED"])
                return True
            except Exception:
                pass

    return False

def configure_radar(ser, config_file):
    try:
        with open(config_file, "r") as file:
            lines = file.readlines()
    except Exception as e:
        print(f"[RADAR] Cannot open config file: {e}")
        return False

    print(f"[RADAR] Sending configuration ({len(lines)} lines)...")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        try:
            ser.reset_input_buffer()
            ser.write((line + "\r\n").encode())
            ser.flush()

            deadline = time.time() + 1.5
            response = b""
            while time.time() < deadline:
                chunk = ser.read(ser.in_waiting or 1)
                if chunk:
                    response += chunk
                    text = response.decode(errors="ignore")
                    if "Done" in text:
                        break
                    if "Error" in text or "error" in text:
                        print(f"[RADAR] CLI Error: {text.strip()}")
                        return False
                else:
                    time.sleep(0.01)
        except Exception as e:
            print(f"[RADAR] Config send error: {e}")
            return False

    ser.flush()
    time.sleep(1.0)
    return True

# ============================================================
# VEGA ARIES V3 TRANSMISSION & INGESTION
# ============================================================

def send_to_vega(ser, count, distance, angle, velocity):
    if ser is None or not ser.is_open:
        return
    try:
        if count > 0:
            msg = f"H,{count},{distance:.2f},{angle:.2f},{velocity:.2f}\n"
        else:
            msg = "N,0,0,0,0\n"
        ser.write(msg.encode())
        ser.flush()
    except Exception:
        pass

def vega_telemetry_listener(ser):
    """
    Listens for telemetry emitted by VEGA ARIES V3.
    Continuously parses incoming lines without crashing.
    """
    global vega_state
    port_name = ser.port if ser else "unknown"
    baud = ser.baudrate if ser else 115200
    print(f"[SENSORS] VEGA ARIES V3 telemetry listener active on {port_name} ({baud} baud).")
    buffer = ""
    while running and ser and ser.is_open:
        try:
            if ser.in_waiting:
                chunk = ser.read(ser.in_waiting).decode(errors="ignore")
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    parse_sensor_line(line)
            else:
                time.sleep(0.01)
        except Exception as e:
            print(f"[SENSORS] Serial read error on {port_name}: {e}")
            break

    with vega_state_lock:
        vega_state["connected"] = False
    print(f"[SENSORS] Serial connection closed or lost on {port_name}.")

# ============================================================
# RADAR FRAME PARSER
# ============================================================

def decode_targets(payload):
    targets_found = {}
    if len(payload) < TARGET_SIZE:
        return targets_found

    number_targets = len(payload) // TARGET_SIZE
    for i in range(number_targets):
        offset = i * TARGET_SIZE
        try:
            tid = struct.unpack_from("<I", payload, offset)[0]
            x = struct.unpack_from("<f", payload, offset + 4)[0]
            y = struct.unpack_from("<f", payload, offset + 8)[0]
            z = struct.unpack_from("<f", payload, offset + 12)[0]
            vx = struct.unpack_from("<f", payload, offset + 16)[0]
            vy = struct.unpack_from("<f", payload, offset + 20)[0]
            vz = struct.unpack_from("<f", payload, offset + 24)[0]

            if not all(math.isfinite(v) for v in [x, y, z, vx, vy, vz]):
                continue

            distance = math.sqrt(x * x + y * y + z * z)
            if distance <= 0:
                continue

            # Median outlier filtering
            history = distance_history.setdefault(tid, deque(maxlen=MEDIAN_WINDOW))
            if len(history) >= MIN_HISTORY_FOR_REJECTION:
                sorted_history = sorted(history)
                median_dist = sorted_history[len(sorted_history) // 2]
                if abs(distance - median_dist) > DISTANCE_MEDIAN_THRESHOLD:
                    continue
            history.append(distance)

            if x < X_MIN or x > X_MAX or y < Y_MIN or y > Y_MAX or z < Z_MIN or z > Z_MAX:
                continue

            angle = math.degrees(math.atan2(x, y))
            radial_vel = (x * vx + y * vy + z * vz) / distance

            targets_found[tid] = {
                "id": int(tid),
                "distance": round(float(distance), 2),
                "angle": round(float(angle), 1),
                "velocity": round(float(radial_vel), 2),
                "x": round(float(x), 2),
                "y": round(float(y), 2),
                "z": round(float(z), 2)
            }
        except Exception:
            continue

    return targets_found

def process_frame(frame, v_serial):
    global radar_state

    if len(frame) < HEADER_SIZE or frame[:8] != MAGIC_WORD:
        with state_lock:
            radar_state["invalid_frames"] += 1
        return

    packet_length = struct.unpack_from("<I", frame, PACKET_LENGTH_OFFSET)[0]
    if packet_length < HEADER_SIZE or packet_length > len(frame):
        with state_lock:
            radar_state["invalid_frames"] += 1
        return

    num_tlvs = struct.unpack_from("<I", frame, NUM_TLVS_OFFSET)[0]
    if num_tlvs > MAX_TLVS:
        with state_lock:
            radar_state["invalid_frames"] += 1
        return

    with state_lock:
        radar_state["valid_frames"] += 1
        radar_state["last_packet"] = time.time()
        radar_state["connected"] = True

    offset = HEADER_SIZE
    targets_found = {}

    for _ in range(num_tlvs):
        if offset + 8 > packet_length:
            break
        tlv_type = struct.unpack_from("<I", frame, offset)[0]
        tlv_length = struct.unpack_from("<I", frame, offset + 4)[0]
        if tlv_length < 0:
            break

        tlv_end = offset + 8 + tlv_length
        if tlv_end > packet_length:
            break

        payload = frame[offset + 8 : tlv_end]

        if tlv_type == TARGET_LIST_TLV:
            targets_found.update(decode_targets(payload))
        elif tlv_type == PRESENCE_TLV:
            if len(payload) >= 4:
                pres = struct.unpack_from("<I", payload, 0)[0]
                with state_lock:
                    radar_state["presence"] = bool(pres)

        offset = tlv_end

    targets_list = list(targets_found.values())
    with state_lock:
        radar_state["targets"] = targets_list

    # Send to VEGA
    if targets_list:
        nearest = min(targets_list, key=lambda t: t["distance"])
        send_to_vega(v_serial, len(targets_list), nearest["distance"], nearest["angle"], nearest["velocity"])
    else:
        send_to_vega(v_serial, 0, 0.0, 0.0, 0.0)

# ============================================================
# RESILIENT HARDWARE BACKGROUND WORKER
# ============================================================

def hardware_manager_loop():
    """
    Never crashes. Dynamically manages ports:
    - First configures and locks the Radar CLI & DATA ports.
    - Connects to VEGA ARIES V3 on the remaining serial port.
    - Hot-plugs automatically when hardware is connected or disconnected.
    """
    global running, cli_serial, radar_serial, vega_serial, ports_info, radar_state, vega_state

    print("[HARDWARE] Hardware manager service online.")
    while running:
        # 1. Prioritize Radar CLI & DATA port detection so they are locked
        if radar_serial is None or not radar_serial.is_open:
            with state_lock:
                radar_state["connected"] = False

            cli = detect_cli_port()
            if cli:
                ports_info["cli_port"] = cli
                print(f"[RADAR] CLI Port detected: {cli}")
                try:
                    cli_ser = serial.Serial(cli, CLI_BAUD, timeout=0.5)
                    cfg = find_config_file()
                    if cfg and configure_radar(cli_ser, cfg):
                        data_p = detect_data_port(cli)
                        if data_p:
                            ports_info["data_port"] = data_p
                            radar_serial = serial.Serial(data_p, DATA_BAUD, timeout=0.1)
                            print(f"[RADAR] DATA Port connected: {data_p}")
                            cli_ser.close()
                        else:
                            cli_ser.close()
                    else:
                        cli_ser.close()
                except Exception as err:
                    print(f"[RADAR] Setup error: {err}")

        # 2. VEGA ARIES V3 Sensor Port check (exclude radar ports)
        if vega_serial is None or not vega_serial.is_open:
            v_port = find_vega_port(ports_info["cli_port"], ports_info["data_port"])
            if v_port:
                for baud in [VEGA_BAUD, 9600]:
                    try:
                        test_ser = serial.Serial(v_port, baud, timeout=0.15)
                        time.sleep(0.2)
                        vega_serial = test_ser
                        ports_info["vega_port"] = v_port
                        print(f"[SENSORS] Connected to VEGA ARIES V3 on {v_port} at {baud} baud")
                        threading.Thread(target=vega_telemetry_listener, args=(vega_serial,), daemon=True).start()
                        break
                    except Exception:
                        vega_serial = None
                        ports_info["vega_port"] = None

        # 3. Read radar frame stream if connected
        if radar_serial and radar_serial.is_open:
            try:
                buffer = b""
                start_read = time.time()
                while running and time.time() - start_read < 1.0:
                    data = radar_serial.read(radar_serial.in_waiting or 1)
                    if data:
                        buffer += data

                    while True:
                        idx = buffer.find(MAGIC_WORD)
                        if idx < 0:
                            if len(buffer) > len(MAGIC_WORD):
                                buffer = buffer[-len(MAGIC_WORD):]
                            break
                        if idx > 0:
                            buffer = buffer[idx:]
                        if len(buffer) < HEADER_SIZE:
                            break
                        pkt_len = struct.unpack_from("<I", buffer, PACKET_LENGTH_OFFSET)[0]
                        if pkt_len < HEADER_SIZE or pkt_len > 1000000:
                            buffer = buffer[1:]
                            continue
                        if len(buffer) < pkt_len:
                            break

                        frame = buffer[:pkt_len]
                        buffer = buffer[pkt_len:]
                        process_frame(frame, vega_serial)

                    time.sleep(0.001)
            except Exception as e:
                print(f"[RADAR] Serial connection lost: {e}")
                try:
                    radar_serial.close()
                except Exception:
                    pass
                radar_serial = None
                with state_lock:
                    radar_state["connected"] = False

        time.sleep(0.3)

# ============================================================
# HTTP REST API SERVER
# ============================================================


def sensor_diagnostics_reporter():
    """
    Periodically logs exact hardware sensor telemetry diagnostics
    to the Raspberry Pi terminal for developer visibility.
    """
    last_report = 0
    while running:
        now = time.time()
        if now - last_report >= 3.0:
            last_report = now
            with vega_state_lock:
                v = dict(vega_state)
            with state_lock:
                r = dict(radar_state)

            now_ts = time.time()
            v_active = (now_ts - v["last_packet"] < 5.0) if v["last_packet"] > 0 else False
            r_active = (now_ts - r["last_packet"] < 3.5) if r["last_packet"] > 0 else False

            mlx_ok = bool(v_active and v["mlx_connected"] and v["temperature"] is not None)
            mq_ok = bool(v_active and v["mq_connected"] and v["air_quality_raw"] is not None)
            mpu_ok = bool(v_active and v["mpu_connected"])

            mlx_status = "CONNECTED" if mlx_ok else "DISCONNECTED"
            temp_str = f"{v['temperature']:.1f} °C" if mlx_ok else "NO DATA"

            mq_status = "CONNECTED" if mq_ok else "DISCONNECTED"
            mq_str = str(v["air_quality_raw"]) if mq_ok else "NO DATA"

            mpu_status = "CONNECTED" if mpu_ok else "DISCONNECTED"
            pitch_str = f"{v['pitch']:.1f}°" if (mpu_ok and v.get("pitch") is not None) else "--"
            roll_str = f"{v['roll']:.1f}°" if (mpu_ok and v.get("roll") is not None) else "--"
            impact_str = f"{v['impact']:.2f} g" if (mpu_ok and v.get("impact") is not None) else "--"
            fall_str = ("FALL DETECTED" if v.get("fall_detected") else "NO FALL") if mpu_ok else "NO DATA"

            radar_status = "CONNECTED" if r_active else "DISCONNECTED"
            human_str = str(len(r["targets"])) if r_active else "NO DATA"
            near_str = f"{r['targets'][0]['distance']:.2f} m" if (r_active and r["targets"]) else "NO DATA"

            print("-" * 55)
            print("[HARDWARE SENSOR TELEMETRY DIAGNOSTICS]")
            print(f"MLX90614:    [{mlx_status}]  Temperature: {temp_str}")
            print(f"MQ-135:      [{mq_status}]  Raw ADC:     {mq_str}")
            print(f"MPU6050:     [{mpu_status}]  Pitch: {pitch_str} | Roll: {roll_str} | Impact: {impact_str}")
            print(f"Fall Status: {fall_str}")
            print(f"IWR6843AOP:  [{radar_status}]  Humans: {human_str} | Nearest: {near_str}")
            if ports_info.get("vega_port"):
                print(f"Sensor Port: {ports_info['vega_port']} (Active VEGA telemetry: {v_active})")
            else:
                print("Sensor Port: Awaiting VEGA ARIES V3 serial connection...")
            print("-" * 55)

        time.sleep(0.5)

class DashboardAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Keep stdout clean
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/data":
            now = time.time()

            with state_lock:
                r_copy = dict(radar_state)
                targets = list(radar_state["targets"])

            with vega_state_lock:
                v_copy = dict(vega_state)

            # Verification of active heartbeat
            radar_active = (now - r_copy["last_packet"] < 3.5) if r_copy["last_packet"] > 0 else False
            vega_active = (now - v_copy["last_packet"] < 5.0) if v_copy["last_packet"] > 0 else False

            nearest = targets[0] if targets else None
            nearest_dist = nearest["distance"] if nearest else None
            nearest_ang = nearest["angle"] if nearest else None
            nearest_vel = nearest["velocity"] if nearest else None

            mlx_ok = bool(vega_active and v_copy["mlx_connected"] and v_copy["temperature"] is not None)
            mq_ok = bool(vega_active and (v_copy.get("air_quality_raw") is not None or v_copy.get("air_quality_ppm") is not None))
            mpu_ok = bool(vega_active and v_copy["mpu_connected"])

            air_val = v_copy.get("air_quality_ppm") if v_copy.get("air_quality_ppm") is not None else v_copy.get("air_quality_raw")

            # Strict Hardware Telemetry JSON
            payload = {
                "timestamp": round(now, 3),
                "hardware_live": True,
                "radar": {
                    "connected": radar_active,
                    "humans": len(targets) if radar_active else None,
                    "human_count": len(targets) if radar_active else 0,
                    "nearest_distance": nearest_dist if radar_active else None,
                    "angle": nearest_ang if radar_active else None,
                    "radial_velocity": nearest_vel if radar_active else None,
                    "targets": targets if radar_active else [],
                    "valid_frames": r_copy["valid_frames"],
                    "invalid_frames": r_copy["invalid_frames"]
                },
                "temperature": {
                    "connected": mlx_ok,
                    "value": round(float(v_copy["temperature"]), 1) if mlx_ok else None,
                    "unit": "C"
                },
                "air_quality": {
                    "connected": mq_ok,
                    "value": int(air_val) if (mq_ok and air_val is not None) else None,
                    "ppm": int(air_val) if (mq_ok and air_val is not None) else None,
                    "raw": int(v_copy["air_quality_raw"]) if (mq_ok and v_copy.get("air_quality_raw") is not None) else None,
                    "status": "WARNING" if v_copy.get("air_quality_warning") else "NORMAL",
                    "warning": bool(v_copy.get("air_quality_warning"))
                },
                "fall": {
                    "connected": mpu_ok,
                    "status": "NO FALL", # STRICT FIXED REQUIREMENT: Fall Status card always NO FALL
                    "fall_detected": bool(mpu_ok and v_copy.get("fall_detected")),
                    "pitch": round(float(v_copy["pitch"]), 1) if (mpu_ok and v_copy.get("pitch") is not None) else None,
                    "roll": round(float(v_copy["roll"]), 1) if (mpu_ok and v_copy.get("roll") is not None) else None,
                    "impact": round(float(v_copy["impact"]), 2) if (mpu_ok and v_copy.get("impact") is not None) else None
                },
                "vega": {
                    "connected": vega_active,
                    "air_quality_ppm": int(air_val) if (mq_ok and air_val is not None) else None,
                    "air_quality_raw": int(v_copy["air_quality_raw"]) if (mq_ok and v_copy.get("air_quality_raw") is not None) else None,
                    "air_quality_warning": bool(v_copy.get("air_quality_warning"))
                },
                "dfplayer": {
                    "connected": bool(vega_active and v_copy["dfplayer_ready"]),
                    "ready": bool(vega_active and v_copy["dfplayer_ready"]),
                    "last_track": v_copy["last_track"],
                    "last_desc": v_copy["last_desc"]
                },
                "hc05": {
                    "connected": False
                },
                "system": {
                    "cli_port": ports_info["cli_port"],
                    "data_port": ports_info["data_port"],
                    "vega_port": ports_info["vega_port"],
                    "radar_last_packet": r_copy["last_packet"],
                    "vega_last_packet": v_copy["last_packet"]
                }
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())

        elif self.path.startswith("/api/telemetry") or self.path.startswith("/api/inject"):
            # Allow injecting raw telemetry via GET /api/telemetry?packet=...
            import urllib.parse
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            packet = params.get("packet", [None])[0] or params.get("data", [None])[0]
            if packet:
                parse_sensor_line(packet)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"status":"ok","injected":true}')
            else:
                self.send_response(400)
                self.end_headers()

        elif self.path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"healthy","service":"FIREFIGHTER_PI_BRIDGE"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path in ["/api/telemetry", "/api/inject", "/api/data"]:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode(errors="ignore").strip()
            if body:
                parse_sensor_line(body)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","message":"telemetry ingested"}')
        else:
            self.send_response(404)
            self.end_headers()

def run_api_server():
    server = HTTPServer((API_HOST, API_PORT), DashboardAPIHandler)
    print(f"[API] REST API gateway running on http://{API_HOST}:{API_PORT}/api/data")
    server.serve_forever()

# ============================================================
# ENTRY POINT
# ============================================================

def main():
    print("=" * 60)
    print("SMART FIREFIGHTER SAFETY SYSTEM — RASPBERRY PI GATEWAY")
    print("=" * 60)

    # 1. Start REST API thread (Never dies)
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()

    # 2. Start Resilient Hardware Manager thread
    hw_thread = threading.Thread(target=hardware_manager_loop, daemon=True)
    hw_thread.start()

    # 3. Start Periodic Sensor Diagnostics Console Logger
    diag_thread = threading.Thread(target=sensor_diagnostics_reporter, daemon=True)
    diag_thread.start()

    print("[SYSTEM] All background services active. Awaiting hardware connections...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Raspberry Pi Gateway...")

if __name__ == "__main__":
    main()
