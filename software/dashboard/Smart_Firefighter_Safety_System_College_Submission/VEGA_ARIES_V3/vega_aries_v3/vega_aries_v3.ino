// ============================================================
// VEGA ARIES V3 - FIREFIGHTER SAFETY VEST (HARDWARE SENSORS)
// ============================================================
//
// CONTROLLER: VEGA ARIES V3 (THEAS RISC-V SoC) ONLY
//
// HARDWARE CONNECTIONS:
// ------------------------------------------------------------
// 1. Radar input & Telemetry: Raspberry Pi <-> USB Serial (UART0 @ 115200 baud)
// 2. SSD1306 OLED: 128x64 I2C Address 0x3C on Wire(0) (SDA=Pin 3, SCL=Pin 4)
// 3. MLX90614 IR Temp: SDA Pin 3, SCL Pin 4 (VEGA_MLX90614)
// 4. MQ-135 Gas Sensor: Analog Pin A0 (Real Raw ADC 0-1023)
// 5. MPU6050 6-DOF IMU: I2C Address 0x68 on Wire(0) (Shared I2C bus)
// 6. DFPlayer Mini Audio: HardwareSerial(2) (UART2 @ 9600 baud)
// 7. HC-05 Bluetooth: HardwareSerial(1) (UART1 @ 9600 baud)
//
// RADAR INPUT FORMAT (from Raspberry Pi):
// ------------------------------------------------------------
// Human:    H,count,distance,angle,velocity\n
// No human: N,0,0,0,0\n
//
// USB SERIAL TELEMETRY TO RASPBERRY PI:
// ------------------------------------------------------------
// V,temp,mqRaw,fallDetected,possibleFall,pitch,roll,impact,mlxOk,mpuOk,mqOk\n
// ============================================================

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <math.h>

#include "VEGA_MLX90614.h"
#include <DFRobotDFPlayerMini.h>

// ============================================================
// OLED DISPLAY (SSD1306 128x64 on I2C-0)
// ============================================================

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define OLED_ADDRESS 0x3C

TwoWire Wire(0);
TwoWire Wire1(1);

Adafruit_SSD1306 display(
  SCREEN_WIDTH,
  SCREEN_HEIGHT,
  &Wire,
  OLED_RESET
);

// ============================================================
// MLX90614 TEMPERATURE SENSOR (GPIO 3, 4)
// ============================================================

#define MLX_SDA 3
#define MLX_SCL 4

VEGA_MLX90614 mlx(
  MLX_SDA,
  MLX_SCL
);

float temperature = 0.0;
bool mlxConnected = false;

// ============================================================
// MQ-135 AIR QUALITY / GAS SENSOR (Analog Pin A0)
// ============================================================

#define MQ135_PIN A0

int mq135Raw = 0;
float airQualityPPM = 0.0;
float displayAirPPM = 0.0;
bool displayAirWarning = false;
bool mqConnected = false;

#define AIR_WARNING_PPM 1000.0
#define MQ135_R0_KOHM 10.0
#define MQ135_RL_KOHM 10.0

// ============================================================
// MPU6050 6-DOF IMU (Probes Wire1 & Wire @ 0x68 / 0x69)
// ============================================================

#define MPU_PWR_MGMT_1   0x6B
#define MPU_SMPLRT_DIV   0x19
#define MPU_CONFIG       0x1A
#define MPU_ACCEL_CONFIG 0x1C
#define MPU_GYRO_CONFIG  0x1B
#define MPU_ACCEL_XOUT_H 0x3B
#define MPU_WHO_AM_I     0x75

bool mpuConnected = false;
uint8_t mpuAddress = 0x68;
TwoWire* mpuWire = &Wire1;

float accelX = 0.0, accelY = 0.0, accelZ = 1.0;
float gyroX = 0.0, gyroY = 0.0, gyroZ = 0.0;
float pitch = 0.0;
float roll = 0.0;
float impactMagnitude = 1.0;

// Fall Detection State Machine
enum FallDetectionState
{
  FALL_STATE_NORMAL,            // Normal standing/moving state (~1.0g)
  FALL_STATE_FREE_FALL,         // Stage 1: Free fall detected (< 0.5g)
  FALL_STATE_IMPACT,            // Stage 2: High impact (> 2.5g) following free fall
  FALL_STATE_ORIENTATION_CHECK, // Stage 3: Significant tilt sustained check (>= 60 deg)
  FALL_STATE_DETECTED           // Stage 4: Confirmed fall emergency
};

FallDetectionState fallState = FALL_STATE_NORMAL;
unsigned long freeFallStartTime = 0;
unsigned long impactTime = 0;
unsigned long orientationStartTime = 0;
unsigned long uprightStartTime = 0;

const float THRESHOLD_FREE_FALL      = 0.5;   // Stage 1: Free fall (< 0.5g)
const float THRESHOLD_IMPACT         = 2.5;   // Stage 2: Strong impact (> 2.5g)
const float THRESHOLD_TILT_DEG       = 60.0;  // Stage 3: Post-fall orientation tilt (>= 60 deg)
const unsigned long FREE_FALL_TIMEOUT_MS   = 800;  // Impact must follow within 800ms of free fall
const unsigned long IMPACT_TIMEOUT_MS      = 1000; // Orientation check window after impact
const unsigned long ORIENTATION_CONFIRM_MS = 1500; // Orientation tilt sustained for 1.5s confirms fall
const unsigned long RECOVERY_UPRIGHT_MS    = 1200; // Standing upright for 1.2s auto-recovers to NORMAL

bool possibleFall = false;
bool fallDetected = false;

// ============================================================
// HC-05 BLUETOOTH (UART1)
// ============================================================

HardwareSerial Bluetooth(1);

// ============================================================
// DFPLAYER MINI (UART2)
// ============================================================

HardwareSerial DFSerial(2);
DFRobotDFPlayerMini dfPlayer;
bool dfPlayerReady = false;

// ============================================================
// RADAR VARIABLES (from Raspberry Pi)
// ============================================================

bool humanDetected = false;
int humanCount = 0;
float distance = 0.0;
float angle = 0.0;
float velocity = 0.0;

// 10-Second Snapshot for OLED & DFPlayer
bool displayHumanDetected = false;
int displayHumanCount = 0;
float displayDistance = 0.0;
float displayAngle = 0.0;
float displayVelocity = 0.0;

// ============================================================
// AUDIO STATE MACHINE
// ============================================================

bool previousHighTemperature = false;
bool previousPoorAir = false;

enum AudioState
{
  AUDIO_IDLE,
  AUDIO_HUMAN,
  AUDIO_COUNT,
  AUDIO_DISTANCE_WHOLE,
  AUDIO_DISTANCE_POINT,
  AUDIO_DISTANCE_DECIMAL1,
  AUDIO_DISTANCE_DECIMAL2,
  AUDIO_DISTANCE_METER,
  AUDIO_NO_HUMAN
};

AudioState audioState = AUDIO_IDLE;
unsigned long lastAudioAction = 0;
int audioHumanCount = 0;
float audioDistance = 0.0;

// ============================================================
// SERIAL BUFFERS & TIMERS
// ============================================================

String radarBuffer = "";

unsigned long lastSensorRead = 0;
unsigned long lastTelemetrySend = 0;
unsigned long lastOLEDPage = 0;
unsigned long lastBluetooth = 0;
unsigned long lastRadarSnapshot = 0;

int currentPage = 0;

#define SENSOR_INTERVAL      200   // Read IMU & environment fast
#define TELEMETRY_INTERVAL   250   // Send V,... packet to Raspberry Pi
#define OLED_PAGE_TIME       2500  // Cycle OLED page
#define BLUETOOTH_INTERVAL   1000  // HC-05 report
#define RADAR_UPDATE_INTERVAL 10000 // 10s voice snapshot
#define AUDIO_STEP_INTERVAL  1000  // Non-blocking voice step

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

void initMPU6050();
void readMPU6050();
void processFallDetection();
void readTemperature();
void readAirQuality();
void sendTelemetryToPi();
void readRadarData();
void playTrack(uint16_t track);
void speakNumber(int number);
void speakDistance(float d);
void startRadarAudio();
void updateRadarSnapshot();
void processRadarAudio();
void playTemperatureWarning();
void playAirWarning();
void processWarningAudio();
void showHumanPage();
void showMotionPage();
void showEnvironmentPage();
void showStatusPage();
void showStartup();

// ============================================================
// MPU6050 INITIALIZATION & READING
// ============================================================

bool probeMpu(TwoWire* bus, uint8_t addr)
{
  bus->beginTransmission(addr);
  bus->write(MPU_WHO_AM_I);
  if (bus->endTransmission() != 0) return false;

  bus->requestFrom((uint8_t)addr, (uint8_t)1);
  if (bus->available())
  {
    byte who = bus->read();
    if (who == 0x68 || who == 0x70 || who == 0x72)
    {
      return true;
    }
  }
  return false;
}

void initMPU6050()
{
  Serial.println("[MPU6050] Initializing...");
  mpuConnected = false;

  // Probe I2C1 (Wire1) first, then I2C0 (Wire) across addresses 0x68 and 0x69
  if (probeMpu(&Wire1, 0x68)) {
    mpuWire = &Wire1;
    mpuAddress = 0x68;
    mpuConnected = true;
  } else if (probeMpu(&Wire1, 0x69)) {
    mpuWire = &Wire1;
    mpuAddress = 0x69;
    mpuConnected = true;
  } else if (probeMpu(&Wire, 0x68)) {
    mpuWire = &Wire;
    mpuAddress = 0x68;
    mpuConnected = true;
  } else if (probeMpu(&Wire, 0x69)) {
    mpuWire = &Wire;
    mpuAddress = 0x69;
    mpuConnected = true;
  }

  if (!mpuConnected)
  {
    Serial.println("[MPU6050] NOT DETECTED");
    return;
  }

  // Wake up MPU6050 (clear sleep bit in PWR_MGMT_1)
  mpuWire->beginTransmission(mpuAddress);
  mpuWire->write(MPU_PWR_MGMT_1);
  mpuWire->write(0x00);
  mpuWire->endTransmission();
  delay(50);

  // Set sample rate divider
  mpuWire->beginTransmission(mpuAddress);
  mpuWire->write(MPU_SMPLRT_DIV);
  mpuWire->write(0x07);
  mpuWire->endTransmission();

  // Set low-pass filter (44 Hz)
  mpuWire->beginTransmission(mpuAddress);
  mpuWire->write(MPU_CONFIG);
  mpuWire->write(0x03);
  mpuWire->endTransmission();

  // Accel range ±2g (16384 LSB/g)
  mpuWire->beginTransmission(mpuAddress);
  mpuWire->write(MPU_ACCEL_CONFIG);
  mpuWire->write(0x00);
  mpuWire->endTransmission();

  // Gyro range ±250 deg/s (131 LSB/deg/s)
  mpuWire->beginTransmission(mpuAddress);
  mpuWire->write(MPU_GYRO_CONFIG);
  mpuWire->write(0x00);
  mpuWire->endTransmission();

  Serial.println("[MPU6050] Connected");
}

void readMPU6050()
{
  if (!mpuConnected)
  {
    // Retry initialization once every 3 seconds
    static unsigned long lastRetry = 0;
    if (millis() - lastRetry > 3000)
    {
      lastRetry = millis();
      initMPU6050();
    }
    return;
  }

  mpuWire->beginTransmission(mpuAddress);
  mpuWire->write(MPU_ACCEL_XOUT_H);
  if (mpuWire->endTransmission() != 0)
  {
    mpuConnected = false;
    Serial.println("[MPU6050] NOT DETECTED");
    return;
  }

  mpuWire->requestFrom((uint8_t)mpuAddress, (uint8_t)14);
  if (mpuWire->available() < 14)
  {
    return;
  }

  int16_t rawAx = (mpuWire->read() << 8) | mpuWire->read();
  int16_t rawAy = (mpuWire->read() << 8) | mpuWire->read();
  int16_t rawAz = (mpuWire->read() << 8) | mpuWire->read();
  int16_t rawT  = (mpuWire->read() << 8) | mpuWire->read(); // Chip internal temp
  int16_t rawGx = (mpuWire->read() << 8) | mpuWire->read();
  int16_t rawGy = (mpuWire->read() << 8) | mpuWire->read();
  int16_t rawGz = (mpuWire->read() << 8) | mpuWire->read();

  // Convert to g (±2g range)
  accelX = rawAx / 16384.0;
  accelY = rawAy / 16384.0;
  accelZ = rawAz / 16384.0;

  // Impact / Total acceleration magnitude: sqrt(ax*ax + ay*ay + az*az)
  impactMagnitude = sqrt(accelX * accelX + accelY * accelY + accelZ * accelZ);

  // Convert to deg/s (±250 dps range)
  gyroX = rawGx / 131.0;
  gyroY = rawGy / 131.0;
  gyroZ = rawGz / 131.0;

  // Calculate Pitch and Roll (in degrees)
  pitch = atan2(-accelX, sqrt(accelY * accelY + accelZ * accelZ)) * (180.0 / 3.14159265);
  roll  = atan2(accelY, accelZ) * (180.0 / 3.14159265);

  // Execute multi-stage fall detection algorithm
  processFallDetection();

  // Throttled serial debug (1000ms interval, non-flooding)
  static unsigned long lastMpuDebug = 0;
  if (millis() - lastMpuDebug >= 1000)
  {
    lastMpuDebug = millis();
    const char* stateName = "NO_FALL";
    if (fallState == FALL_STATE_FREE_FALL) stateName = "FREE_FALL";
    else if (fallState == FALL_STATE_IMPACT) stateName = "IMPACT";
    else if (fallState == FALL_STATE_ORIENTATION_CHECK) stateName = "ORIENTATION_CHECK";
    else if (fallState == FALL_STATE_DETECTED) stateName = "FALL_DETECTED";

    Serial.print("AX="); Serial.print(accelX, 2);
    Serial.print(" AY="); Serial.print(accelY, 2);
    Serial.print(" AZ="); Serial.print(accelZ, 2);
    Serial.print(" GX="); Serial.print(gyroX, 1);
    Serial.print(" GY="); Serial.print(gyroY, 1);
    Serial.print(" GZ="); Serial.print(gyroZ, 1);
    Serial.print(" Pitch="); Serial.print(pitch, 1);
    Serial.print(" Roll="); Serial.print(roll, 1);
    Serial.print(" Impact="); Serial.print(impactMagnitude, 2);
    Serial.print(" FallState="); Serial.println(stateName);
  }
}

void processFallDetection()
{
  if (!mpuConnected)
  {
    fallState = FALL_STATE_NORMAL;
    fallDetected = false;
    possibleFall = false;
    return;
  }

  unsigned long now = millis();
  bool isTilted = (fabs(pitch) >= THRESHOLD_TILT_DEG || fabs(roll) >= THRESHOLD_TILT_DEG);
  bool isUpright = (fabs(pitch) < 35.0 && fabs(roll) < 35.0);

  switch (fallState)
  {
    case FALL_STATE_NORMAL:
      fallDetected = false;
      possibleFall = false;
      // STAGE 1 — FREE FALL: accelMagnitude < 0.5 g
      if (impactMagnitude < THRESHOLD_FREE_FALL)
      {
        fallState = FALL_STATE_FREE_FALL;
        freeFallStartTime = now;
        possibleFall = true;
      }
      break;

    case FALL_STATE_FREE_FALL:
      possibleFall = true;
      // STAGE 2 — IMPACT: After free fall, detect strong impact > 2.5 g
      if (impactMagnitude > THRESHOLD_IMPACT)
      {
        fallState = FALL_STATE_IMPACT;
        impactTime = now;
      }
      else if (now - freeFallStartTime > FREE_FALL_TIMEOUT_MS)
      {
        // Timeout: Free fall without high-g impact -> reset to NORMAL
        fallState = FALL_STATE_NORMAL;
        possibleFall = false;
      }
      break;

    case FALL_STATE_IMPACT:
      possibleFall = true;
      // STAGE 3 — POST-FALL ORIENTATION: Check whether firefighter orientation changes significantly
      if (isTilted)
      {
        fallState = FALL_STATE_ORIENTATION_CHECK;
        orientationStartTime = now;
      }
      else if (now - impactTime > IMPACT_TIMEOUT_MS)
      {
        // Timeout: Impact happened, but firefighter remained upright -> false alarm
        fallState = FALL_STATE_NORMAL;
        possibleFall = false;
      }
      break;

    case FALL_STATE_ORIENTATION_CHECK:
      possibleFall = true;
      if (!isTilted)
      {
        // Orientation returned upright before 1.5s -> recovered balance, reset to NORMAL
        fallState = FALL_STATE_NORMAL;
        possibleFall = false;
      }
      else if (now - orientationStartTime >= ORIENTATION_CONFIRM_MS)
      {
        // Firefighter orientation tilted >= 60 deg sustained for 1.5s -> FALL DETECTED!
        fallState = FALL_STATE_DETECTED;
        fallDetected = true;
        possibleFall = false;
        uprightStartTime = 0;
      }
      break;

    case FALL_STATE_DETECTED:
      fallDetected = true;
      possibleFall = false;
      // Recovery: Firefighter stands back upright
      if (isUpright)
      {
        if (uprightStartTime == 0)
        {
          uprightStartTime = now;
        }
        else if (now - uprightStartTime >= RECOVERY_UPRIGHT_MS)
        {
          fallState = FALL_STATE_NORMAL;
          fallDetected = false;
          uprightStartTime = 0;
        }
      }
      else
      {
        uprightStartTime = 0;
      }
      break;
  }
}

// ============================================================
// MLX90614 TEMPERATURE
// ============================================================

void readTemperature()
{
  float rawTemp = mlx.mlx90614ReadAmbientTempC();

  // Strict physical validity check (MLX90614 ambient range: -40 to +125 C)
  if (!isnan(rawTemp) && rawTemp >= -40.0 && rawTemp <= 125.0)
  {
    temperature = rawTemp;
    mlxConnected = true;
  }
  else
  {
    mlxConnected = false;
  }
}

// ============================================================
// MQ-135 AIR QUALITY (Real Raw ADC 0-1023)
// ============================================================

void readAirQuality()
{
  long total = 0;
  const int samples = 10;
  for (int i = 0; i < samples; i++)
  {
    total += analogRead(MQ135_PIN);
    delay(2);
  }
  float adc = (float)total / samples;
  mq135Raw = (int)round(adc);

  if (adc < 1.0) adc = 1.0;
  float RS = MQ135_RL_KOHM * ((1023.0 / adc) - 1.0);
  float ratio = RS / MQ135_R0_KOHM;
  float ppm = 116.6020682 * pow(ratio, -2.769034857);
  if (ppm < 0.0) ppm = 0.0;

  displayAirPPM = ppm;
  airQualityPPM = displayAirPPM;
  displayAirWarning = (airQualityPPM > AIR_WARNING_PPM);
  mqConnected = (mq135Raw >= 0 && mq135Raw <= 1023);
}

float readMQ135PPM()
{
  return displayAirPPM;
}

// ============================================================
// TELEMETRY TO RASPBERRY PI (UART0 USB @ 115200)
// ============================================================

void sendTelemetryToPi()
{
  // 1. Compact V-format for high-speed parsing
  // Format: V,temp,mqVal,fallDetected,possibleFall,pitch,roll,impact,mlxOk,mpuOk,mqOk\n
  Serial.print("V,");

  if (mlxConnected)
  {
    Serial.print(temperature, 1);
  }
  else
  {
    Serial.print("-999.0");
  }
  Serial.print(",");

  if (mqConnected)
  {
    Serial.print((int)round(displayAirPPM > 0 ? displayAirPPM : mq135Raw));
  }
  else
  {
    Serial.print("-1");
  }
  Serial.print(",");

  Serial.print(fallDetected ? "1" : "0");
  Serial.print(",");

  Serial.print(possibleFall ? "1" : "0");
  Serial.print(",");

  if (mpuConnected)
  {
    Serial.print(pitch, 1);
    Serial.print(",");
    Serial.print(roll, 1);
    Serial.print(",");
    Serial.print(impactMagnitude, 2);
  }
  else
  {
    Serial.print("0.0,0.0,0.00");
  }
  Serial.print(",");

  Serial.print(mlxConnected ? "1" : "0");
  Serial.print(",");
  Serial.print(mpuConnected ? "1" : "0");
  Serial.print(",");
  Serial.println(mqConnected ? "1" : "0");

  // 2. Standard Key-Value Telemetry (transmits real AIR_PPM and AIR_STATUS)
  Serial.print("TEMP:");
  Serial.print(mlxConnected ? temperature : -999.0, 1);
  Serial.print(",AIR_PPM:");
  Serial.print((int)round(displayAirPPM > 0 ? displayAirPPM : mq135Raw));
  Serial.print(",AIR_STATUS:");
  Serial.print(displayAirWarning ? "WARNING" : "NORMAL");
  Serial.print(",FALL:");
  Serial.println(mpuConnected ? (fallDetected ? "DETECTED" : "NO_FALL") : "NO_DATA");
}

// ============================================================
// DFPLAYER TRACK PLAYER
// ============================================================

void playTrack(uint16_t track)
{
  if (!dfPlayerReady) return;
  dfPlayer.playMp3Folder(track);
}

void speakNumber(int number)
{
  if (number == 0)
  {
    playTrack(14);
  }
  else if (number >= 1 && number <= 9)
  {
    playTrack(4 + number);
  }
}

void speakDistance(float d)
{
  if (d < 0.0) return;

  int wholeNumber = (int)d;
  int decimalNumber = (int)((d - wholeNumber) * 100.0 + 0.5);
  if (decimalNumber >= 100) decimalNumber = 99;

  if (wholeNumber >= 0 && wholeNumber <= 9)
  {
    speakNumber(wholeNumber);
  }

  if (decimalNumber > 0)
  {
    playTrack(15); // POINT
    int tens = decimalNumber / 10;
    int ones = decimalNumber % 10;
    if (tens > 0) speakNumber(tens);
    speakNumber(ones);
  }

  playTrack(16); // METER
}

void startRadarAudio()
{
  if (!dfPlayerReady || audioState != AUDIO_IDLE) return;

  audioHumanCount = displayHumanCount;
  audioDistance = displayDistance;

  if (displayHumanDetected)
  {
    audioState = AUDIO_HUMAN;
  }
  else
  {
    audioState = AUDIO_NO_HUMAN;
  }

  lastAudioAction = millis() - AUDIO_STEP_INTERVAL;
}

void updateRadarSnapshot()
{
  displayHumanDetected = humanDetected;
  displayHumanCount = humanCount;
  displayDistance = distance;
  displayAngle = angle;
  displayVelocity = velocity;

  if (currentPage == 0) showHumanPage();
  else if (currentPage == 1) showMotionPage();
  else if (currentPage == 2) showEnvironmentPage();
  else if (currentPage == 3) showStatusPage();

  startRadarAudio();
}

void processRadarAudio()
{
  if (!dfPlayerReady) return;
  unsigned long now = millis();

  if (audioState == AUDIO_IDLE) return;
  if (now - lastAudioAction < AUDIO_STEP_INTERVAL) return;

  lastAudioAction = now;

  if (audioState == AUDIO_HUMAN)
  {
    playTrack(1); // 0001: Human Detected
    audioState = AUDIO_COUNT;
  }
  else if (audioState == AUDIO_COUNT)
  {
    if (audioHumanCount >= 1 && audioHumanCount <= 9) speakNumber(audioHumanCount);
    audioState = AUDIO_DISTANCE_WHOLE;
  }
  else if (audioState == AUDIO_DISTANCE_WHOLE)
  {
    int whole = (int)audioDistance;
    if (whole < 0) whole = 0;
    if (whole > 9) whole = 9;
    speakNumber(whole);
    audioState = AUDIO_DISTANCE_POINT;
  }
  else if (audioState == AUDIO_DISTANCE_POINT)
  {
    playTrack(15); // 0015: Point
    audioState = AUDIO_DISTANCE_DECIMAL1;
  }
  else if (audioState == AUDIO_DISTANCE_DECIMAL1)
  {
    int digit = ((int)(audioDistance * 10.0)) % 10;
    if (digit < 0) digit = 0;
    speakNumber(digit);
    audioState = AUDIO_DISTANCE_DECIMAL2;
  }
  else if (audioState == AUDIO_DISTANCE_DECIMAL2)
  {
    int digit = ((int)(audioDistance * 100.0)) % 10;
    if (digit < 0) digit = 0;
    speakNumber(digit);
    audioState = AUDIO_DISTANCE_METER;
  }
  else if (audioState == AUDIO_DISTANCE_METER)
  {
    playTrack(16); // 0016: Meter
    audioState = AUDIO_IDLE;
  }
  else if (audioState == AUDIO_NO_HUMAN)
  {
    playTrack(2); // 0002: No Human Detected
    audioState = AUDIO_IDLE;
  }
}

void playTemperatureWarning()
{
  playTrack(4); // 0004: High Temperature Warning
}

bool previousHighTemperature = false;
bool previousPoorAir = false;
bool previousFallDetected = false;

void playAirWarning()
{
  playTrack(3); // 0003: Low Air Quality Warning
}

void playFallWarning()
{
  playTrack(4); // 0004: Emergency Alert / Fall Warning
}

void processWarningAudio()
{
  bool highTemp = (mlxConnected && temperature > 60.0);
  bool poorAir  = (mqConnected && airQualityPPM > 1000.0);

  if (audioState == AUDIO_IDLE)
  {
    if (fallDetected && !previousFallDetected)
    {
      playFallWarning();
    }
    else if (highTemp && !previousHighTemperature)
    {
      playTemperatureWarning();
    }
    else if (poorAir && !previousPoorAir)
    {
      playAirWarning();
    }
  }

  previousFallDetected = fallDetected;
  previousHighTemperature = highTemp;
  previousPoorAir = poorAir;
}

// ============================================================
// READ RADAR DATA FROM RASPBERRY PI
// ============================================================

void readRadarData()
{
  while (Serial.available())
  {
    char c = Serial.read();

    if (c == '\n' || c == '\r')
    {
      if (radarBuffer.length() > 0)
      {
        String data = radarBuffer;
        radarBuffer = "";

        if (data.startsWith("H,"))
        {
          int c1 = data.indexOf(',');
          int c2 = data.indexOf(',', c1 + 1);
          int c3 = data.indexOf(',', c2 + 1);
          int c4 = data.indexOf(',', c3 + 1);

          if (c1 > 0 && c2 > c1 && c3 > c2 && c4 > c3)
          {
            humanDetected = true;
            humanCount = data.substring(c1 + 1, c2).toInt();
            distance = data.substring(c2 + 1, c3).toFloat();
            angle = data.substring(c3 + 1, c4).toFloat();
            velocity = data.substring(c4 + 1).toFloat();
          }
        }
        else if (data.startsWith("N,"))
        {
          humanDetected = false;
          humanCount = 0;
          distance = 0.0;
          angle = 0.0;
          velocity = 0.0;
        }
      }
    }
    else
    {
      radarBuffer += c;
      if (radarBuffer.length() > 100)
      {
        radarBuffer = "";
      }
    }
  }
}

// ============================================================
// OLED DISPLAY PAGES
// ============================================================

void showHumanPage()
{
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  if (displayHumanDetected && displayHumanCount > 0)
  {
    display.setTextSize(2);
    display.setCursor(5, 0);
    display.println("HUMAN");
    display.println("DETECTED");

    display.setTextSize(1);
    display.setCursor(0, 38);
    display.print("COUNT: ");
    display.println(displayHumanCount);

    display.setCursor(0, 52);
    display.print("DIST:  ");
    display.print(displayDistance, 2);
    display.println(" m");
  }
  else
  {
    // Display explicitly as NO HUMAN DETECTED
    display.setTextSize(2);
    display.setCursor(5, 10);
    display.println("NO HUMAN");
    display.setCursor(5, 34);
    display.println("DETECTED");
  }

  display.display();
}

void showMotionPage()
{
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  display.setTextSize(2);
  display.setCursor(0, 0);
  display.println("ANGLE");

  display.setTextSize(1);
  display.setCursor(0, 20);
  display.print(displayAngle, 2);
  display.println(" deg");

  display.setTextSize(2);
  display.setCursor(0, 35);
  display.println("VELOCITY");

  display.setTextSize(1);
  display.setCursor(0, 55);
  display.print(displayVelocity, 2);
  display.println(" m/s");

  display.display();
}

void showEnvironmentPage()
{
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("TEMPERATURE");

  display.setTextSize(2);
  display.setCursor(0, 10);
  if (mlxConnected)
  {
    display.print(temperature, 1);
    display.println(" C");
  }
  else
  {
    display.println("NO DATA");
  }

  display.setTextSize(1);
  display.setCursor(0, 35);
  display.println("AIR QUALITY (RAW)");

  display.setTextSize(2);
  display.setCursor(0, 45);
  if (mqConnected)
  {
    display.print(mq135Raw);
  }
  else
  {
    display.println("NO DATA");
  }

  display.display();
}

void showStatusPage()
{
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  display.setTextSize(2);
  display.setCursor(0, 0);
  display.println("FALL STATUS");

  display.setTextSize(2);
  display.setCursor(0, 22);
  if (!mpuConnected)
  {
    display.println("NO DATA");
  }
  else if (fallDetected)
  {
    display.println("! FALL !");
  }
  else if (possibleFall)
  {
    display.println("CHECKING");
  }
  else
  {
    display.println("SAFE");
  }

  display.setTextSize(1);
  display.setCursor(0, 50);
  if (fallDetected)
  {
    display.println("EMERGENCY ALERT!");
  }
  else if (mlxConnected && temperature > 60.0)
  {
    display.println("HIGH TEMP WARNING");
  }
  else if (mqConnected && airQualityPPM > 1000.0)
  {
    display.println("AIR QUALITY HAZARD");
  }
  else
  {
    display.println("OVERALL: SAFE");
  }

  display.display();
}

void showStartup()
{
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  display.setTextSize(2);
  display.setCursor(5, 10);
  display.println("FIREFIGHTER");

  display.setCursor(35, 30);
  display.println("VEST");

  display.setTextSize(1);
  display.setCursor(40, 52);
  display.println("ARIES V3");

  display.display();
}

// ============================================================
// SETUP
// ============================================================

void setup()
{
  // UART0: Raspberry Pi Radar & Telemetry
  Serial.begin(115200);
  delay(500);

  Serial.println("================================");
  Serial.println(" VEGA ARIES V3 FIREFIGHTER VEST");
  Serial.println("================================");

  // Initialize I2C bus (Wire0)
  Wire.begin();

  // Initialize OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS))
  {
    Serial.println("OLED FAILED");
  }
  else
  {
    showStartup();
  }

  // Initialize MPU6050
  initMPU6050();

  // Initialize HC-05 Bluetooth (UART1)
  Bluetooth.begin(9600);

  // Initialize DFPlayer Mini (UART2)
  DFSerial.begin(9600);
  delay(300);

  if (dfPlayer.begin(DFSerial, false, false))
  {
    dfPlayerReady = true;
    dfPlayer.volume(25);
    delay(200);
    dfPlayer.stop();
    Serial.println("DFPLAYER READY");
  }
  else
  {
    dfPlayerReady = false;
    Serial.println("DFPLAYER NOT FOUND");
  }

  // Initialize MQ-135 ADC
  pinMode(MQ135_PIN, INPUT);

  // Initial sensor read
  readTemperature();
  readAirQuality();
  readMPU6050();

  delay(2000);

  lastRadarSnapshot = millis() - RADAR_UPDATE_INTERVAL;
  Serial.println("VEGA ARIES V3 SYSTEM INITIALIZED");
}

// ============================================================
// MAIN LOOP
// ============================================================

void loop()
{
  // 1. Read Radar packets from Raspberry Pi
  readRadarData();

  // 2. Read Sensors (MLX90614, MQ-135, MPU6050)
  unsigned long now = millis();
  if (now - lastSensorRead >= SENSOR_INTERVAL)
  {
    lastSensorRead = now;
    readTemperature();
    readAirQuality();
    readMPU6050();
  }

  // 3. Send Telemetry to Raspberry Pi (USB Serial UART0)
  if (now - lastTelemetrySend >= TELEMETRY_INTERVAL)
  {
    lastTelemetrySend = now;
    sendTelemetryToPi();
  }

  // 4. Update Radar Snapshot every 10 seconds for OLED & Audio
  if (now - lastRadarSnapshot >= RADAR_UPDATE_INTERVAL)
  {
    lastRadarSnapshot = now;
    updateRadarSnapshot();
  }

  // 5. Process Non-Blocking DFPlayer Audio Announcements & Warnings
  processRadarAudio();
  processWarningAudio();

  // 6. Cycle OLED Pages every 2.5 seconds
  if (now - lastOLEDPage >= OLED_PAGE_TIME)
  {
    lastOLEDPage = now;
    currentPage++;
    if (currentPage > 3) currentPage = 0;

    if (currentPage == 0) showHumanPage();
    else if (currentPage == 1) showMotionPage();
    else if (currentPage == 2) showEnvironmentPage();
    else if (currentPage == 3) showStatusPage();
  }

  // 7. Bluetooth HC-05 Broadcast (UART1)
  if (now - lastBluetooth >= BLUETOOTH_INTERVAL)
  {
    lastBluetooth = now;

    Bluetooth.print("HUMAN:");
    Bluetooth.print(humanDetected ? "YES" : "NO");
    Bluetooth.print(",COUNT:");
    Bluetooth.print(humanCount);
    Bluetooth.print(",DIST:");
    Bluetooth.print(distance, 2);
    Bluetooth.print(",ANGLE:");
    Bluetooth.print(angle, 2);
    Bluetooth.print(",VELOCITY:");
    Bluetooth.print(velocity, 2);
    Bluetooth.print(",TEMP:");
    Bluetooth.print(mlxConnected ? temperature : -999.0, 1);
    Bluetooth.print(",AIR_PPM:");
    Bluetooth.print((int)round(displayAirPPM > 0 ? displayAirPPM : mq135Raw));
    Bluetooth.print(",AIR_STATUS:");
    Bluetooth.print(displayAirWarning ? "WARNING" : "NORMAL");
    Bluetooth.print(",FALL:");
    if (!mpuConnected)
    {
      Bluetooth.print("NO_DATA");
    }
    else
    {
      Bluetooth.print(fallDetected ? "DETECTED" : "NO_FALL");
    }
    Bluetooth.print(",PITCH:");
    Bluetooth.print(pitch, 1);
    Bluetooth.print(",ROLL:");
    Bluetooth.print(roll, 1);
    Bluetooth.print(",IMPACT:");
    Bluetooth.println(impactMagnitude, 2);
  }
}
