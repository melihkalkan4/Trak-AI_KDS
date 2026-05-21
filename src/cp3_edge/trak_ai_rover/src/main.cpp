#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <TinyGPSPlus.h>
#include <ArduinoJson.h>
#include "config.h"

// Nesneler
WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);
DHT          dht(DHT22_PIN, DHT22);
TinyGPSPlus  gps;
HardwareSerial gpsSerial(2);
HardwareSerial camSerial(1);

// Zamanlama
unsigned long lastSensorTime = 0;
unsigned long lastMqttTime   = 0;

// Veri yapısı
struct SensorData {
  float nem1_pct    = 0;
  float nem2_pct    = 0;
  float hava_temp   = 0;
  float hava_nem    = 0;
  long  engel_on    = 999;
  long  engel_arka  = 999;
  float gps_lat     = 0;
  float gps_lon     = 0;
  bool  gps_valid   = false;
  String bbch_sinif = "BILINMIYOR";
  float bbch_guven  = 0;
  int   waypoint_id = 0;
  String image_b64  = "";  // base64 JPEG ("" = görüntü yok)
};
SensorData veri;

// Waypoint listesi (tarlaya göre güncellenecek)
struct Waypoint { double lat; double lon; };
const int WP_COUNT = 6;
Waypoint waypoints[WP_COUNT] = {
  {41.6938, 27.1045},
  {41.6940, 27.1050},
  {41.6942, 27.1045},
  {41.6942, 27.1050},
  {41.6944, 27.1045},
  {41.6944, 27.1050},
};
int currentWP = 0;

// ── Kalibrasyon ──────────────────────────────────────────────────
float adcToNem(int adcRaw) {
  float x = (float)adcRaw;
  float nem = CAL_A * x * x + CAL_B * x + CAL_C;
  return constrain(nem, 0.0f, 100.0f);
}

// ── Ultrasonik ───────────────────────────────────────────────────
long mesafeOlc(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long sure = pulseIn(echoPin, HIGH, 30000);
  if (sure == 0) return 999;
  return sure * 0.034 / 2;
}

// ── Motor Kontrol ─────────────────────────────────────────────────
// ESP32'de analogWrite() yok — LEDC kanalları (setup'ta tanımlanır)
#define LEDC_ENA 0
#define LEDC_ENB 1

void motorDur() {
  digitalWrite(MOTOR_IN1, LOW); digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, LOW); digitalWrite(MOTOR_IN4, LOW);
  ledcWrite(LEDC_ENA, 0);       ledcWrite(LEDC_ENB, 0);
}

void motorIleri(int hiz = MOTOR_SPEED_NORMAL) {
  ledcWrite(LEDC_ENA, hiz);     ledcWrite(LEDC_ENB, hiz);
  digitalWrite(MOTOR_IN1, HIGH); digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, HIGH); digitalWrite(MOTOR_IN4, LOW);
}

void motorGeri(int hiz = MOTOR_SPEED_NORMAL) {
  ledcWrite(LEDC_ENA, hiz);     ledcWrite(LEDC_ENB, hiz);
  digitalWrite(MOTOR_IN1, LOW);  digitalWrite(MOTOR_IN2, HIGH);
  digitalWrite(MOTOR_IN3, LOW);  digitalWrite(MOTOR_IN4, HIGH);
}

void motorSolaDon(int hiz = MOTOR_SPEED_SLOW) {
  ledcWrite(LEDC_ENA, hiz);     ledcWrite(LEDC_ENB, hiz);
  digitalWrite(MOTOR_IN1, LOW);  digitalWrite(MOTOR_IN2, HIGH);
  digitalWrite(MOTOR_IN3, HIGH); digitalWrite(MOTOR_IN4, LOW);
}

void motorSagaDon(int hiz = MOTOR_SPEED_SLOW) {
  ledcWrite(LEDC_ENA, hiz);     ledcWrite(LEDC_ENB, hiz);
  digitalWrite(MOTOR_IN1, HIGH); digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, LOW);  digitalWrite(MOTOR_IN4, HIGH);
}

// ── Navigasyon ────────────────────────────────────────────────────
double haversineMetre(double lat1, double lon1, double lat2, double lon2) {
  const double R = 6371000.0;
  double dLat = (lat2 - lat1) * PI / 180.0;
  double dLon = (lon2 - lon1) * PI / 180.0;
  double a = sin(dLat/2)*sin(dLat/2) +
             cos(lat1*PI/180.0)*cos(lat2*PI/180.0)*
             sin(dLon/2)*sin(dLon/2);
  return R * 2 * atan2(sqrt(a), sqrt(1-a));
}

void waypointNavigasyon() {
  if (!veri.gps_valid || currentWP >= WP_COUNT) {
    motorDur();
    return;
  }
  if (veri.engel_on < ENGEL_ESIK_CM) {
    motorDur();
    delay(500);
    motorGeri(MOTOR_SPEED_SLOW);
    delay(1000);
    motorSolaDon();
    delay(800);
    return;
  }
  double mesafe = haversineMetre(
    gps.location.lat(), gps.location.lng(),
    waypoints[currentWP].lat, waypoints[currentWP].lon
  );
  if (mesafe < 2.0) {
    motorDur();
    veri.waypoint_id = currentWP;
    delay(3000);
    // Waypoint'te duruldu — kameraya anlık görüntü al komutu gönder
    camSerial.println("CAPTURE");
    Serial.println("[CAM] CAPTURE komutu gonderildi");
    delay(2000);  // CAM'in encode + gönderme süresi için bekle
    currentWP++;
    return;
  }
  motorIleri();
}

// ── ESP32-CAM Veri Okuma ─────────────────────────────────────────
void camVerisiOku() {
  if (camSerial.available()) {
    String json = camSerial.readStringUntil('\n');
    json.trim();
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, json);
    if (!err) {
      if (doc["type"] == "image") {
        // Yeni format: base64 JPEG görüntü
        veri.image_b64 = doc["data"].as<String>();
        Serial.printf("[CAM] Goruntu alindi: %d karakter base64\n",
                      veri.image_b64.length());
      } else if (doc.containsKey("bbch")) {
        // Geriye uyumlu: eski BBCH JSON formatı
        veri.bbch_sinif = doc["bbch"].as<String>();
        veri.bbch_guven = doc["guven"] | 0.0f;
      }
    }
  }
}

// ── Sensör Ölçüm ─────────────────────────────────────────────────
void sensorOlc() {
  veri.nem1_pct  = adcToNem(analogRead(SEN0193_1_PIN));
  veri.nem2_pct  = adcToNem(analogRead(SEN0193_2_PIN));
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t)) veri.hava_temp = t;
  if (!isnan(h)) veri.hava_nem  = h;
  veri.engel_on   = mesafeOlc(HCSR04_F_TRIG, HCSR04_F_ECHO);
  veri.engel_arka = mesafeOlc(HCSR04_B_TRIG, HCSR04_B_ECHO);
  while (gpsSerial.available()) gps.encode(gpsSerial.read());
  if (gps.location.isValid()) {
    veri.gps_lat   = gps.location.lat();
    veri.gps_lon   = gps.location.lng();
    veri.gps_valid = true;
  }
  Serial.printf("[SENSOR] Nem1:%.1f%% Nem2:%.1f%% Temp:%.1f Engel:%ldcm\n",
    veri.nem1_pct, veri.nem2_pct, veri.hava_temp, veri.engel_on);
}

// ── MQTT Yayın ───────────────────────────────────────────────────
void mqttYayinla() {
  if (!mqtt.connected()) return;
  JsonDocument doc;
  doc["timestamp"]     = millis();
  doc["gps_lat"]       = veri.gps_lat;
  doc["gps_lon"]       = veri.gps_lon;
  doc["gps_valid"]     = veri.gps_valid;
  doc["nem_1_pct"]     = veri.nem1_pct;
  doc["nem_2_pct"]     = veri.nem2_pct;
  doc["hava_temp_c"]   = veri.hava_temp;
  doc["hava_nem_pct"]  = veri.hava_nem;
  doc["engel_on_cm"]   = veri.engel_on;
  doc["engel_arka_cm"] = veri.engel_arka;
  doc["bbch_sinif"]    = veri.bbch_sinif;
  doc["bbch_guven"]    = veri.bbch_guven;
  doc["waypoint_id"]   = veri.waypoint_id;
  doc["rover_id"]      = MQTT_CLIENT;
  if (veri.image_b64.length() > 0) {
    doc["image"] = veri.image_b64;
  }
  // Büyük payload için dinamik String — char[512] yeterli değil
  String payload_str;
  serializeJson(doc, payload_str);
  mqtt.publish(MQTT_TOPIC, (const uint8_t*)payload_str.c_str(), payload_str.length());
  Serial.printf("[MQTT] Paket gonderildi (%d byte).\n", payload_str.length());
  veri.image_b64 = "";  // Belleği serbest bırak
}

// ── Bağlantı ─────────────────────────────────────────────────────
void wifiBaglan() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int i = 0;
  while (WiFi.status() != WL_CONNECTED && i < 20) {
    delay(500); i++;
  }
  if (WiFi.status() == WL_CONNECTED)
    Serial.printf("[WiFi] Bağlandı: %s\n", WiFi.localIP().toString().c_str());
}

void mqttBaglan() {
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  int i = 0;
  while (!mqtt.connected() && i < 5) {
    mqtt.connect(MQTT_CLIENT);
    delay(2000); i++;
  }
}

// ── Setup ────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("=== TRAK-AI ROVER BASLIYOR ===");

  // MQTT büyük payload için buffer büyüt (64KB — base64 görüntü)
  mqtt.setBufferSize(65536);

  pinMode(MOTOR_IN1, OUTPUT); pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_IN3, OUTPUT); pinMode(MOTOR_IN4, OUTPUT);
  ledcSetup(LEDC_ENA, 5000, 8);
  ledcSetup(LEDC_ENB, 5000, 8);
  ledcAttachPin(MOTOR_ENA, LEDC_ENA);
  ledcAttachPin(MOTOR_ENB, LEDC_ENB);
  motorDur();

  pinMode(HCSR04_F_TRIG, OUTPUT); pinMode(HCSR04_F_ECHO, INPUT);
  pinMode(HCSR04_B_TRIG, OUTPUT); pinMode(HCSR04_B_ECHO, INPUT);

  dht.begin();
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  camSerial.begin(115200, SERIAL_8N1, CAM_RX_PIN, CAM_TX_PIN);

  wifiBaglan();
  if (WiFi.status() == WL_CONNECTED) mqttBaglan();

  Serial.println("[SETUP] Hazır!");
}

// ── Loop ─────────────────────────────────────────────────────────
void loop() {
  if (WiFi.status() == WL_CONNECTED && !mqtt.connected()) mqttBaglan();
  mqtt.loop();

  while (gpsSerial.available()) gps.encode(gpsSerial.read());
  camVerisiOku();

  unsigned long now = millis();
  if (now - lastSensorTime >= SENSOR_INTERVAL_MS) {
    sensorOlc();
    lastSensorTime = now;
  }
  if (now - lastMqttTime >= MQTT_INTERVAL_MS) {
    mqttYayinla();
    lastMqttTime = now;
  }

  waypointNavigasyon();
  delay(100);
}