# System Architecture

## 1. Project Overview

The **Smart Firefighter Safety Vest** is an intelligent wearable safety system developed to improve firefighter safety and situational awareness in hazardous and zero-visibility environments.

The system combines **environmental sensors** and an **IWR6843AOP mmWave radar** with an embedded processing system. The environmental sensors monitor safety-related parameters such as temperature and gas conditions, while the mmWave radar provides human/target detection capability even when conventional visual detection is difficult.

The system uses a **VEGA processor** for embedded sensor interfacing and processing. A **USB Host interface** can be used to connect USB-based devices such as the radar to the VEGA platform.

A **Raspberry Pi 3 is used as an optional external processing platform**, particularly when additional computational resources are required for radar-data processing, Python-based processing, testing, or development.

The processed information is presented to the firefighter through a **TFT display**, while the **DFPlayer Mini and speaker** provide audio and voice warnings.

The overall system is designed to provide multiple forms of safety information through **sensor monitoring, radar-based detection, visual indication, and audio alerts**.

---

## 2. Overall System Architecture

The Smart Firefighter Safety Vest consists of the following major functional blocks:

```text
                    ┌─────────────────────────┐
                    │   Environmental Sensors │
                    │                         │
                    │ Temperature / Gas /     │
                    │ Safety Parameters       │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     VEGA Processor      │
                    │                         │
                    │ Sensor Data Acquisition │
                    │ Processing & Control    │
                    └────────────┬────────────┘
                                 │
                         USB / Serial
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Raspberry Pi 3        │
                    │      (Optional)         │
                    │                         │
                    │ Radar/Data Processing   │
                    │ Communication & Control │
                    └────────────┬────────────┘
                                 │
                                 │
                    ┌────────────▼────────────┐
                    │    IWR6843AOP mmWave    │
                    │         Radar           │
                    │                         │
                    │   Human / Target        │
                    │      Detection          │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Detection / Safety      │
                    │ Data Processing         │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
          ┌──────────────────┐      ┌──────────────────┐
          │   TFT Display    │      │  DFPlayer Mini   │
          │                  │      │                  │
          │ Sensor Readings  │      │ Voice / Audio    │
          │ Radar Status     │      │ Alerts            │
          │ Warning Status   │      │                  │
          └──────────────────┘      └────────┬─────────┘
                                             │
                                             ▼
                                          Speaker
```

### Primary Embedded Architecture

When the VEGA processor has the required USB Host capability and sufficient processing resources, the Raspberry Pi is not required for the basic system architecture.

```text
Environmental Sensors
          │
          ▼
    VEGA Processor
          ▲
          │
    USB Host Module
          ▲
          │
   IWR6843AOP Radar
          │
          ▼
   Radar Data Processing
          │
     ┌────┴────┐
     ▼         ▼
TFT Display  DFPlayer
                │
                ▼
             Speaker
```

### Optional Raspberry Pi Architecture

The Raspberry Pi 3 can be used when additional processing capability is required.

```text
IWR6843AOP Radar
        │
        ▼
 Raspberry Pi 3
        │
        ▼
Radar Data Processing
        │
        ▼
Detection Information
        │
        ├──────────► TFT Display
        │
        └──────────► DFPlayer Mini
                         │
                         ▼
                      Speaker
```

---

## 3. Major System Components

### 3.1 Environmental Sensors

Environmental sensors are integrated into the firefighter safety vest to monitor conditions that may affect firefighter safety.

The sensor subsystem can monitor parameters such as:

* Temperature
* Gas/environmental conditions
* Other safety-related parameters depending on the sensors integrated into the vest

The sensor readings are acquired by the VEGA processor and processed before being presented to the firefighter.

---

### 3.2 IWR6843AOP mmWave Radar

The **IWR6843AOP mmWave radar** is a core sensing component of the system.

It is used to detect humans or other targets in the firefighter's surrounding environment.

The radar operates using millimeter-wave signals and does not depend on visible light for target detection. This makes it particularly useful for firefighter applications where smoke, darkness, or other conditions can result in **zero or severely reduced visibility**.

The radar produces measurement data that is transferred to the processing system for target detection and analysis.

The basic radar flow is:

```text
IWR6843AOP mmWave Radar
            │
            ▼
       Radar Data
            │
            ▼
   USB Host / Processing Unit
            │
            ▼
     Radar Data Processing
            │
            ▼
      Target Detection
```

---

### 3.3 VEGA Processor

The **VEGA processor** acts as the primary embedded controller of the firefighter safety vest.

Its responsibilities include:

* Acquiring environmental sensor data
* Processing sensor readings
* Communicating with external devices
* Managing system-level operations
* Providing processed information to the output devices

The VEGA processor can also interface with the mmWave radar through a suitable **USB Host module**, allowing the system to be implemented without a Raspberry Pi when the required processing and software support are available.

---

### 3.4 USB Host Module

The **USB Host module** provides the required USB host interface for connecting compatible USB devices to the VEGA processor.

In the proposed architecture, the USB Host module can be used to interface with the mmWave radar.

The communication path is:

```text
IWR6843AOP Radar
        │
        ▼
 USB Host Module
        │
        ▼
  VEGA Processor
```

This provides a compact alternative to using an external Raspberry Pi for USB communication.

---

### 3.5 Raspberry Pi 3 — Optional

The **Raspberry Pi 3 is an optional processing platform**.

It can be used when additional processing capability is required, especially for:

* Radar-data processing
* Python-based applications
* Development and testing
* Data visualization
* Communication with additional peripherals
* More computationally demanding processing

The Raspberry Pi is therefore **not considered a mandatory component of the core embedded architecture**.

---

### 3.6 TFT Display

The TFT display provides visual feedback to the firefighter.

It can display information such as:

* Temperature readings
* Gas/sensor readings
* Radar detection status
* Human/target detection information
* Warning conditions
* System status

The display presents the latest processed information so that the firefighter can quickly understand the current safety status.

---

### 3.7 DFPlayer Mini and Speaker

The **DFPlayer Mini** is used to provide pre-recorded voice and audio alerts.

When an important warning condition is detected, the processing unit sends a command to the DFPlayer Mini. The selected audio file is then played through the connected speaker.

```text
Safety Condition
       │
       ▼
Processing Unit
       │
       ▼
DFPlayer Mini
       │
       ▼
Speaker
       │
       ▼
Voice / Audio Warning
```

Audio alerts provide an additional warning method when the firefighter cannot continuously observe the TFT display.

---

## 4. Radar Subsystem

The radar subsystem is responsible for detecting humans or targets in the firefighter's surroundings.

The **IWR6843AOP mmWave radar** is particularly important for operation in **zero-visibility environments**, where smoke or darkness can severely limit conventional visual detection.

The radar continuously generates measurement data. The data is transferred to the processing system through the available communication interface.

Depending on the system configuration, radar data can be processed either by the VEGA processor through the USB Host interface or by the optional Raspberry Pi 3.

### Radar Processing Flow

```text
                 IWR6843AOP
                 mmWave Radar
                       │
                       ▼
                Raw Radar Data
                       │
                       ▼
                USB Interface
                       │
                       ▼
                 USB Host Module
                       │
                       ▼
                  VEGA Processor
                       │
                       ▼
             Radar Data Processing
                       │
                       ▼
                Target Detection
                       │
                       ▼
             Human / Target Status
                       │
                ┌──────┴──────┐
                ▼             ▼
           TFT Display    Audio Alert
```

### Optional Raspberry Pi Radar Processing

```text
IWR6843AOP Radar
       │
       ▼
 Raspberry Pi 3
       │
       ▼
Radar Processing
       │
       ▼
Human / Target Detection
```

The radar subsystem adds a sensing capability that does not depend on visible light, making it valuable for firefighter operations in **zero-visibility and low-visibility environments**.

---

## 5. Communication Architecture

The system uses communication interfaces to exchange information between the VEGA processor, radar, and output devices.

The primary architecture is based on the VEGA processor and USB Host module.

```text
Environmental Sensors
          │
          ▼
    VEGA Processor
          │
          ├──────────────► TFT Display
          │
          └──────────────► DFPlayer Mini
                                  │
                                  ▼
                               Speaker

IWR6843AOP Radar
          │
          ▼
    USB Host Module
          │
          ▼
    VEGA Processor
```

The USB Host module provides the interface required for communication between the VEGA processor and the USB-compatible radar interface.

### Optional Raspberry Pi Communication

When the Raspberry Pi 3 is used, it can act as an additional processing and communication unit.

```text
VEGA Processor
      │
      │ USB / Serial
      ▼
Raspberry Pi 3
      │
      ▼
Radar / Data Processing
      │
      ├──────────► TFT Display
      │
      └──────────► DFPlayer Mini
```

The Raspberry Pi is therefore an **optional processing layer rather than a required component of the basic architecture**.

---

## 6. Data Processing

The system continuously acquires environmental and radar information and processes the data to provide safety-related information to the firefighter.

### Processing Sequence

1. The environmental sensors measure the required parameters.
2. The VEGA processor acquires the sensor readings.
3. The VEGA processes the sensor data.
4. The IWR6843AOP mmWave radar detects surrounding targets.
5. Radar data is transferred through the available USB interface.
6. The USB Host module provides the interface to the VEGA when the standalone architecture is used.
7. Radar data is processed to identify human/target information.
8. Sensor and radar information are evaluated.
9. The system determines the current safety status.
10. The latest information is displayed on the TFT.
11. When an alert condition occurs, the DFPlayer Mini provides an audio warning.
12. The system continues monitoring continuously.

### Data Processing Flow

```text
       Environmental Sensors
                │
                ▼
        VEGA Data Acquisition
                │
                ▼
        Sensor Data Processing
                │
                │
                │
        IWR6843AOP Radar
                │
                ▼
        USB Host Interface
                │
                ▼
        Radar Data Processing
                │
                ▼
      Sensor + Radar Evaluation
                │
                ▼
         Safety Decision
                │
         ┌──────┴──────┐
         ▼             ▼
    TFT Display    Audio Alert
         │             │
         └──────┬──────┘
                ▼
       Continuous Monitoring
```

---

## 7. TFT Display

The TFT display acts as the primary visual interface for the firefighter.

The display provides information such as:

* Environmental sensor readings
* Temperature
* Gas-related readings
* Radar detection status
* Human/target detection information
* Warning conditions
* System status

The display is updated with the latest available processed information.

The visual interface allows the firefighter to quickly identify important safety information without requiring an external monitoring device.

---

## 8. Audio Alert System

The audio alert system uses the **DFPlayer Mini and speaker** to provide pre-recorded voice warnings.

The system uses audio alerts as a complementary warning mechanism because the firefighter may not always be able to look at the TFT display while operating.

### Audio Alert Flow

```text
Environmental / Radar Condition
              │
              ▼
       Safety Evaluation
              │
              ▼
        Warning Detected
              │
              ▼
        DFPlayer Mini
              │
              ▼
           Speaker
              │
              ▼
        Voice Warning
```

The audio system provides an additional channel of communication between the safety system and the firefighter.

---

## 9. System Operating Cycle

The complete system operates continuously after power-on.

```text
                POWER ON
                   │
                   ▼
          Initialize Hardware
                   │
                   ▼
          Initialize Sensors
                   │
                   ▼
         Initialize USB Host
                   │
                   ▼
       Initialize mmWave Radar
                   │
                   ▼
         Initialize TFT Display
                   │
                   ▼
       Initialize Audio Module
                   │
                   ▼
              Read Sensors
                   │
                   ▼
          Receive Radar Data
                   │
                   ▼
            Process Data
                   │
                   ▼
        Evaluate Safety Status
                   │
            ┌──────┴──────┐
            ▼             ▼
          NORMAL        WARNING
            │             │
            ▼             ▼
       Display Data   Display Warning
                          │
                          ▼
                     Audio Warning
                          │
            └──────┬──────┘
                   ▼
        Continue Monitoring
                   │
                   └──────► Repeat
```

The continuous operating cycle allows the system to monitor the firefighter's environment throughout operation.

---

## 10. Hardware Architecture

The major hardware components of the Smart Firefighter Safety Vest are:

| Component                 | Function                                                                                                    |
| ------------------------- | ----------------------------------------------------------------------------------------------------------- |
| VEGA Processor            | Main embedded controller for sensor acquisition, processing, and system control                             |
| USB Host Module           | Provides USB host connectivity for interfacing compatible USB devices                                       |
| IWR6843AOP mmWave Radar   | Human/target detection, including operation in zero-visibility environments                                 |
| Environmental Sensors     | Measurement of temperature, gas, and other safety-related environmental parameters                          |
| TFT Display               | Visual display of sensor readings, radar status, warnings, and system information                           |
| DFPlayer Mini             | Playback of pre-recorded voice and audio alerts                                                             |
| Speaker                   | Produces audible warning and voice notifications                                                            |
| Power Supply              | Provides electrical power to the system                                                                     |
| Raspberry Pi 3 (Optional) | Additional processing platform for advanced radar processing, Python applications, testing, and development |

### Primary Hardware Configuration

```text
             Environmental Sensors
                      │
                      ▼
                VEGA Processor
                      ▲
                      │
               USB Host Module
                      ▲
                      │
             IWR6843AOP Radar
                      │
                      ▼
              Radar Processing
                      │
              ┌───────┴───────┐
              ▼               ▼
         TFT Display     DFPlayer Mini
                              │
                              ▼
                           Speaker
```

### Optional Raspberry Pi Configuration

```text
             IWR6843AOP Radar
                      │
                      ▼
                Raspberry Pi 3
                      │
                      ▼
             Radar Processing
                      │
              ┌───────┴───────┐
              ▼               ▼
         TFT Display     DFPlayer Mini
                              │
                              ▼
                           Speaker
```

The Raspberry Pi 3 is optional and can be omitted when the VEGA processor and USB Host module are capable of handling the required radar communication and processing.

---

## 11. Software Architecture

The software is divided into functional modules for sensor acquisition, radar communication, data processing, safety evaluation, display control, and audio control.

```text
┌───────────────────────────────────┐
│        Main Embedded Program      │
├───────────────────────────────────┤
│ Environmental Sensor Acquisition  │
├───────────────────────────────────┤
│ USB Host Communication             │
├───────────────────────────────────┤
│ mmWave Radar Communication         │
├───────────────────────────────────┤
│ Radar Data Processing              │
├───────────────────────────────────┤
│ Sensor Data Processing             │
├───────────────────────────────────┤
│ Safety Condition Evaluation        │
├───────────────────────────────────┤
│ TFT Display Control                │
├───────────────────────────────────┤
│ DFPlayer Audio Control              │
└───────────────────────────────────┘
```

The software continuously receives available sensor and radar information, processes the data, evaluates safety conditions, and updates the firefighter interface.

When the Raspberry Pi 3 is used, Python-based software can be used for radar communication, processing, system integration, and testing.

---

## 12. Safety Decision Layer

The safety decision layer evaluates information obtained from the environmental sensors and the mmWave radar.

The system can use the available sensor and radar information to determine the current safety condition.

The system states can include:

* **Normal**
* **Warning**
* **Danger**

The corresponding information is provided to the firefighter through the TFT display and, when required, through an audio alert.

```text
Sensor Data ───────────┐
                       │
                       ▼
                Safety Decision
                       ▲
                       │
Radar Data ────────────┘
                       │
               ┌───────┴───────┐
               ▼               ▼
          TFT Display      Audio Alert
```

The decision layer allows multiple sensing sources to contribute to the overall safety-monitoring process.

---

## 13. Advantages of the Architecture

The proposed architecture provides the following advantages:

* Continuous environmental monitoring.
* mmWave radar-based human/target detection.
* Detection capability in zero-visibility and low-visibility environments.
* Reduced dependence on conventional visual detection.
* Integration of multiple sensing technologies.
* Real-time embedded data processing.
* Visual warnings through the TFT display.
* Audio and voice warnings through the DFPlayer Mini.
* Compact embedded implementation using the VEGA processor and USB Host module.
* Raspberry Pi 3 can be added when additional processing capability is required.
* Modular hardware and software architecture.
* Expandable design for additional firefighter safety features.
* Multiple information channels for improved firefighter situational awareness.

---

## 14. Future Expansion

The system architecture can be extended with additional firefighter safety and monitoring features, including:

* GPS-based firefighter location tracking.
* Wireless communication with a control room.
* Emergency SOS button.
* Fall detection.
* Additional gas-specific sensors.
* Thermal imaging integration.
* Mesh-network communication.
* Remote monitoring dashboard.
* Centralized firefighter status monitoring.
* Additional biometric sensors.
* Real-time remote alert transmission.

The modular architecture allows future components to be integrated without completely redesigning the existing system.

---

## 15. Conclusion

The **Smart Firefighter Safety Vest** integrates environmental sensing, **IWR6843AOP mmWave radar-based human/target detection**, embedded processing, visual indication, and audio warning into a wearable firefighter safety system.

The **VEGA processor** acts as the primary embedded controller for sensor acquisition, processing, and system control. The **USB Host module** provides an interface for connecting compatible USB devices, including the mmWave radar.

The **IWR6843AOP mmWave radar** provides target-detection capability without depending on visible light, making it particularly useful for firefighter operations in **zero-visibility and severely reduced-visibility environments**.

The **TFT display** provides visual information to the firefighter, while the **DFPlayer Mini and speaker** provide pre-recorded voice and audio alerts.

The **Raspberry Pi 3 is an optional processing platform**. It can be used when additional computational resources, Python-based processing, advanced radar-data processing, or development and testing capabilities are required. When the VEGA processor and USB Host module can perform the required operations, the Raspberry Pi can be omitted from the primary embedded implementation.

Overall, the architecture provides a modular and expandable platform for improving firefighter situational awareness and safety through the integration of environmental sensing, radar-based detection, visual feedback, and audio warnings.
