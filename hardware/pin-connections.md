# Pin Connections

## 1. Raspberry Pi 3 → ARIES V3

| Raspberry Pi | ARIES V3 |
| USB Port | USB-C Port |
| Connection | USB Cable |
| GPIO TX/RX | Not Connected |

## 2. HC-05 → ARIES V3

| HC-05 Pin | ARIES V3 |
|---|---|
| VCC | +5V |
| GND | GND |
| TXD | RX1 |
| RXD | TX1 |

## 3. DFPlayer Mini → ARIES V3

| DFPlayer Pin | ARIES V3 |
|---|---|
| VCC | +5V |
| GND | GND |
| TX | RX2 |
| RX | TX2 through 1 kΩ resistor |
| SPK1 | Speaker + |
| SPK2 | Speaker − |

## 4. SSD1306 OLED → ARIES V3

| OLED Pin | ARIES V3 |
|---|---|
| VCC | 3.3V |
| GND | GND |
| SDA | I²C-0 SDA |
| SCL | I²C-0 SCL |

## 5. MLX90614 → ARIES V3

| MLX90614 Pin | ARIES V3 |
|---|---|
| VCC | 3.3V |
| GND | GND |
| SDA | Pin 3 |
| SCL | Pin 4 |

## 6. MQ-135 → ARIES V3

| MQ-135 Pin | ARIES V3 |
|---|---|
| VCC | 5V |
| GND | GND |
| AO | A0 |

## 7. MPU6050 → ARIES V3

| MPU6050 Pin | ARIES V3 |
|---|---|
| VCC | 3.3V |
| GND | GND |
| SDA | I²C-1 SDA |
| SCL | I²C-1 SCL |

## UART Assignment

| Function | ARIES V3 Interface | Baud Rate |
|---|---|---:|
| Raspberry Pi Radar | USB / Serial | 115200 |
| HC-05 | UART1 (TX1/RX1) | 9600 |
| DFPlayer Mini | UART2 (TX2/RX2) | 9600 |

## Important Connections

- HC-05 TXD → ARIES V3 RX1
- HC-05 RXD → ARIES V3 TX1
- DFPlayer TX → ARIES V3 RX2
- DFPlayer RX → ARIES V3 TX2 through 1 kΩ resistor
- Raspberry Pi communicates with ARIES V3 through USB
- Raspberry Pi GPIO TX/RX are not connected