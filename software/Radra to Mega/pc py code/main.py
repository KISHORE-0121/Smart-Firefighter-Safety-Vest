import serial
import time
import os
import struct
import math
from collections import deque


# ============================================================
# USER SETTINGS
# ============================================================

# ------------------------------------------------------------
# CHANGE ONLY THESE 3 COM PORTS
# ------------------------------------------------------------

CLI_PORT  = "COM6"     # IWR6843AOP CLI port
DATA_PORT = "COM5"     # IWR6843AOP DATA port
MEGA_PORT = "COM15"    # Arduino Mega USB port


# ------------------------------------------------------------
# BAUD RATES
# ------------------------------------------------------------

CLI_BAUD = 115200
DATA_BAUD = 921600
MEGA_BAUD = 115200


# ------------------------------------------------------------
# RADAR CONFIG FILE
# ------------------------------------------------------------

CONFIG_FILENAME = "AOP_6m_default.cfg"


# ------------------------------------------------------------
# MAXIMUM HUMANS
# ------------------------------------------------------------

MAX_HUMANS = 5


# ============================================================
# MEGA 10 SECOND COOLDOWN
# ============================================================

MEGA_COOLDOWN = 10.0

last_mega_send_time = 0.0


# ============================================================
# RADAR MAGIC WORD
# ============================================================

MAGIC_WORD = b'\x02\x01\x04\x03\x06\x05\x08\x07'


# ============================================================
# RADAR PACKET SETTINGS
# ============================================================

HEADER_SIZE = 40

PACKET_LENGTH_OFFSET = 12
NUM_TLVS_OFFSET = 32

TARGET_LIST_TLV = 1010
TARGET_SIZE = 112

MAX_TLVS = 100


# ============================================================
# MEDIAN FILTER
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

    # First look in the same folder as this Python file
    script_folder = os.path.dirname(
        os.path.abspath(__file__)
    )

    config_path = os.path.join(
        script_folder,
        CONFIG_FILENAME
    )

    if os.path.isfile(config_path):
        return config_path

    # Then look in current working directory
    config_path = os.path.join(
        os.getcwd(),
        CONFIG_FILENAME
    )

    if os.path.isfile(config_path):
        return config_path

    return None


# ============================================================
# SEND RADAR CONFIGURATION
# ============================================================

def configure_radar(cli_serial, config_file):

    print()
    print("========================================")
    print("SENDING RADAR CONFIGURATION")
    print("========================================")
    print(config_file)

    try:

        with open(config_file, "r") as file:
            lines = file.readlines()

    except Exception as e:

        print("ERROR: Cannot open config file")
        print(e)

        return False


    for line in lines:

        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip comments
        if line.startswith("%"):
            continue

        print("CLI <<", line)

        try:

            cli_serial.reset_input_buffer()

            cli_serial.write(
                (line + "\r\n").encode()
            )

            cli_serial.flush()

            deadline = time.time() + 2.0

            response = b""

            while time.time() < deadline:

                data = cli_serial.read(
                    cli_serial.in_waiting or 1
                )

                if data:

                    response += data

                    text = response.decode(
                        errors="ignore"
                    )

                    if "Done" in text:
                        break

                    if (
                        "Error" in text
                        or
                        "error" in text
                    ):

                        print()
                        print("RADAR CLI ERROR:")
                        print(text)

                        return False

                else:

                    time.sleep(0.01)

            else:

                print(
                    "WARNING: No Done response for:",
                    line
                )

        except Exception as e:

            print("Config send error:")
            print(e)

            return False


    print()
    print("Radar configuration completed.")

    time.sleep(2)

    return True


# ============================================================
# SEND DATA TO ARDUINO MEGA
# ============================================================

def send_to_mega(
    mega_serial,
    count,
    distance,
    angle,
    velocity
):

    global last_mega_send_time


    if mega_serial is None:
        return


    # ========================================================
    # 10 SECOND COOLDOWN
    # ========================================================

    current_time = time.time()

    if (
        current_time -
        last_mega_send_time
    ) < MEGA_COOLDOWN:

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

            message = "N,0,0,0,0\n"


        mega_serial.write(
            message.encode()
        )

        mega_serial.flush()


        # Update timer ONLY after successful send

        last_mega_send_time = time.time()


        print(
            "MEGA <<",
            message.strip()
        )

        print(
            "Next Mega update after 10 seconds."
        )


    except Exception as e:

        print("Mega send error:")
        print(e)


# ============================================================
# DECODE TARGET LIST
# ============================================================

def decode_targets(payload):

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


    for i in range(number_targets):

        offset = i * TARGET_SIZE

        try:

            # ------------------------------------------------
            # TARGET ID
            # ------------------------------------------------

            tid = struct.unpack_from(
                "<I",
                payload,
                offset
            )[0]


            # ------------------------------------------------
            # POSITION
            # ------------------------------------------------

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


            # ------------------------------------------------
            # VELOCITY
            # ------------------------------------------------

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


            # ------------------------------------------------
            # CHECK VALID NUMBERS
            # ------------------------------------------------

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


            # ------------------------------------------------
            # DISTANCE
            # ------------------------------------------------

            distance = math.sqrt(
                x * x +
                y * y +
                z * z
            )


            if distance <= 0:
                continue


            # ------------------------------------------------
            # MEDIAN FILTER
            # ------------------------------------------------

            history = distance_history.setdefault(
                tid,
                deque(
                    maxlen=MEDIAN_WINDOW
                )
            )


            if len(history) >= MIN_HISTORY_FOR_REJECTION:

                sorted_history = sorted(history)

                median_distance = sorted_history[
                    len(sorted_history) // 2
                ]


                if (
                    abs(
                        distance -
                        median_distance
                    )
                    >
                    DISTANCE_MEDIAN_THRESHOLD
                ):

                    print(
                        f"OUTLIER REJECTED: "
                        f"ID={tid}, "
                        f"Distance={distance:.2f} m, "
                        f"Median={median_distance:.2f} m"
                    )

                    continue


            history.append(distance)


            # ------------------------------------------------
            # AREA FILTER
            # ------------------------------------------------

            if x < X_MIN or x > X_MAX:
                continue

            if y < Y_MIN or y > Y_MAX:
                continue

            if z < Z_MIN or z > Z_MAX:
                continue


            # ------------------------------------------------
            # ANGLE
            # ------------------------------------------------

            angle = math.degrees(
                math.atan2(
                    x,
                    y
                )
            )


            # ------------------------------------------------
            # RADIAL VELOCITY
            # ------------------------------------------------

            radial_velocity = (
                x * vx +
                y * vy +
                z * vz
            ) / distance


            # ------------------------------------------------
            # SAVE TARGET
            # ------------------------------------------------

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
    mega_serial
):

    # ========================================================
    # NO HUMAN
    # ========================================================

    if not targets_found:

        print()
        print("================================")
        print("NO HUMAN DETECTED")
        print("================================")

        send_to_mega(
            mega_serial,
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
    # DISPLAY ON LAPTOP
    # ========================================================

    print()
    print("================================")
    print("HUMAN DETECTED")
    print("================================")

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

    print("================================")


    # ========================================================
    # SEND TO MEGA
    # ========================================================

    send_to_mega(
        mega_serial,
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
    mega_serial
):

    try:

        # ----------------------------------------------------
        # CHECK HEADER
        # ----------------------------------------------------

        if len(frame) < HEADER_SIZE:
            return


        # ----------------------------------------------------
        # CHECK MAGIC WORD
        # ----------------------------------------------------

        if frame[:8] != MAGIC_WORD:
            return


        # ----------------------------------------------------
        # PACKET LENGTH
        # ----------------------------------------------------

        packet_length = struct.unpack_from(
            "<I",
            frame,
            PACKET_LENGTH_OFFSET
        )[0]


        if packet_length < HEADER_SIZE:
            return


        if packet_length > len(frame):
            return


        # ----------------------------------------------------
        # NUMBER OF TLVs
        # ----------------------------------------------------

        num_tlvs = struct.unpack_from(
            "<I",
            frame,
            NUM_TLVS_OFFSET
        )[0]


        if num_tlvs > MAX_TLVS:
            return


        offset = HEADER_SIZE

        targets_found = {}


        # ----------------------------------------------------
        # READ TLVs
        # ----------------------------------------------------

        for tlv_number in range(num_tlvs):

            if (
                offset + 8 >
                packet_length
            ):
                return


            # TLV TYPE

            tlv_type = struct.unpack_from(
                "<I",
                frame,
                offset
            )[0]


            # TLV LENGTH

            tlv_length = struct.unpack_from(
                "<I",
                frame,
                offset + 4
            )[0]


            tlv_end = (
                offset +
                8 +
                tlv_length
            )


            if tlv_end > packet_length:
                return


            payload_start = offset + 8

            payload_end = (
                offset +
                8 +
                tlv_length
            )


            payload = frame[
                payload_start:
                payload_end
            ]


            # ------------------------------------------------
            # TARGET LIST TLV
            # ------------------------------------------------

            if tlv_type == TARGET_LIST_TLV:

                if (
                    len(payload) %
                    TARGET_SIZE
                    == 0
                ):

                    decoded = decode_targets(
                        payload
                    )

                    targets_found.update(
                        decoded
                    )

                else:

                    print(
                        "WARNING: Invalid target payload size:",
                        len(payload)
                    )


            # ------------------------------------------------
            # PRESENCE TLV
            # ------------------------------------------------

            elif tlv_type == 1021:

                if len(payload) >= 4:

                    presence = struct.unpack_from(
                        "<I",
                        payload,
                        0
                    )[0]

                    print(
                        "Presence:",
                        "HUMAN"
                        if presence
                        else
                        "NO HUMAN"
                    )


            # ------------------------------------------------
            # NEXT TLV
            # ------------------------------------------------

            offset = tlv_end


        # ----------------------------------------------------
        # SEND RESULT
        # ----------------------------------------------------

        process_result(
            targets_found,
            mega_serial
        )


    except Exception as e:

        print(
            "Frame processing error:",
            e
        )


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print()
    print("========================================")
    print(" IWR6843AOP HUMAN DETECTION")
    print(" LAPTOP -> ARDUINO MEGA 2560")
    print(" FIXED COM PORT VERSION")
    print(" MEGA UPDATE COOLDOWN: 10 SECONDS")
    print("========================================")

    print()
    print("CLI PORT  :", CLI_PORT)
    print("DATA PORT :", DATA_PORT)
    print("MEGA PORT :", MEGA_PORT)


    # ========================================================
    # CHECK THAT PORTS ARE DIFFERENT
    # ========================================================

    if (
        CLI_PORT == DATA_PORT or
        CLI_PORT == MEGA_PORT or
        DATA_PORT == MEGA_PORT
    ):

        print()
        print("ERROR:")
        print("CLI, DATA and MEGA ports must be different.")

        return


    cli_serial = None
    radar_serial = None
    mega_serial = None


    try:

        # ====================================================
        # FIND CONFIG FILE
        # ====================================================

        config_file = find_config_file()


        if config_file is None:

            print()
            print(
                "ERROR:",
                CONFIG_FILENAME,
                "not found."
            )

            print()
            print(
                "Put AOP_6m_default.cfg in the same"
            )

            print(
                "folder as this Python program."
            )

            return


        print()
        print("CONFIG FILE:")
        print(config_file)


        # ====================================================
        # OPEN RADAR CLI
        # ====================================================

        print()
        print("Opening RADAR CLI...")
        print(
            f"{CLI_PORT} @ {CLI_BAUD}"
        )


        try:

            cli_serial = serial.Serial(
                port=CLI_PORT,
                baudrate=CLI_BAUD,
                timeout=0.5
            )

        except Exception as e:

            print()
            print("ERROR: Cannot open CLI port")
            print(CLI_PORT)
            print(e)

            return


        time.sleep(0.5)

        cli_serial.reset_input_buffer()


        print("CLI port opened.")


        # ====================================================
        # CONFIGURE RADAR
        # ====================================================

        if not configure_radar(
            cli_serial,
            config_file
        ):

            print()
            print("ERROR: Radar configuration failed.")

            return


        # ====================================================
        # CLOSE CLI
        # ====================================================

        cli_serial.close()
        cli_serial = None

        print()
        print("CLI port closed.")


        # ====================================================
        # OPEN RADAR DATA
        # ====================================================

        print()
        print("Opening RADAR DATA...")
        print(
            f"{DATA_PORT} @ {DATA_BAUD}"
        )


        try:

            radar_serial = serial.Serial(
                port=DATA_PORT,
                baudrate=DATA_BAUD,
                timeout=0.1
            )

        except Exception as e:

            print()
            print("ERROR: Cannot open DATA port")
            print(DATA_PORT)
            print(e)

            return


        time.sleep(0.5)

        radar_serial.reset_input_buffer()


        print("RADAR DATA port opened.")


        # ====================================================
        # OPEN ARDUINO MEGA USB
        # ====================================================

        print()
        print("Opening Arduino Mega...")
        print(
            f"{MEGA_PORT} @ {MEGA_BAUD}"
        )


        try:

            mega_serial = serial.Serial(
                port=MEGA_PORT,
                baudrate=MEGA_BAUD,
                timeout=0.1
            )

        except Exception as e:

            print()
            print("ERROR: Cannot open Mega port")
            print(MEGA_PORT)
            print(e)

            return


        # Arduino resets when USB serial is opened
        time.sleep(2.0)

        mega_serial.reset_input_buffer()


        print("Arduino Mega USB opened.")


        # ====================================================
        # RADAR BUFFER
        # ====================================================

        buffer = b""


        print()
        print("========================================")
        print("SYSTEM RUNNING")
        print("========================================")

        print()
        print("IWR6843AOP")
        print("     |")
        print("     | USB")
        print("     v")
        print("   LAPTOP")
        print("     |")
        print("     | USB")
        print("     v")
        print(" ARDUINO MEGA 2560")

        print()
        print("Waiting for human detection...")
        print("Mega data update: every 10 seconds.")
        print("Press CTRL+C to stop.")
        print()


        # ====================================================
        # MAIN LOOP
        # ====================================================

        while True:

            # ------------------------------------------------
            # READ RADAR BINARY DATA
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


                if magic_index < 0:

                    if (
                        len(buffer) >
                        len(MAGIC_WORD)
                    ):

                        buffer = buffer[
                            -len(MAGIC_WORD):
                        ]

                    break


                # ------------------------------------------------
                # REMOVE GARBAGE BEFORE MAGIC WORD
                # ------------------------------------------------

                if magic_index > 0:

                    buffer = buffer[
                        magic_index:
                    ]


                # ------------------------------------------------
                # WAIT FOR COMPLETE HEADER
                # ------------------------------------------------

                if len(buffer) < HEADER_SIZE:

                    break


                # ------------------------------------------------
                # READ PACKET LENGTH
                # ------------------------------------------------

                packet_length = struct.unpack_from(
                    "<I",
                    buffer,
                    PACKET_LENGTH_OFFSET
                )[0]


                # ------------------------------------------------
                # CHECK PACKET LENGTH
                # ------------------------------------------------

                if (
                    packet_length < HEADER_SIZE
                    or
                    packet_length > 1000000
                ):

                    print(
                        "ERROR: Invalid packet length:",
                        packet_length
                    )

                    buffer = buffer[1:]

                    continue


                # ------------------------------------------------
                # WAIT FOR COMPLETE PACKET
                # ------------------------------------------------

                if len(buffer) < packet_length:

                    break


                # ------------------------------------------------
                # EXTRACT COMPLETE FRAME
                # ------------------------------------------------

                frame = buffer[
                    :packet_length
                ]


                # Remove processed frame

                buffer = buffer[
                    packet_length:
                ]


                # ------------------------------------------------
                # PROCESS FRAME
                # ------------------------------------------------

                process_frame(
                    frame,
                    mega_serial
                )


            time.sleep(0.001)


    except KeyboardInterrupt:

        print()
        print("Stopping program...")


    except Exception as e:

        print()
        print("MAIN ERROR:")
        print(e)


    finally:

        # ----------------------------------------------------
        # CLOSE RADAR DATA
        # ----------------------------------------------------

        if radar_serial is not None:

            try:
                radar_serial.close()
            except:
                pass


        # ----------------------------------------------------
        # CLOSE MEGA
        # ----------------------------------------------------

        if mega_serial is not None:

            try:
                mega_serial.close()
            except:
                pass


        # ----------------------------------------------------
        # CLOSE CLI
        # ----------------------------------------------------

        if cli_serial is not None:

            try:
                cli_serial.close()
            except:
                pass


        print()
        print("Serial ports closed.")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()