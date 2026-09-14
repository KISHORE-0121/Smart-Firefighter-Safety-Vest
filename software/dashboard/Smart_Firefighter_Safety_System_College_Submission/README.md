# SMART FIREFIGHTER SAFETY SYSTEM
### Real-Time Incident Command, Firefighter Telemetry & mmWave Radar Life Safety Monitoring Platform
**Powered by VEGA ARIES V3 (THEJAS32 RISC-V SoC)**

---

## 1. Project Title
**Smart Firefighter Safety System with Real-Time mmWave Radar Life Detection and Biometric Hazard Telemetry on VEGA ARIES V3 RISC-V Architecture**

---

## 2. Problem Statement
During structural fire emergencies, firefighters operate inside zero-visibility environments filled with dense particulate smoke, lethal concentrations of toxic combustion gases (such as CO, ammonia, and smoke particles), structural collapse risks, and extreme flashover temperatures. Traditional search-and-rescue methods encounter severe limitations:
1. **Optical & Thermal Camera Obscuration**: Standard visual and infrared cameras suffer heavy backscattering in heavy smoke or water fog.
2. **Delayed Life Detection**: Detecting trapped, unconscious, or fallen victims manually exposes personnel to prolonged extreme danger.
3. **Lack of Central Incident Command Telemetry**: Command centers outside the incident perimeter often lack continuous, real-time physiological and environmental vitals from individual firefighters.

---

## 3. Objective
1. Build a wearable life-safety platform centered on the indigenous **VEGA ARIES V3 RISC-V SoC** controller.
2. Integrate high-frequency **60 GHz mmWave radar (IWR6843AOP)** to penetrate dense smoke and detect human presence, range, angle, and radial velocity.
3. Monitor ambient temperature using contactless infrared thermometry (**MLX90614**).
4. Quantify toxic and combustible gas levels continuously using **MQ-135**.
5. Provide continuous firefighter orientation and fall tracking via a 6-DOF IMU (**MPU6050**).
6. Transmit processed telemetry wirelessly to a real-time incident command **Web Dashboard** featuring 8 dedicated metric cards.

---

## 4. Proposed Solution
The proposed solution implements a dual-stage edge computing architecture:
1. **Wearable Tactical Unit**:
   - **VEGA ARIES V3** reads local biometric and environmental sensors (MLX90614, MQ-135, MPU6050) and drives an SSD1306 local OLED HUD and autonomous DFPlayer Mini audio warnings.
   - **Raspberry Pi** connects to the **IWR6843AOP mmWave radar**, decodes binary TLV target clouds into Cartesian coordinates $(x,y,z)$, computes human distance, angle, and velocity, and feeds target data into VEGA.
2. **Incident Command Central Web Dashboard**:
   - A modern HTML5/CSS3/JavaScript dashboard polling the local REST API / Bluetooth link, updating 8 dedicated safety cards and plotting real-time spatial target polar maps without full-page reloads.

---

## 5. Hardware Components
| Component | Part / Model | Specification / Interface | Role in System |
|---|---|---|---|
| **Main Controller** | **VEGA ARIES V3** | THEJAS32 32-bit RISC-V Core @ 100MHz | Central wearable unit, sensor acquisition, local alerts |
| **Radar Processor** | **Raspberry Pi 4B / 3B+** | Quad-Core ARM Cortex-A72 / A53, Linux OS | Radar binary parser, tracker, REST API server |
| **Life Detection Radar**| **TI IWR6843AOPEVM** | 60-64 GHz FMCW Radar, Antenna-on-Package | Penetrates smoke/dust, human tracking (distance, angle, vel) |
| **Temperature Sensor** | **MLX90614ESF** | Contactless Infrared Thermometer (I2C) | Measures ambient and radiant fire temperature |
| **Gas Sensor** | **MQ-135** | Metal Oxide Semiconductor Gas Sensor (A0) | Measures air quality PPM, smoke, toxic combustion gases |
| **IMU / Motion Sensor** | **MPU6050** | 3-axis Gyroscope + 3-axis Accelerometer (I2C) | Firefighter body tilt, impact acceleration, fall telemetry |
| **Local Display** | **SSD1306** | 128x64 Monochrome OLED Display (I2C 0x3C) | Wearable status HUD on firefighter vest |
| **Audio Module** | **DFPlayer Mini** | MP3 Serial Audio Decoder + Speaker (UART2) | Autonomous local audio alarms for firefighter |
| **Wireless Module** | **HC-05** | Bluetooth Serial Port Profile (UART1) | Wireless telemetry link to mobile/laptop dashboard |

---

## 6. Software Components
- **Microcontroller Firmware**: C++ (`.ino`) compiled via Arduino IDE targeting the VEGA ARIES V3 RISC-V board package.
- **Embedded Radar Engine**: Python 3 (`radar_pi_with_api.py`) with `pyserial`, multi-threaded serial listeners, and an embedded HTTP REST server (`http.server`).
- **Simulated Evaluation Server**: Python 3 (`mock_pi_server.py`) for offline hardware-in-the-loop testing and grading.
- **Web Dashboard**: Vanilla HTML5, CSS3, and JavaScript (ES6) with Chart.js telemetry graphing and zero external framework bloat.
- **Automated Test Suite**: Python 3 test script (`test_dashboard_suite.py`) validating hardware schemas and 3 benchmark test packets.

---

## 7. System Architecture

```text
[TI IWR6843AOP mmWave Radar]
             |
             | USB Data (921600 baud) & CLI (115200 baud)
             v
   [Raspberry Pi 4 / 3B+] <-----------------------------------------+
   - Decodes TLV (TLV 1010 Target List, TLV 1021 Presence)          |
   - Computes Distance (m), Angle (deg), Radial Velocity (m/s)       |
   - Runs HTTP REST API Server on Port 5000                         |
             |                                                      |
             | USB Serial / UART (115200 baud)                      |
             | H,count,dist,angle,vel                               | V,temp,air,fall...
             v                                                      |
    [VEGA ARIES V3 RISC-V Board] -----------------------------------+
    - Reads MLX90614 (I2C), MQ-135 (A0), MPU6050 (I2C)
    - Drives SSD1306 OLED (128x64 I2C HUD)
    - Drives DFPlayer Mini (UART2 Voice/Tone Alerts)
    - Emits Telemetry to Pi & HC-05 Bluetooth (UART1)
             |
             | Wireless Bluetooth / HTTP REST API
             v
   [Incident Command Web Dashboard]
   - Title: SMART FIREFIGHTER SAFETY SYSTEM
   - Subtitle: VEGA ARIES V3 — REAL-TIME SAFETY MONITORING
   - 8 Dedicated Cards + Radar Visualizer + Real-time Graphs
```

---

## 8. Working Principle
1. **Radar Sensing**: The IWR6843AOP chirps frequency-modulated continuous waves (FMCW) at 60 GHz. Reflected signals from human bodies are mixed, digitized, and clustered by the on-chip DSP into target lists.
2. **Pi Edge Extraction**: The Raspberry Pi reads data frames via `/dev/ttyACM1`, matches the magic word `0x0102030405060708`, parses TLV 1010, and applies Kalman filtering.
3. **Telemetry to VEGA**: The Pi sends formatted target strings (`H,count,dist,angle,vel`) to the VEGA ARIES V3 via UART.
4. **Sensor Acquisition on VEGA**: The VEGA ARIES V3 reads the MLX90614 temperature sensor, reads the analog MQ-135 air quality level, and polls MPU6050 accelerometer/gyroscope vectors.
5. **Local Audio & Visual Alarms**: If temperature exceeds safety thresholds or gas PPM rises, VEGA displays alerts on the OLED and commands the DFPlayer Mini to sound emergency audio tracks.
6. **Telemetry Transmission & Web Dashboard**: VEGA packages sensor telemetry (`TEMP:<val>,AIR_PPM:<val>,AIR_STATUS:<status>,FALL:<status>`) back to the Pi. The Pi exposes this via `GET /api/data`, and the Incident Command dashboard renders all 8 cards in real time.

---

## 9. Sensor Functions
1. **TI IWR6843AOP (Life Detection)**: Trapped victim localization through smoke, measuring human count, proximity distance (0.1m to 10m), azimuth angle (-60° to +60°), and movement velocity.
2. **MLX90614 (Contactless Thermal)**: Measures ambient and radiant heat (up to 380°C) without physical contact degradation.
3. **MQ-135 (Hazardous Gas)**: Detects harmful combustion byproducts (NH3, NOx, alcohol, benzene, smoke, CO2).
4. **MPU6050 (Orientation & Fall Telemetry)**: Tracks body pitch, roll, and gravitational acceleration vector magnitudes.

---

## 10. Communication Flow
```text
Step 1: Radar -> Pi (USB Data CDC @ 921600 bps)
Step 2: Pi -> VEGA (UART0 @ 115200 bps): "H,2,0.65,-12.40,0.25\n"
Step 3: VEGA -> Pi (UART0 @ 115200 bps): "TEMP:29.0,AIR_PPM:3,AIR_STATUS:NORMAL,FALL:NO_FALL\n"
Step 4: Pi -> Dashboard (HTTP GET http://<PI_IP>:5000/api/data @ 1Hz)
Step 5: Dashboard parses JSON -> Updates 8 DOM cards smoothly without reload
```

---

## 11. Dashboard Features
The Incident Command Web Dashboard contains **8 dedicated metric cards**:
1. **HUMANS DETECTED (`cardHumanCount`)**: Displays `N DETECTED` (when count > 0), `NO HUMAN` (when count == 0), or `NO DATA`.
2. **NEAREST HUMAN (`cardNearestHuman`)**: Displays actual nearest target distance in meters (e.g. `0.65 m`) or `NO HUMAN`.
3. **ANGLE (`cardAngle`)**: Displays target azimuth angle in degrees (e.g. `-12.4°`) or `0.0°`.
4. **VELOCITY (`cardVelocity`)**: Displays target radial velocity (e.g. `0.25 m/s`) or `0.00 m/s`.
5. **TEMPERATURE (`cardTemperature`)**: Displays actual MLX90614 temperature (e.g. `29.0 °C`) with dynamic gauge and tags (`NORMAL`, `HIGH`, `CRITICAL`).
6. **AIR QUALITY / GAS (`cardAirQuality`)**: Displays actual MQ-135 numerical PPM value (e.g. `3`, `1200`), with status tags `NORMAL`, `GOOD`, `WARNING`, or `DANGER`.
7. **FALL STATUS (`cardFallStatus`)**: Permanently fixed display showing **`NO FALL`** and **`CONNECTED`**.
8. **SYSTEM CONNECTION (`cardSystemConnection`)**: Real-time heartbeat watchdog showing **`SYSTEM CONNECTED`** with millisecond latency, automatically shifting to **`SYSTEM DISCONNECTED`** if telemetry stops.

---

## 12. Testing Procedure
Testing is performed via the automated verification suite `test_dashboard_suite.py`:
1. Start the API server (`radar_pi_with_api.py` or `mock_pi_server.py`).
2. Run `python test_dashboard_suite.py`.
3. Verify that all 13 test cases pass, including the 3 core benchmark packets.

---

## 13. Expected Output

### Test Packet 1: Standby Baseline
- **Input**: `HUMAN:NO,COUNT:0,DIST:0.00,ANGLE:0.00,VELOCITY:0.00,TEMP:29.0,AIR_PPM:3,AIR_STATUS:NORMAL,FALL:NO_FALL`
- **Output**:
  - Humans Detected: `NO HUMAN`
  - Nearest Human: `NO HUMAN`
  - Angle: `0.0°`
  - Velocity: `0.00 m/s`
  - Temperature: `29.0 °C` (`NORMAL`)
  - Air Quality / Gas: `3` (`NORMAL` / `GOOD`)
  - Fall Status: `NO FALL` (`CONNECTED`)
  - System Connection: `SYSTEM CONNECTED`

### Test Packet 2: Proximity Human Detection
- **Input**: `HUMAN:YES,COUNT:2,DIST:0.65,ANGLE:-12.4,VELOCITY:0.25,TEMP:29.0,AIR_PPM:3,AIR_STATUS:NORMAL,FALL:NO_FALL`
- **Output**:
  - Humans Detected: `2 DETECTED`
  - Nearest Human: `0.65 m` (`VERY CLOSE`)
  - Angle: `-12.4°` (`TRACKED`)
  - Velocity: `0.25 m/s` (`TRACKED`)
  - Temperature: `29.0 °C` (`NORMAL`)
  - Air Quality / Gas: `3` (`NORMAL` / `GOOD`)
  - Fall Status: `NO FALL` (`CONNECTED`)
  - System Connection: `SYSTEM CONNECTED`

### Test Packet 3: Gas Hazard Escalation
- **Input**: `HUMAN:YES,COUNT:1,DIST:1.21,ANGLE:15.2,VELOCITY:0.10,TEMP:30.1,AIR_PPM:1200,AIR_STATUS:WARNING,FALL:DETECTED`
- **Output**:
  - Humans Detected: `1 DETECTED`
  - Nearest Human: `1.21 m` (`VERY CLOSE`)
  - Angle: `15.2°` (`TRACKED`)
  - Velocity: `0.10 m/s` (`TRACKED`)
  - Temperature: `30.1 °C` (`NORMAL`)
  - Air Quality / Gas: `1200` (`WARNING`)
  - Fall Status: `NO FALL` (`CONNECTED`) *(Invariance rule maintained)*
  - System Connection: `SYSTEM CONNECTED`

---

## 14. Installation & Setup Procedure
1. Clone or extract the `Smart_Firefighter_Safety_System_Final/` directory.
2. Install Python 3.8+ on the host PC or Raspberry Pi.
3. Install dependencies:
   ```bash
   pip install pyserial
   ```

---

## 15. How to Run Raspberry Pi
```bash
cd Raspberry_Pi
python radar_pi_with_api.py
```
*(Or for offline demonstration/grading without physical radar):*
```bash
python mock_pi_server.py
```

---

## 16. How to Run Dashboard
```bash
cd Dashboard
python -m http.server 8080
```
Open `http://localhost:8080` in your web browser.

---

## 17. VEGA ARIES V3 Programming Procedure
1. Open **Arduino IDE**.
2. Go to `Tools -> Board -> VEGA ARIES V3`.
3. Open `VEGA_ARIES_V3/vega_aries_v3.ino`.
4. Ensure required libraries (`Adafruit GFX`, `Adafruit SSD1306`, `DFRobotDFPlayerMini`) are installed.
5. Connect VEGA ARIES V3 via USB Type-C and click **Upload**.

---

## 18. Troubleshooting
- **Port Permission Denied on Linux/Raspberry Pi**:
  Run `sudo usermod -a -G dialout $USER` and log out/log in.
- **Radar Config File Not Found**:
  Ensure `AOP_6m_default.cfg` is located in `Radar/` or in the same directory as the Python script.
- **Dashboard Shows "SYSTEM DISCONNECTED"**:
  Confirm the Raspberry Pi script is running and port 5000 is accessible over your local network.

---

## 19. Future Improvements
1. **LoRaWAN / Long-Range Mesh Network**: Integrate long-range SX1262 LoRa transceivers for multi-kilometer transmission outside steel-reinforced structures.
2. **Thermal Core Fusion**: Combine mmWave radar point clouds with long-wave infrared (LWIR) radiometric thermal imaging.
3. **Multi-Vest Fleet Mesh**: Centralized multi-firefighter dashboard tracking an entire operational platoon on a 3D building floorplan.

---

## 20. Team & Project Information
- **Project Title**: Smart Firefighter Safety System
- **Controller Architecture**: VEGA ARIES V3 (THEJAS32 RISC-V SoC)
- **Target Platform**: Raspberry Pi OS & Modern Web Browsers
- **Submission Type**: Final Year Engineering / Capstone Project Submission
