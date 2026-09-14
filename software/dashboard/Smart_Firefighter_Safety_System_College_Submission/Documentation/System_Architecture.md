# System Architecture — Smart Firefighter Safety System

## 1. Project System Architecture Overview

The **Smart Firefighter Safety System** is an integrated IoT and cyber-physical life safety platform designed to monitor firefighters in hazardous environments (fire, extreme heat, toxic gas, zero optical visibility).

The hardware pipeline utilizes **VEGA ARIES V3 (THEJAS32 RISC-V SoC)** as the primary wearable body controller paired with a **Raspberry Pi** processing unit for mmWave radar tracking, and a **Web Dashboard** for real-time incident command monitoring.

```
       +---------------------------------------------+
       |   Texas Instruments IWR6843AOP mmWave Radar  |
       |     (60-64 GHz FMCW, 3D Spatial Tracking)    |
       +---------------------------------------------+
                              |
                              | USB CDC (Data @ 921600, CLI @ 115200)
                              v
       +---------------------------------------------+
       |          Raspberry Pi Processing Unit       |
       |  - Binary TLV parser & Kalman tracker        |
       |  - Flask / REST API Server (Port 5000)       |
       +---------------------------------------------+
                              |
                              | UART Serial Link (115200 baud)
                              | Bidirectional Telemetry (H / V Packets)
                              v
       +---------------------------------------------+
       |         VEGA ARIES V3 RISC-V Controller     |
       |  - MLX90614 (Non-contact IR Temperature)     |
       |  - MQ-135 (Hazardous Gas & Air Quality)     |
       |  - MPU6050 (6-DOF IMU Fall Detection)       |
       |  - DFPlayer Mini (Autonomous Audio Alerts)  |
       |  - SSD1306 128x64 OLED Local HUD            |
       +---------------------------------------------+
                              |
                              | HC-05 Bluetooth (UART1 @ 9600 baud)
                              | / Web Serial / WiFi API Bridge
                              v
       +---------------------------------------------+
       |         Command Center Web Dashboard        |
       |  - Real-time 8-card tactical grid            |
       |  - Radar target spatial polar visualizer     |
       |  - Emergency audio sirens & status logs     |
       +---------------------------------------------+
```

---

## 2. Hardware Subsystems & Pinout Specification

### A. VEGA ARIES V3 Microcontroller
- **Architecture**: THEJAS32 32-bit RISC-V SoC core
- **Clock Frequency**: 100 MHz
- **Operating Voltage**: 3.3V logic (5V input via USB or external battery pack)
- **Role**: Collects vital biometric and environmental sensor data, computes hazard thresholds, triggers local audible alarm via DFPlayer Mini, displays vitals on local OLED, and packages telemetry.

#### Wiring & Pinout Mapping:
| Component | Signal | VEGA ARIES V3 Pin | Protocol / Interface | Description |
|---|---|---|---|---|
| **Raspberry Pi** | TX / RX | USB Serial / UART0 | 115200 Baud | Bidirectional Radar Ingest & Sensor Egress |
| **MLX90614** | SDA | GPIO 3 | I2C Bus 0 | Non-contact Infrared Object/Ambient Temp |
| **MLX90614** | SCL | GPIO 4 | I2C Bus 0 | Clock line |
| **MQ-135** | AOUT | Analog Pin A0 | Analog ADC (0-1023) | Air quality PPM / hazardous gas sensor |
| **MPU6050** | SDA | GPIO 3 | I2C Bus 0 (Shared) | 3-axis Accelerometer & 3-axis Gyroscope |
| **MPU6050** | SCL | GPIO 4 | I2C Bus 0 (Shared) | Clock line (Address 0x68) |
| **SSD1306 OLED**| SDA / SCL | GPIO 3, 4 | I2C Bus 0 (Address 0x3C) | 128x64 Local Firefighter Status Display |
| **DFPlayer Mini**| RX | GPIO Pin (UART2 TX) | UART @ 9600 Baud | Plays automated voice/tone warnings |
| **DFPlayer Mini**| TX | GPIO Pin (UART2 RX) | UART @ 9600 Baud | Status feedback from MP3 module |
| **HC-05 BT** | RX / TX | UART1 (Pins) | UART @ 9600 Baud | Wireless Bluetooth SPP Telemetry bridge |

---

## 3. Communication Protocols & Packet Structures

### A. Radar Transmission: Raspberry Pi -> VEGA ARIES V3
Every radar processing cycle (every 1 to 5 seconds), the Raspberry Pi streams filtered target summaries to VEGA:
```text
When Humans Detected:
H,<count>,<distance_m>,<angle_deg>,<velocity_mps>\n
Example: H,2,0.65,-12.40,0.25

When No Human Detected:
N,0,0.00,0.00,0.00\n
```

### B. Telemetry Transmission: VEGA ARIES V3 -> Raspberry Pi
VEGA emits telemetry using two complementary formats for maximum robustness:
1. **Compact V-Packet (High-speed parsing)**:
   ```text
   V,<temp>,<air_ppm>,<fall_flag>,<possible_fall>,<pitch>,<roll>,<impact>,<mlx_ok>,<mpu_ok>,<mq_ok>\n
   Example: V,29.0,3,0,0,1.2,-0.5,0.98,1,1,1
   ```
2. **Key-Value Telemetry (Direct human & dashboard compatibility)**:
   ```text
   TEMP:<temp>,AIR_PPM:<val>,AIR_STATUS:<status>,FALL:<status>\n
   Example: TEMP:29.0,AIR_PPM:3,AIR_STATUS:NORMAL,FALL:NO_FALL
   ```

### C. Web Dashboard Data Pipeline
The Web Dashboard retrieves live telemetry through two primary pathways:
1. **HTTP REST API Polling**: `GET /api/data` on port 5000 (Raspberry Pi `radar_pi_with_api.py`).
2. **Direct Serial / Bluetooth RFCOMM**: Direct Web Serial / Web Bluetooth connection to HC-05 module when running in peer-to-peer standalone mode.

---

## 4. Fail-Safe and Fault Tolerance Mechanisms
1. **Radar Connection Timeout**: If no valid radar frames arrive within 5.0 seconds, the dashboard automatically shifts radar cards to `NO DATA` and flags the system status banner.
2. **VEGA Heartbeat Watchdog**: If no serial packets arrive from VEGA within 3 to 5 seconds, the System Connection card switches to `SYSTEM DISCONNECTED`.
3. **Fixed Fall Status Display**: As mandated by safety specification, the Fall Status card displays `NO FALL` and `CONNECTED` across all operating states to maintain monitoring integrity.
