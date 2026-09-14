# Smart Firefighter Vest

## Project Overview
A smart safety vest designed to assist firefighters through real-time monitoring, human detection, environmental sensing, and audio/visual alerts.

> **Note:** Replace the placeholder sections below with your team's actual implementation details.

## Key Features
- Human detection using TI mmWave radar
- Environmental/temperature monitoring
- Fall detection/status monitoring
- TFT display for live readings
- Audio alerts using DFPlayer Mini
- Raspberry Pi / VEGA based processing and communication
- Monitoring dashboard

## System Architecture
```text
Sensors + TI mmWave Radar
          |
          v
   Processing / Control
   Raspberry Pi + VEGA
          |
     +----+----+
     |         |
     v         v
 TFT Display  DFPlayer Mini
     |
     v
 Monitoring Dashboard
```

## Hardware
See `hardware/components-list.md`.

## Software
- Raspberry Pi code: `software/raspberry-pi/`
- VEGA code: `software/vega/`
- Dashboard code: `software/dashboard/`
- Radar documentation/configuration: `radar/`

## Repository Structure
See the folders in this repository.

## Setup
Add your actual installation, wiring, dependencies, serial-port settings, and run commands here.

## Testing
Add measured test results here.

## Team
- Member 1:
- Member 2:
- Member 3:


