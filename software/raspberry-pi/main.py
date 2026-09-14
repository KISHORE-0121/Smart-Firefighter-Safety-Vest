import serial
import serial.tools.list_ports
import time
import os
import struct
import math
import glob
from collections import deque


# ============================================================
# SETTINGS
# ============================================================

CLI_BAUD = 115200
DATA_BAUD = 921600
VEGA_BAUD = 115200

CONFIG_FILENAME = "AOP_6m_default.cfg"

UPDATE_INTERVAL = 10.0
MAX_HUMANS = 5


# ============================================================
# RADAR MAGIC WORD
# ============================================================

MAGIC_WORD = b'\x02\x01\x04\x03\x06\x05\x08\x07'


# ============================================================
# 3D PEOPLE TRACKING
# ============================================================

HEADER_SIZE = 40

PACKET_LENGTH_OFFSET = 12
NUM_TLVS_OFFSET = 32

TARGET_LIST_TLV = 1010
TARGET_SIZE = 112

MAX_TLVS = 100

# ============================================================
# MEDIAN BASED OUTLIER REJECTION
# ============================================================

MEDIAN_WINDOW = 5
MIN_HISTORY_FOR_REJECTION = 3
DISTANCE_MEDIAN_THRESHOLD = 1.0

distance_history = {}


# ============================================================
# HUMAN DETECTION AREA
# ============================================================

X_MIN = -5.0
X_MAX = 5.0

Y_MIN = 0.1
Y_MAX = 10.0

Z_MIN = -2.0
Z_MAX = 3.0


# ============================================================
# FIND CONFIG FILE
# ============================================================

def find_config_file():

    search_locations = [

        os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)
            ),
            CONFIG_FILENAME
        ),

        os.path.join(
            os.getcwd(),
            CONFIG_FILENAME
        ),

        os.path.expanduser(
            os.path.join(
                "~",
                CONFIG_FILENAME
            )
        )
    ]

    for path in search_locations:

        if os.path.isfile(path):
            return path

    for root in [
        os.path.dirname(
            os.path.abspath(__file__)
        ),
        os.getcwd(),
        os.path.expanduser("~")
    ]:

        try:

            for path in glob.glob(
                os.path.join(
                    root,
                    "**",
                    CONFIG_FILENAME
                ),
                recursive=True
            ):

                if os.path.isfile(path):
                    return path

        except Exception:
            pass

    return None


# ============================================================
# SERIAL PORT SCANNING
# ============================================================

def get_serial_ports():

    ports = []

    # Windows: ports appear as COM3, COM4, COM5, etc.
    # Linux/Raspberry Pi: ports appear as /dev/ttyUSB0, /dev/ttyACM0, etc.
    for p in serial.tools.list_ports.comports():

        device = p.device

        if os.name == "nt":
            # Windows
            if device.upper().startswith("COM"):
                ports.append(device)
        else:
            # Linux / Raspberry Pi
            if (
                device.startswith("/dev/ttyUSB") or
                device.startswith("/dev/ttyACM") or
                device.startswith("/dev/ttyS") or
                device.startswith("/dev/ttyAMA") or
                device.startswith("/dev/serial/by-id/")
            ):
                ports.append(device)

    return ports


# ============================================================
# CHECK CLI PORT
# ============================================================

def check_cli_port(port):

    ser = None

    try:

        ser = serial.Serial(
            port,
            CLI_BAUD,
            timeout=0.5
        )

        time.sleep(0.2)

        ser.reset_input_buffer()

        ser.write(
            b"version\r\n"
        )

        time.sleep(0.5)

        response = ser.read(500)

        text = response.decode(
            errors="ignore"
        ).lower()

        keywords = [
            "version",
            "mmwave",
            "iwr6843",
            "demo"
        ]

        for keyword in keywords:

            if keyword in text:

                return True

    except Exception as e:

        print(
            "CLI check error:",
            port,
            e
        )

    finally:

        if ser is not None:

            try:
                ser.close()
            except Exception:
                pass

    return False


# ============================================================
# DETECT CLI PORT
# ============================================================

def detect_cli_port():

    ports = get_serial_ports()

    print()
    print("Available serial ports:")

    for port in ports:

        print(
            " ",
            port
        )

    for port in ports:

        print(
            "Checking CLI:",
            port
        )

        if check_cli_port(port):

            print()
            print(
                "CLI PORT FOUND:",
                port
            )

            return port

    return None


# ============================================================
# SEND RADAR CONFIGURATION
# ============================================================

def configure_radar(
    cli_serial,
    config_file
):

    print()
    print(
        "Loading configuration:"
    )

    print(
        config_file
    )

    try:

        with open(
            config_file,
            "r"
        ) as file:

            lines = file.readlines()

    except Exception as e:

        print(
            "ERROR: Cannot open config:",
            e
        )

        return False

    print()
    print(
        "Sending radar configuration..."
    )

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if line.startswith("%"):
            continue

        try:

            cli_serial.reset_input_buffer()
            cli_serial.write((line + "\r\n").encode())
            cli_serial.flush()

            # Wait for the radar CLI to acknowledge the command.
            deadline = time.time() + 2.0
            response = b""
            while time.time() < deadline:
                chunk = cli_serial.read(cli_serial.in_waiting or 1)
                if chunk:
                    response += chunk
                    text = response.decode(errors="ignore")
                    if "Done" in text:
                        break
                    if "Error" in text or "error" in text:
                        print("RADAR CLI ERROR:", text.strip())
                        return False
                else:
                    time.sleep(0.01)
            else:
                print("WARNING: No Done response for:", line)
                print("Continuing...")

        except Exception as e:

            print(
                "Config send error:",
                e
            )

            return False

    cli_serial.flush()

    print()
    print(
        "Radar configuration sent."
    )

    time.sleep(
        2.0
    )

    return True


# ============================================================
# CHECK DATA PORT
# ============================================================

def check_data_port(
    port,
    wait_time=5.0
):

    ser = None

    try:

        print(
            "Checking RADAR DATA:",
            port
        )

        ser = serial.Serial(
            port,
            DATA_BAUD,
            timeout=0.1
        )

        # Do not clear the stream here; frames may already be arriving.
        start_time = time.time()

        buffer = b""

        while (
            time.time() -
            start_time <
            wait_time
        ):

            data = ser.read(
                ser.in_waiting or 1
            )

            if data:

                buffer += data

                if MAGIC_WORD in buffer:

                    print(
                        "RADAR DATA PORT FOUND:",
                        port
                    )

                    return True

            time.sleep(
                0.001
            )

    except Exception as e:

        print(
            "Data check failed:",
            port,
            e
        )

    finally:

        if ser is not None:

            try:
                ser.close()
            except Exception:
                pass

    return False


# ============================================================
# DETECT RADAR DATA PORT
# ============================================================

def detect_data_port(
    cli_port
):

    ports = get_serial_ports()

    print()
    print(
        "========================================"
    )
    print(
        "SEARCHING FOR RADAR DATA PORT"
    )
    print(
        "========================================"
    )

    for port in ports:

        if port == cli_port:
            continue

        if check_data_port(
            port,
            wait_time=5.0
        ):

            return port

    return None


# ============================================================
# FIND VEGA PORT
# ============================================================

def find_vega_port(
    cli_port,
    data_port
):

    ports = get_serial_ports()

    for port in ports:

        if (
            port != cli_port and
            port != data_port
        ):

            return port

    return None


# ============================================================
# SEND DATA TO VEGA
# ============================================================

def send_to_vega(
    vega_serial,
    count,
    distance,
    angle,
    velocity
):

    if vega_serial is None:

        return

    try:

        if count > 0:

            message = (
                f"H,{count},"
                f"{distance:.2f},"
                f"{angle:.2f},"
                f"{velocity:.2f}\n"
            )

        else:

            message = (
                "N,0,0,0,0\n"
            )

        vega_serial.write(
            message.encode()
        )

        vega_serial.flush()

        print(
            "VEGA <<",
            message.strip()
        )

    except Exception as e:

        print(
            "VEGA send error:",
            e
        )


# ============================================================
# DECODE TARGET LIST
# ============================================================

def decode_targets(
    payload
):

    targets_found = {}

    if len(payload) < TARGET_SIZE:

        return targets_found

    if len(payload) % TARGET_SIZE != 0:

        print(
            "WARNING: Target payload size",
            len(payload),
            "is not a multiple of",
            TARGET_SIZE
        )

    number_targets = (
        len(payload) //
        TARGET_SIZE
    )

    for i in range(
        number_targets
    ):

        offset = (
            i *
            TARGET_SIZE
        )

        try:

            # ----------------------------------------------
            # TARGET ID
            # ----------------------------------------------

            tid = struct.unpack_from(
                "<I",
                payload,
                offset
            )[0]


            # ----------------------------------------------
            # POSITION
            # ----------------------------------------------

            x = struct.unpack_from(
                "<f",
                payload,
                offset + 4
            )[0]

            y = struct.unpack_from(
                "<f",
                payload,
                offset + 8
            )[0]

            z = struct.unpack_from(
                "<f",
                payload,
                offset + 12
            )[0]


            # ----------------------------------------------
            # VELOCITY
            # ----------------------------------------------

            vx = struct.unpack_from(
                "<f",
                payload,
                offset + 16
            )[0]

            vy = struct.unpack_from(
                "<f",
                payload,
                offset + 20
            )[0]

            vz = struct.unpack_from(
                "<f",
                payload,
                offset + 24
            )[0]


            # ----------------------------------------------
            # CHECK NUMBERS
            # ----------------------------------------------

            if not all(
                math.isfinite(value)
                for value in [
                    x,
                    y,
                    z,
                    vx,
                    vy,
                    vz
                ]
            ):

                continue


            # ----------------------------------------------
            # DISTANCE
            # ----------------------------------------------

            distance = math.sqrt(
                x * x +
                y * y +
                z * z
            )

            if distance <= 0:

                continue


            # ----------------------------------------------
            # MEDIAN BASED OUTLIER REJECTION
            # ----------------------------------------------

            history = distance_history.setdefault(
                tid,
                deque(maxlen=MEDIAN_WINDOW)
            )

            if len(history) >= MIN_HISTORY_FOR_REJECTION:

                sorted_history = sorted(history)

                median_distance = sorted_history[
                    len(sorted_history) // 2
                ]

                if (
                    abs(distance - median_distance)
                    > DISTANCE_MEDIAN_THRESHOLD
                ):

                    print(
                        f"OUTLIER REJECTED: "
                        f"ID={tid}, "
                        f"Distance={distance:.2f} m, "
                        f"Median={median_distance:.2f} m"
                    )

                    continue

            history.append(distance)


            # ----------------------------------------------
            # AREA FILTER
            # ----------------------------------------------

            if x < X_MIN or x > X_MAX:

                continue

            if y < Y_MIN or y > Y_MAX:

                continue

            if z < Z_MIN or z > Z_MAX:

                continue


            # ----------------------------------------------
            # ANGLE
            # ----------------------------------------------

            angle = math.degrees(
                math.atan2(
                    x,
                    y
                )
            )


            # ----------------------------------------------
            # RADIAL VELOCITY
            # ----------------------------------------------

            radial_velocity = (
                x * vx +
                y * vy +
                z * vz
            ) / distance


            # ----------------------------------------------
            # SAVE TARGET
            # ----------------------------------------------

            targets_found[tid] = {

                "id": tid,

                "x": x,
                "y": y,
                "z": z,

                "vx": vx,
                "vy": vy,
                "vz": vz,

                "distance": distance,

                "angle": angle,

                "velocity": radial_velocity
            }

        except Exception as e:

            print(
                "Target decode error:",
                e
            )

            continue

    return targets_found


# ============================================================
# PROCESS RESULT
# ============================================================

def process_result(
    targets_found,
    vega_serial
):

    # ========================================================
    # NO HUMAN
    # ========================================================

    if not targets_found:

        print()
        print(
            "=============================="
        )

        print(
            "NO HUMAN DETECTED"
        )

        print(
            "=============================="
        )

        send_to_vega(
            vega_serial,
            0,
            0.0,
            0.0,
            0.0
        )

        return


    # ========================================================
    # HUMAN COUNT
    # ========================================================

    human_count = min(
        len(targets_found),
        MAX_HUMANS
    )


    # ========================================================
    # NEAREST HUMAN
    # ========================================================

    nearest_target = min(
        targets_found.values(),
        key=lambda target:
        target["distance"]
    )

    nearest_distance = (
        nearest_target["distance"]
    )

    nearest_angle = (
        nearest_target["angle"]
    )

    nearest_velocity = (
        nearest_target["velocity"]
    )


    # ========================================================
    # DISPLAY
    # ========================================================

    print()
    print(
        "================================"
    )

    print(
        "NEAREST HUMAN"
    )

    print(
        "================================"
    )

    print(
        "TOTAL HUMANS :",
        human_count
    )

    print(
        "DISTANCE     :",
        f"{nearest_distance:.2f} m"
    )

    print(
        "ANGLE        :",
        f"{nearest_angle:.2f} deg"
    )

    print(
        "RADIAL SPEED :",
        f"{nearest_velocity:.2f} m/s"
    )

    print(
        "================================"
    )


    # ========================================================
    # SEND TO VEGA
    # ========================================================

    send_to_vega(
        vega_serial,
        human_count,
        nearest_distance,
        nearest_angle,
        nearest_velocity
    )


# ============================================================
# PROCESS RADAR FRAME
# ============================================================

def process_frame(
    frame,
    vega_serial
):

    try:

        # ====================================================
        # CHECK HEADER
        # ====================================================

        if len(frame) < HEADER_SIZE:

            return


        # ====================================================
        # CHECK MAGIC WORD
        # ====================================================

        if frame[:8] != MAGIC_WORD:

            return


        # ====================================================
        # PACKET LENGTH
        # ====================================================

        packet_length = struct.unpack_from(
            "<I",
            frame,
            PACKET_LENGTH_OFFSET
        )[0]


        # ====================================================
        # BASIC VALIDATION
        # ====================================================

        if packet_length < HEADER_SIZE:

            print(
                "ERROR: Invalid packet length:",
                packet_length
            )

            return


        if packet_length > len(frame):

            print(
                "ERROR: Incomplete frame:",
                packet_length,
                "bytes expected,",
                len(frame),
                "received"
            )

            return


        # ====================================================
        # NUMBER OF TLVs
        # ====================================================

        num_tlvs = struct.unpack_from(
            "<I",
            frame,
            NUM_TLVS_OFFSET
        )[0]


        if num_tlvs > MAX_TLVS:

            print(
                "ERROR: Invalid TLV count:",
                num_tlvs
            )

            return


        print()
        print(
            "RADAR FRAME"
        )

        print(
            "Packet length :",
            packet_length
        )

        print(
            "Number TLVs   :",
            num_tlvs
        )


        # ====================================================
        # TLV START
        # ====================================================

        offset = HEADER_SIZE

        targets_found = {}


        # ====================================================
        # READ EACH TLV
        # ====================================================

        for tlv_number in range(
            num_tlvs
        ):

            # ----------------------------------------------
            # TLV HEADER
            # ----------------------------------------------

            if (
                offset + 8 >
                packet_length
            ):

                print(
                    "ERROR: TLV header outside packet"
                )

                return


            tlv_type = struct.unpack_from(
                "<I",
                frame,
                offset
            )[0]

            tlv_length = struct.unpack_from(
                "<I",
                frame,
                offset + 4
            )[0]


            print(
                f"TLV {tlv_number}: "
                f"type={tlv_type}, "
                f"payload_length={tlv_length}"
            )


            # ----------------------------------------------
            # TLV LENGTH VALIDATION
            #
            # IMPORTANT:
            # tlv_length is the PAYLOAD length.
            # The 8-byte TLV header is NOT included.
            # Complete TLV size = 8 + tlv_length
            # ----------------------------------------------

            if tlv_length < 0:

                print(
                    "ERROR: Invalid TLV length:",
                    tlv_length
                )

                return


            tlv_end = (
                offset +
                8 +
                tlv_length
            )


            if tlv_end > packet_length:

                print(
                    "ERROR: TLV extends beyond packet"
                )

                print(
                    "offset =",
                    offset,
                    "payload_length =",
                    tlv_length,
                    "packet =",
                    packet_length
                )

                return


            # ----------------------------------------------
            # PAYLOAD
            # ----------------------------------------------

            payload_start = (
                offset + 8
            )

            payload_end = (
                offset +
                8 +
                tlv_length
            )


            payload = frame[
                payload_start:
                payload_end
            ]


            # ----------------------------------------------
            # TARGET LIST TLV
            # ----------------------------------------------

            if tlv_type == TARGET_LIST_TLV:

                print(
                    "TARGET LIST TLV FOUND"
                )

                print(
                    "Target payload:",
                    len(payload),
                    "bytes"
                )


                if (
                    len(payload) %
                    TARGET_SIZE
                    != 0
                ):

                    print(
                        "WARNING: Invalid target payload size"
                    )

                else:

                    decoded = decode_targets(
                        payload
                    )

                    targets_found.update(
                        decoded
                    )


            # ----------------------------------------------
            # PRESENCE TLV (1021)
            # ----------------------------------------------

            if tlv_type == 1021:
                if len(payload) >= 4:
                    presence = struct.unpack_from("<I", payload, 0)[0]
                    print("PRESENCE:", "HUMAN DETECTED" if presence else "NO HUMAN DETECTED")
                else:
                    print("PRESENCE TLV received")

            # ----------------------------------------------
            # MOVE TO NEXT TLV
            # ----------------------------------------------

            offset = tlv_end


        # ====================================================
        # PROCESS HUMAN RESULT
        # ====================================================

        process_result(
            targets_found,
            vega_serial
        )


    except Exception as e:

        print()
        print(
            "Frame processing error:",
            e
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "========================================"
    )

    print(
        " IWR6843AOP HUMAN DETECTION"
    )

    print(
        " PC/Laptop -> VEGA ARIES v2"
    )

    print(
        "========================================"
    )


    # ========================================================
    # STEP 1
    # FIND CLI
    # ========================================================

    cli_port = detect_cli_port()

    if cli_port is None:

        print()
        print(
            "ERROR: CLI port not found."
        )

        return


    print()
    print(
        "CLI PORT:",
        cli_port
    )


    # ========================================================
    # STEP 2
    # OPEN CLI
    # ========================================================

    try:

        cli_serial = serial.Serial(
            cli_port,
            CLI_BAUD,
            timeout=0.5
        )

    except Exception as e:

        print(
            "CLI open error:",
            e
        )

        return


    radar_serial = None
    vega_serial = None


    try:

        # ====================================================
        # STEP 3
        # FIND CONFIG
        # ====================================================

        config_file = find_config_file()

        if config_file is None:

            print()
            print(
                "ERROR:",
                CONFIG_FILENAME,
                "not found."
            )

            return


        # ====================================================
        # STEP 4
        # CONFIGURE RADAR
        # ====================================================

        if not configure_radar(
            cli_serial,
            config_file
        ):

            print(
                "ERROR: Radar configuration failed."
            )

            return


        # ====================================================
        # STEP 5
        # FIND DATA PORT
        # ====================================================

        print()
        print(
            "Radar configured."
        )

        print(
            "Searching for DATA stream..."
        )


        data_port = detect_data_port(
            cli_port
        )


        if data_port is None:

            print()
            print(
                "ERROR: Radar DATA port not found."
            )

            return


        print()
        print(
            "DATA PORT:",
            data_port
        )


        # ====================================================
        # STEP 6
        # OPEN RADAR DATA
        # ====================================================

        try:

            radar_serial = serial.Serial(
                data_port,
                DATA_BAUD,
                timeout=0.1
            )

        except Exception as e:

            print(
                "Radar DATA open error:",
                e
            )

            return


        # Keep the first bytes of the live stream.


        # ====================================================
        # STEP 7
        # FIND VEGA
        # ====================================================

        vega_port = find_vega_port(
            cli_port,
            data_port
        )


        print(
            "VEGA PORT:",
            vega_port
        )


        # ====================================================
        # STEP 8
        # OPEN VEGA
        # ====================================================

        if vega_port is not None:

            try:

                vega_serial = serial.Serial(
                    vega_port,
                    VEGA_BAUD,
                    timeout=0.1
                )

                print(
                    "VEGA serial opened."
                )

            except Exception as e:

                print(
                    "VEGA open error:",
                    e
                )

                vega_serial = None

        else:

            print(
                "WARNING: VEGA port not found."
            )


        # ====================================================
        # STEP 9
        # RADAR BUFFER
        # ====================================================

        buffer = b""


        print()
        print(
            "========================================"
        )

        print(
            "RADAR RUNNING"
        )

        print(
            "Waiting for human detection..."
        )

        print(
            "========================================"
        )


        # ====================================================
        # STEP 10
        # MAIN LOOP
        # ====================================================

        while True:


            # ------------------------------------------------
            # READ RADAR DATA
            # ------------------------------------------------

            data = radar_serial.read(
                radar_serial.in_waiting or 1
            )


            if data:

                buffer += data


            # ------------------------------------------------
            # SEARCH FOR MAGIC WORD
            # ------------------------------------------------

            while True:

                magic_index = buffer.find(
                    MAGIC_WORD
                )


                # --------------------------------------------
                # MAGIC NOT FOUND
                # --------------------------------------------

                if magic_index < 0:

                    if (
                        len(buffer) >
                        len(MAGIC_WORD)
                    ):

                        buffer = buffer[
                            -len(MAGIC_WORD):
                        ]

                    break


                # --------------------------------------------
                # REMOVE GARBAGE BEFORE MAGIC
                # --------------------------------------------

                if magic_index > 0:

                    buffer = buffer[
                        magic_index:
                    ]


                # --------------------------------------------
                # WAIT FOR HEADER
                # --------------------------------------------

                if len(buffer) < HEADER_SIZE:

                    break


                # --------------------------------------------
                # READ PACKET LENGTH
                # --------------------------------------------

                packet_length = struct.unpack_from(
                    "<I",
                    buffer,
                    PACKET_LENGTH_OFFSET
                )[0]


                # --------------------------------------------
                # INVALID PACKET LENGTH
                # --------------------------------------------

                if (
                    packet_length <
                    HEADER_SIZE
                    or
                    packet_length >
                    1000000
                ):

                    print(
                        "ERROR: Invalid packet length:",
                        packet_length
                    )

                    # Move forward one byte
                    # and search for next magic word

                    buffer = buffer[1:]

                    continue


                # --------------------------------------------
                # WAIT FOR COMPLETE PACKET
                # --------------------------------------------

                if len(buffer) < packet_length:

                    break


                # --------------------------------------------
                # EXTRACT COMPLETE FRAME
                # --------------------------------------------

                frame = buffer[
                    :packet_length
                ]


                # --------------------------------------------
                # REMOVE FRAME FROM BUFFER
                # --------------------------------------------

                buffer = buffer[
                    packet_length:
                ]


                # --------------------------------------------
                # PROCESS FRAME
                # --------------------------------------------

                process_frame(
                    frame,
                    vega_serial
                )


            time.sleep(
                0.001
            )


    except KeyboardInterrupt:

        print()
        print(
            "Stopping..."
        )


    except Exception as e:

        print()
        print(
            "MAIN ERROR:",
            e
        )


    finally:


        if radar_serial is not None:

            try:
                radar_serial.close()
            except Exception:
                pass


        if vega_serial is not None:

            try:
                vega_serial.close()
            except Exception:
                pass


        try:
            cli_serial.close()
        except Exception:
            pass


        print(
            "Serial ports closed."
        )


# ============================================================
# PROGRAM START
# ============================================================

if __name__ == "__main__":

    main()

