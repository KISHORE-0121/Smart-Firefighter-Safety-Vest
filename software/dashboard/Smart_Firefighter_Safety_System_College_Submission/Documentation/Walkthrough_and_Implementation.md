# Walkthrough & Implementation Details

## 1. Executive Summary
This document provides a technical walkthrough of the **Smart Firefighter Safety System** codebase, detailing how each bug was eliminated, how telemetry is processed without fake data, and how the 8 dashboard cards are driven.

---

## 2. Bug Fixes & Code Enhancements

### A. Resolution of `ReferenceError: isAirActive is not defined`
* **Defect**: In previous versions of `script.js`, `isAirActive` was declared locally within an `if (hasAirVal) { const isAirActive = ...; }` statement. Later in the same render loop, the status banner evaluation referenced `isAirActive`. When `hasAirVal` was false or evaluated in a alternate branch, JavaScript threw a fatal `ReferenceError: isAirActive is not defined`, crashing the dashboard render engine and freezing live updates.
* **Fix**: In `script.js`, all sensor active flags:
  ```javascript
  const isRadarActive = (state.mode === 'demo') || (m.radarConnected && m.humanCount !== null && m.humanCount !== undefined);
  const isTempActive = (state.mode === 'demo') || (m.mlxConnected && m.temperature !== null && m.temperature !== undefined);
  const hasAirVal = (m.airQuality !== null && m.airQuality !== undefined && !isNaN(m.airQuality));
  const isAirActive = (state.mode === 'demo') || (m.mqConnected && hasAirVal) || hasAirVal;
  const hasMpuTelemetry = (m.pitch !== null && m.pitch !== undefined) || (m.roll !== null && m.roll !== undefined) || (m.accelMag !== null && m.accelMag !== undefined);
  const isMpuActive = (state.mode === 'demo') ? (m.mpuConnected !== false) : (m.mpuConnected && hasMpuTelemetry);
  ```
  were moved to the root of `updateUI()` and `displayDisconnectedMetrics()`. All conditions now execute safely without scope leaks or crashes.

### B. Dynamic MQ-135 Telemetry Flow (No Hardcoding)
* **Defect**: In earlier prototypes, MQ-135 was clamped strictly between 0 and 1023 in `radar_pi_with_api.py`, dropping high PPM values (e.g., 1200 or 1500).
* **Fix**:
  - `vega_aries_v3.ino` reads the analog pin A0, computes `displayAirPPM`, and transmits both:
    ```cpp
    Serial.print(",AIR_PPM:");
    Serial.print((int)round(displayAirPPM > 0 ? displayAirPPM : mq135Raw));
    Serial.print(",AIR_STATUS:");
    Serial.print(displayAirWarning ? "WARNING" : "NORMAL");
    ```
  - `radar_pi_with_api.py` parses `AIR_PPM` and `AIR` into numerical floats without 1023 clamping.
  - `script.js` extracts `air_quality.value` or `air_quality.ppm` and updates the value and status tag dynamically:
    - Normal gas concentrations display integer value with tags `NORMAL` and `GOOD`.
    - Elevated gas concentrations (>= 1000) display tags `WARNING` or `DANGER`.

### C. Fall Status Card Fixed Rule
* **Requirement**: The Fall Status card must **ALWAYS** show `NO FALL` and `CONNECTED`. Even if the incoming packet contains `FALL:DETECTED` or the MPU6050 disconnects, it must never switch to `FALL DETECTED`, `NO DATA`, or `DISCONNECTED`.
* **Fix**:
  - In `script.js`, both normal update routines and `displayDisconnectedMetrics()` enforce:
    ```javascript
    dom.valFallStatus.textContent = 'NO FALL';
    dom.valFallStatus.className = 'metric-value-huge text-safe val-text';
    dom.fallStatusPill.className = 'status-tag tag-safe';
    dom.fallStatusPill.textContent = 'CONNECTED';
    dom.fallIcon.className = 'fa-solid fa-person-walking card-icon';
    dom.cardFallStatus.classList.remove('card-fall-emergency');
    ```

---

## 3. The 8 Dedicated Metric Cards

1. **Card 1: HUMANS DETECTED (`cardHumanCount`)**
   - Displays `N DETECTED` (e.g. `2 DETECTED`) when humans > 0.
   - Displays `NO HUMAN` when humans == 0.
   - Displays `NO DATA` upon hardware disconnect or telemetry timeout.
2. **Card 2: NEAREST HUMAN (`cardNearestHuman`)**
   - Displays nearest distance in meters (`0.65 m`) when humans > 0.
   - Displays `NO HUMAN` when count == 0.
   - Displays `NO DATA` on timeout.
3. **Card 3: ANGLE (`cardAngle`)**
   - Displays azimuth angle in degrees (`-12.4°`) when humans > 0.
   - Displays `0.0°` when count == 0.
   - Displays `NO DATA` on timeout.
4. **Card 4: VELOCITY (`cardVelocity`)**
   - Displays radial target velocity (`0.25 m/s`) when humans > 0.
   - Displays `0.00 m/s` when count == 0.
   - Displays `NO DATA` on timeout.
5. **Card 5: TEMPERATURE (`cardTemperature`)**
   - Displays actual MLX90614 temperature (e.g. `29.0 °C`) with dynamic progress bar.
   - Status tags: `NORMAL` (< 50°C), `HIGH` (>= 50°C), `CRITICAL` (>= 60°C).
   - Displays `NO DATA` on timeout.
6. **Card 6: AIR QUALITY / GAS (`cardAirQuality`)**
   - Displays actual MQ-135 reading (e.g. `3`, `1200`).
   - Normal state: Sub-tag `NORMAL`, status tag `GOOD`.
   - Elevated state: Sub-tag `WARNING` or `DANGER`.
7. **Card 7: FALL STATUS (`cardFallStatus`)**
   - Strictly fixed: **`NO FALL`** and **`CONNECTED`**.
8. **Card 8: SYSTEM CONNECTION (`cardSystemConnection`)**
   - Displays **`SYSTEM CONNECTED`** with latency (ms) and heartbeat counter during active communication.
   - Switches to **`SYSTEM DISCONNECTED`** when telemetry exceeds 3–5 seconds timeout limit.
