# Working Principle

The Smart Firefighter Safety Vest collects environmental and human-detection information using sensors and the IWR6843AOP mmWave radar. The VEGA processor and Raspberry Pi 3 process the received data and provide warnings to the firefighter.

## Normal Operation

When the vest is powered ON, the sensors, radar, VEGA, Raspberry Pi 3, TFT display, and audio system are initialized.

The system continuously collects sensor and radar data and updates the firefighter with the current safety information.

## Human Detection

The IWR6843AOP mmWave radar detects human targets around the firefighter.

The radar data is processed by the system to identify the presence and movement of a target.

The detected information is displayed on the TFT display and can be used to generate an alert.

## Environmental Alert

The environmental sensors continuously monitor the surrounding conditions.

When a sensor value reaches the configured warning level, the system generates an alert.

The warning information is shown on the TFT display and an audio alert can be played.

## Fall Alert

The system monitors the firefighter's movement for a configured fall condition.

When a fall is detected, the system generates a warning and activates the audio and display alerts.

## Audio Alert

The DFPlayer Mini plays pre-recorded voice messages when an important warning condition occurs.

This allows the firefighter to receive alerts even when visibility is poor.

## Display Update

The TFT display shows the latest available information such as:

- Temperature
- Environmental sensor values
- Human/radar detection
- Warning status
- System status

## Dashboard Update

The processed data can be sent to the dashboard through the HC - 05 .

The dashboard provides a remote view of the firefighter's safety information and system status.