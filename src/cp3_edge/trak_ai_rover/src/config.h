#pragma once

// WiFi
#define WIFI_SSID     "WIFI_ADIN"
#define WIFI_PASSWORD "WIFI_SIFREN"

// MQTT
#define MQTT_BROKER   "192.168.1.102"
#define MQTT_PORT     1883
#define MQTT_TOPIC    "trakaia/rover/data"
#define MQTT_CLIENT   "trak-ai-rover-01"

// Sensör Pinleri
#define SEN0193_1_PIN   34
#define SEN0193_2_PIN   35
#define DHT22_PIN        4
#define HCSR04_F_TRIG    5
#define HCSR04_F_ECHO   18
#define HCSR04_B_TRIG   19
#define HCSR04_B_ECHO   21

// Motor Pinleri (L298N)
#define MOTOR_IN1   26
#define MOTOR_IN2   27
#define MOTOR_IN3   14
#define MOTOR_IN4   12
#define MOTOR_ENA   25
#define MOTOR_ENB   33

// GPS (UART2)
#define GPS_RX_PIN  16
#define GPS_TX_PIN  17
#define GPS_BAUD    9600

// ESP32-CAM (UART1) — GPIO 1/3 USB pinleri; 22/23 kullan
#define CAM_RX_PIN  22
#define CAM_TX_PIN  23

// Kalibrasyon Katsayıları (sensör gelince güncellenecek)
#define CAL_A   0.0000023f
#define CAL_B  -0.0213f
#define CAL_C   52.4f

// Motor Hızı
#define MOTOR_SPEED_NORMAL  180
#define MOTOR_SPEED_SLOW    100
#define ENGEL_ESIK_CM        30

// Zamanlama
#define SENSOR_INTERVAL_MS  30000
#define MQTT_INTERVAL_MS    30000