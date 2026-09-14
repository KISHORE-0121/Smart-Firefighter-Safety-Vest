# Setup and Run Guide — Smart Firefighter Safety System

## 1. Hardware Required
1. **VEGA ARIES V3 Board** (THEJAS32 RISC-V SoC)
2. **Raspberry Pi** (Model 4B, 3B+, or Zero 2W running Raspberry Pi OS)
3. **Texas Instruments IWR6843AOPEVM mmWave Radar**
4. **MLX90614 Contactless Infrared Temperature Sensor** (I2C)
5. **MQ-135 Gas / Air Quality Sensor** (Analog Output)
6. **MPU6050 6-DOF IMU Sensor** (I2C)
7. **SSD1306 128x64 OLED Display** (I2C Address 0x3C)
8. **DFPlayer Mini MP3 Player Module** + MicroSD Card + Speaker
9. **HC-05 Bluetooth Module** (UART)
10. Connecting jumper wires, breadboard, and 5V USB power cables

---

## 2. Flashing the VEGA ARIES V3 Firmware

1. Install the **Arduino IDE** (version 1.8.19 or 2.x).
2. Install the **VEGA ARIES Board Support Package**:
   - Open `File -> Preferences`.
   - Add the VEGA Aries board URL: `https://vegaprocessors.in/packages/package_vega_index.json`
   - Open `Tools -> Board -> Boards Manager`, search for **ARIES**, and click **Install**.
3. Install the required Arduino libraries via Library Manager:
   - `Adafruit GFX Library`
   - `Adafruit SSD1306`
   - `DFRobotDFPlayerMini`
4. Connect the VEGA ARIES V3 board via USB Type-C cable.
5. In Arduino IDE:
   - Select `Tools -> Board -> VEGA ARIES V3`.
   - Select the corresponding COM port.
   - Open `Smart_Firefighter_Safety_System_Final/VEGA_ARIES_V3/vega_aries_v3.ino`.
   - Click **Verify** (Compile) and then **Upload**.
6. The on-board OLED display will initialize, display the system splash screen, and start reading sensors.

---

## 3. Configuring the Raspberry Pi

1. Open a terminal on the Raspberry Pi:
   ```bash
   cd ~/Smart_Firefighter_Safety_System_Final/Raspberry_Pi
   ```
2. Install the serial communication dependency:
   ```bash
   pip3 install -r requirements.txt
   ```
3. Connect the hardware:
   - Connect **IWR6843AOP** via USB (creates `/dev/ttyACM0` for CLI and `/dev/ttyACM1` for Data).
   - Connect **VEGA ARIES V3** via USB (creates `/dev/ttyUSB0`).
4. Ensure serial port permissions:
   ```bash
   sudo usermod -a -G dialout $USER
   ```
5. Run the live hardware processing bridge:
   ```bash
   python3 radar_pi_with_api.py
   ```
   *Note: For testing and demonstration when hardware is offline or on a development PC, run:*
   ```bash
   python3 mock_pi_server.py
   ```

---

## 4. Launching the Web Dashboard

1. Navigate to the `Dashboard` directory:
   ```bash
   cd ~/Smart_Firefighter_Safety_System_Final/Dashboard
   ```
2. Start an HTTP server:
   ```bash
   python3 -m http.server 8080
   ```
3. Open any modern web browser (Google Chrome or Microsoft Edge recommended) and navigate to:
   ```text
   http://localhost:8080
   ```
4. The dashboard will automatically connect to the live API on port 5000, display real-time sensor vitals on all 8 cards, and show tracked radar targets.

---

## 5. Running the Automated Test Suite

To run the automated verification suite:
```bash
python3 test_dashboard_suite.py
```
All 13 tests will execute and confirm system readiness.
