# Texas Instruments IWR6843AOP mmWave Radar Configuration & Data Specification

## 1. Overview
The **IWR6843AOPEVM** is a single-chip 60-GHz to 64-GHz mmWave sensor with Antenna-on-Package (AoP) technology. It integrates a 4-receiver, 3-transmitter architecture with wide field-of-view (+/- 60° azimuth, +/- 60° elevation). In the Smart Firefighter Safety System, it performs human detection through dense smoke and fire where optical cameras and PIR sensors fail.

---

## 2. Serial Communication Interface
The IWR6843AOP communicates with the Raspberry Pi over two USB CDC serial ports:
- **CLI Control Port (`/dev/ttyACM0`)**:
  - Baud Rate: `115200`
  - Function: Uploads the sensor chirp and tracking configuration profile (`.cfg` file) and initiates radar framing.
- **Data Streaming Port (`/dev/ttyACM1`)**:
  - Baud Rate: `921600`
  - Function: Streams binary data packets containing the packet header and Type-Length-Value (TLV) payloads.

---

## 3. Data Packet Structure
Each binary frame sent over the Data Port begins with an 8-byte Magic Word:
```
Magic Word: 0x02 0x01 0x04 0x03 0x06 0x05 0x08 0x07
```

### Packet Header (40 bytes total):
| Field | Offset | Size (Bytes) | Type | Description |
|---|---|---|---|---|
| `magicWord` | 0 | 8 | uint64 | Sync word (`0x0102030405060708`) |
| `version` | 8 | 4 | uint32 | SDK Version / Radar Firmware |
| `totalPacketLen` | 12 | 4 | uint32 | Total frame byte length including header |
| `platform` | 16 | 4 | uint32 | Radar hardware platform ID |
| `frameNumber` | 20 | 4 | uint32 | Monotonically increasing sequence number |
| `timeCpuCycles` | 24 | 4 | uint32 | Radar DSP clock cycle count |
| `numDetectedObj` | 28 | 4 | uint32 | Total number of detected point-cloud points |
| `numTLVs` | 32 | 4 | uint32 | Number of TLV elements in this payload |
| `subFrameNumber` | 36 | 4 | uint32 | Active subframe index |

---

## 4. Key TLV Types Used in Project
- **TLV Type 1010 (`TARGET_LIST_TLV`)**:
  - Struct size: 112 bytes per tracked target.
  - Contains:
    - Target ID (`uint32`)
    - Position X, Y, Z in meters (`float32`)
    - Velocity Vx, Vy, Vz in m/s (`float32`)
    - Acceleration Ax, Ay, Az in m/s² (`float32`)
    - Error covariance matrix
- **TLV Type 1021 (`PRESENCE_TLV`)**:
  - Flag indicating whether motion or occupancy is detected in the monitored zone.

---

## 5. Coordinate Transformations
From Cartesian targets provided by the tracking engine, spherical coordinates are derived:
- **Radial Distance ($d$)**:
  $$\text{Distance} = \sqrt{x^2 + y^2 + z^2}$$
- **Azimuth Angle ($\theta$)**:
  $$\theta = \arctan2(x, y) \times \frac{180}{\pi}$$
- **Radial Velocity ($v_r$)**:
  $$v_r = \frac{x \cdot v_x + y \cdot v_y + z \cdot v_z}{d}$$

Targets are filtered within the firefighter spatial boundary:
- $X \in [-5.0, 5.0]\text{ m}$
- $Y \in [0.1, 10.0]\text{ m}$
- $Z \in [-2.0, 3.0]\text{ m}$
