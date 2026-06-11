/*
 * ═══════════════════════════════════════════════════════════════════
 * TRAK-AI TARIM ROVER — ESP32 EDGE LAYER
 * ═══════════════════════════════════════════════════════════════════
 *
 * Donanım: ESP32 WROOM-32 + SEN0193 + DHT22 + HC-SR04 + NEO-6M + ESP32-CAM + L298N
 *
 * Yetenekler:
 *   • Boot anında IDLE — dashboard ACTIVATE komutu beklenir (güç tasarrufu)
 *   • OTA WiFi firmware update (USB gereksiz, port 3232)
 *   • Telnet remote serial monitor (port 23, USB gereksiz)
 *   • SPIFFS store-and-forward kuyrugu (offline veri kaybı yok, 1 MB FIFO)
 *   • MQTT pub/sub: trakaia/rover/data + trakaia/rover/cmd
 *   • Waypoint navigasyon: Haversine + bearing, 4 nokta state machine
 *   • ESP32-CAM JSON parse (15KB JPEG base64, 32KB RX buffer)
 *   • Tek sensör desteği — NEM2/HCSR04_B yoksa sentinel ile JSON dışı
 *   • Manuel motor kontrol (FORWARD/BACK/LEFT/RIGHT, 100-5000ms süre)
 *
 * Loop iş akışı:
 *   1. ArduinoOTA.handle()              (en başta, paket kaçırma)
 *   2. OTA aktifse minimal mode + return
 *   3. Telnet client kabul
 *   4. MQTT keepalive + reconnect
 *   5. GPS karakter parse
 *   6. Sensor okuma (30sn'de bir)
 *   7. MQTT publish veya SPIFFS kuyruğa (30sn'de bir)
 *   8. Waypoint navigasyon (ACTIVE modda)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoOTA.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <TinyGPSPlus.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>
#include "config.h"

// ════════════════════════════════════════════════════════════════════
// Global donanım nesneleri
// ════════════════════════════════════════════════════════════════════
WiFiClient     wifiClient;
PubSubClient   mqtt(wifiClient);
DHT            dht(DHT22_PIN, DHT22);
TinyGPSPlus    gps;
HardwareSerial gpsSerial(2);      // UART2 — GPS NEO-6M
HardwareSerial camSerial(1);      // UART1 — ESP32-CAM

// Telnet server — WiFi üzerinden remote Serial monitor
WiFiServer  telnetServer(23);
WiFiClient  telnetClient;

// ════════════════════════════════════════════════════════════════════
// Çalışma durumu
// ════════════════════════════════════════════════════════════════════
enum RoverMode     { MODE_IDLE, MODE_ACTIVE };
enum RoverNavState { NAV_DRIVING, NAV_STOPPED, NAV_DONE };

RoverMode      g_mode = MODE_IDLE;
RoverNavState  g_nav  = NAV_DRIVING;
int            g_current_wp     = 0;
unsigned long  g_manual_until_ms = 0;
unsigned long  g_stopped_at_ms   = 0;
unsigned long  g_last_sensor_ms  = 0;
unsigned long  g_last_mqtt_ms    = 0;
unsigned long  g_last_obstacle_ms = 0;
volatile bool  g_ota_in_progress = false;

// Sensor toplama veri yapısı
struct SensorData {
  float  nem1_pct    = 0;
  float  nem2_pct    = -1;        // sentinel: sensör yok
  float  hava_temp_c = 0;
  float  hava_nem    = 0;
  long   engel_on    = -1;        // sentinel: sensör yok
  long   engel_arka  = -1;        // sentinel: sensör yok
  double gps_lat     = 0;
  double gps_lon     = 0;
  bool   gps_valid   = false;
  String bbch_sinif  = "BILINMIYOR";
  float  bbch_guven  = 0;
  String image_b64;               // CAM'den gelen base64 JPEG (var ise)
};
SensorData veri;

// SPIFFS kuyruk
const char*  QUEUE_FILE      = "/data/queue.jsonl";
const size_t QUEUE_MAX_BYTES = 1024 * 1024;     // 1 MB
bool         g_spiffs_ready  = false;

inline const char* modeStr(RoverMode m) {
  return m == MODE_ACTIVE ? "ACTIVE" : "IDLE";
}

// ════════════════════════════════════════════════════════════════════
// Telnet helpers — Serial + WiFi'a aynı anda yaz
// USB kablo olmadan ESP32 loglarını uzaktan oku. WiFi bağlı iken port 23
// açıktır. PC'den: telnet <ESP32_IP> 23  (veya PuTTY → Connection: Telnet)
// ════════════════════════════════════════════════════════════════════
inline void telnetWrite(const char* s, size_t n) {
  if (telnetClient && telnetClient.connected()) {
    telnetClient.write((const uint8_t*)s, n);
  }
}

#define TPRINTF(...) do { \
  char _tbuf[256]; \
  int _n = snprintf(_tbuf, sizeof(_tbuf), __VA_ARGS__); \
  if (_n < 0) _n = 0; \
  if (_n > (int)sizeof(_tbuf) - 1) _n = sizeof(_tbuf) - 1; \
  Serial.print(_tbuf); telnetWrite(_tbuf, _n); \
} while(0)

#define TPRINTLN(s) do { \
  Serial.println(s); \
  if (telnetClient && telnetClient.connected()) { \
    telnetClient.print(s); telnetClient.print("\r\n"); \
  } \
} while(0)

void telnetBaslat() {
  telnetServer.begin();
  telnetServer.setNoDelay(true);
  Serial.printf("[TELNET] Hazir -> telnet %s 23\n",
                WiFi.localIP().toString().c_str());
}

void telnetLoop() {
  if (telnetServer.hasClient()) {
    if (telnetClient && telnetClient.connected()) {
      WiFiClient reject = telnetServer.available();
      reject.println("Baska client zaten bagli.");
      reject.stop();
    } else {
      telnetClient = telnetServer.available();
      telnetClient.setNoDelay(true);
      telnetClient.println();
      telnetClient.println("===================================================");
      telnetClient.println("  TRAK-AI Rover Remote Serial (Telnet)");
      telnetClient.printf ("  Client: %s\r\n", telnetClient.remoteIP().toString().c_str());
      telnetClient.println("  Quit: Ctrl+] then 'quit' (telnet) or close PuTTY");
      telnetClient.println("===================================================");
      Serial.printf("[TELNET] Client bagli: %s\n",
                    telnetClient.remoteIP().toString().c_str());
    }
  }
  if (telnetClient && !telnetClient.connected()) {
    telnetClient.stop();
    Serial.println("[TELNET] Client kapandi");
  }
}

// ════════════════════════════════════════════════════════════════════
// Matematik yardımcıları
// ════════════════════════════════════════════════════════════════════

// SEN0193 ADC raw → nem yüzdesi (lineer interpolasyon, [0..100] clamp)
// Otomatik yön algılama: SOIL_DRY_RAW > SOIL_WET_RAW ise normal davranış,
// SOIL_DRY_RAW < SOIL_WET_RAW ise ters çıkışlı sensör (klon variant) için
// formül otomatik tersine çevrilir.
float adcToNem(int raw) {
  if (SOIL_DRY_RAW > SOIL_WET_RAW) {
    // Normal: kuru = yüksek raw, ıslak = düşük raw
    if (raw >= SOIL_DRY_RAW) return 0.0f;
    if (raw <= SOIL_WET_RAW) return 100.0f;
    return 100.0f * (SOIL_DRY_RAW - raw)
                  / (float)(SOIL_DRY_RAW - SOIL_WET_RAW);
  } else {
    // Ters: kuru = düşük raw, ıslak = yüksek raw (sensör klonları)
    if (raw <= SOIL_DRY_RAW) return 0.0f;
    if (raw >= SOIL_WET_RAW) return 100.0f;
    return 100.0f * (raw - SOIL_DRY_RAW)
                  / (float)(SOIL_WET_RAW - SOIL_DRY_RAW);
  }
}

// HC-SR04 mesafe ölçümü (cm), echo timeout → 999
long mesafeOlc(int trig, int echo) {
  digitalWrite(trig, LOW);  delayMicroseconds(2);
  digitalWrite(trig, HIGH); delayMicroseconds(10);
  digitalWrite(trig, LOW);
  long duration = pulseIn(echo, HIGH, 30000UL);    // 30ms timeout ≈ 5m
  if (duration == 0) return 999;
  return (long)(duration * 0.0343 / 2.0);
}

// Haversine — iki GPS koordinatı arası mesafe (metre)
double haversine_m(double lat1, double lon1, double lat2, double lon2) {
  const double R = 6371000.0;
  double dlat = (lat2 - lat1) * PI / 180.0;
  double dlon = (lon2 - lon1) * PI / 180.0;
  double a = sin(dlat/2) * sin(dlat/2) +
             cos(lat1*PI/180.0) * cos(lat2*PI/180.0) *
             sin(dlon/2) * sin(dlon/2);
  return R * 2.0 * atan2(sqrt(a), sqrt(1 - a));
}

// Bearing — başlangıç noktasından hedefe yön (derece, 0=K, 90=D, 180=G, 270=B)
double bearing_deg(double lat1, double lon1, double lat2, double lon2) {
  double dlon = (lon2 - lon1) * PI / 180.0;
  double y = sin(dlon) * cos(lat2 * PI / 180.0);
  double x = cos(lat1*PI/180.0) * sin(lat2*PI/180.0) -
             sin(lat1*PI/180.0) * cos(lat2*PI/180.0) * cos(dlon);
  double brng = atan2(y, x) * 180.0 / PI;
  return fmod(brng + 360.0, 360.0);
}

// ════════════════════════════════════════════════════════════════════
// L298N motor sürücü
// ════════════════════════════════════════════════════════════════════
void motorDur() {
  ledcWrite(LEDC_ENA, 0);
  ledcWrite(LEDC_ENB, 0);
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, LOW);
  digitalWrite(MOTOR_IN4, LOW);
}

void motorIleri(int hiz = MOTOR_SPEED_NORMAL) {
  digitalWrite(MOTOR_IN1, HIGH); digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, HIGH); digitalWrite(MOTOR_IN4, LOW);
  ledcWrite(LEDC_ENA, hiz);
  ledcWrite(LEDC_ENB, hiz);
}

void motorGeri(int hiz = MOTOR_SPEED_NORMAL) {
  digitalWrite(MOTOR_IN1, LOW);  digitalWrite(MOTOR_IN2, HIGH);
  digitalWrite(MOTOR_IN3, LOW);  digitalWrite(MOTOR_IN4, HIGH);
  ledcWrite(LEDC_ENA, hiz);
  ledcWrite(LEDC_ENB, hiz);
}

void motorSolaDon(int hiz = MOTOR_SPEED_SLOW) {
  digitalWrite(MOTOR_IN1, LOW);  digitalWrite(MOTOR_IN2, HIGH);
  digitalWrite(MOTOR_IN3, HIGH); digitalWrite(MOTOR_IN4, LOW);
  ledcWrite(LEDC_ENA, hiz);
  ledcWrite(LEDC_ENB, hiz);
}

void motorSagaDon(int hiz = MOTOR_SPEED_SLOW) {
  digitalWrite(MOTOR_IN1, HIGH); digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, LOW);  digitalWrite(MOTOR_IN4, HIGH);
  ledcWrite(LEDC_ENA, hiz);
  ledcWrite(LEDC_ENB, hiz);
}

// ════════════════════════════════════════════════════════════════════
// SPIFFS Store-and-Forward Kuyrugu
// MQTT offline ise sensor verisi /data/queue.jsonl'a satır eklenir.
// Bağlantı gelince kuyrukDrain() satır satır publish eder, hepsi başarılı
// olunca dosya silinir. Partial drain destekli (kalanlar dosyaya geri yazılır).
// 1 MB üst sınır — aşılırsa FIFO trim (en eski yarı atılır).
// ════════════════════════════════════════════════════════════════════
bool kuyrukHazirla() {
  if (g_spiffs_ready) return true;
  if (!SPIFFS.begin(true)) {
    Serial.println("[QUEUE] SPIFFS mount basarisiz!");
    return false;
  }
  g_spiffs_ready = true;
  size_t total = SPIFFS.totalBytes();
  size_t used  = SPIFFS.usedBytes();
  Serial.printf("[QUEUE] SPIFFS hazir - Total:%uKB Used:%uKB Free:%uKB\n",
                (unsigned)(total/1024), (unsigned)(used/1024),
                (unsigned)((total - used)/1024));
  if (SPIFFS.exists(QUEUE_FILE)) {
    File f = SPIFFS.open(QUEUE_FILE, "r");
    if (f) {
      Serial.printf("[QUEUE] Bekleyen kayit: %u byte (bagliyken gonderilecek)\n",
                    (unsigned)f.size());
      f.close();
    }
  }
  return true;
}

void kuyrukFifoTrim() {
  if (!g_spiffs_ready) return;
  File f = SPIFFS.open(QUEUE_FILE, "r");
  if (!f) return;
  size_t sz = f.size();
  if (sz <= QUEUE_MAX_BYTES) { f.close(); return; }

  size_t skip = sz / 2;
  f.seek(skip);
  f.readStringUntil('\n');   // ilk newline'a hizala

  String remaining;
  remaining.reserve(sz - skip);
  while (f.available()) remaining += (char)f.read();
  f.close();

  File g = SPIFFS.open(QUEUE_FILE, "w");
  if (!g) return;
  g.print(remaining);
  g.close();
  Serial.printf("[QUEUE] FIFO trim: %u -> %u byte\n",
                (unsigned)sz, (unsigned)remaining.length());
}

bool kuyrukAppend(const String& jsonLine) {
  if (!kuyrukHazirla()) return false;
  if (SPIFFS.exists(QUEUE_FILE)) {
    File f = SPIFFS.open(QUEUE_FILE, "r");
    if (f) {
      size_t sz = f.size();
      f.close();
      if (sz + jsonLine.length() + 2 > QUEUE_MAX_BYTES) kuyrukFifoTrim();
    }
  }
  File f = SPIFFS.open(QUEUE_FILE, FILE_APPEND);
  if (!f) return false;
  size_t n = f.print(jsonLine);
  f.print('\n');
  f.close();
  return n > 0;
}

bool kuyrukDrain() {
  if (!g_spiffs_ready || !SPIFFS.exists(QUEUE_FILE)) return true;
  if (!mqtt.connected()) return false;

  File f = SPIFFS.open(QUEUE_FILE, "r");
  if (!f) return false;

  int   total = 0, sent = 0;
  bool  allSent = true;
  String remaining;

  while (f.available()) {
    String line = f.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) continue;
    total++;
    if (!mqtt.connected()) {
      allSent = false;
      remaining += line; remaining += '\n';
      continue;
    }
    bool ok = mqtt.publish(MQTT_TOPIC,
                           (const uint8_t*)line.c_str(), line.length());
    if (ok) {
      sent++;
      mqtt.loop();
      delay(50);
    } else {
      allSent = false;
      remaining += line; remaining += '\n';
    }
  }
  f.close();

  if (allSent && sent == total) {
    SPIFFS.remove(QUEUE_FILE);
    if (sent > 0) TPRINTF("[QUEUE] %d kayit gonderildi, kuyruk temizlendi\n", sent);
    return true;
  }
  File g = SPIFFS.open(QUEUE_FILE, "w");
  if (g) { g.print(remaining); g.close(); }
  TPRINTF("[QUEUE] %d/%d gonderildi, kalan %u byte dosyada\n",
          sent, total, (unsigned)remaining.length());
  return false;
}

// ════════════════════════════════════════════════════════════════════
// ESP32-CAM UART okuma — JSON parse (ArduinoJson v7)
// ════════════════════════════════════════════════════════════════════
void camCapture() {
  // Ana ESP32 → CAM: "CAPTURE\n" → CAM JPEG yakalar, base64 JSON yollar
  if (camSerial) camSerial.println("CAPTURE");
}

void camVerisiOku() {
  // CAM aynı cycle'da hem image hem classify JSON yollayabilir → tüm satırları drain et
  int linesProcessed = 0;
  while (camSerial.available() && linesProcessed < 5) {
    String json = camSerial.readStringUntil('\n');
    json.trim();
    if (json.length() == 0) continue;
    linesProcessed++;
    Serial.printf("[CAM] HAM JSON gelen: %d karakter\n", json.length());

    // ArduinoJson v7: JsonDocument otomatik allocator, 32KB+ JSON için OK
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, json);
    if (err) {
      Serial.printf("[CAM] PARSE HATASI: %s (ilk 80c: %s)\n",
                    err.c_str(), json.substring(0, 80).c_str());
      continue;
    }
    const char* type = doc["type"] | "";
    if (strcmp(type, "image") == 0) {
      veri.image_b64 = doc["data"].as<String>();
      int bytes = doc["bytes"] | 0;
      Serial.printf("[CAM] Goruntu alindi: %d karakter base64 (JPEG=%d byte)\n",
                    veri.image_b64.length(), bytes);
    } else if (strcmp(type, "classify") == 0) {
      // CAM yerel CV sınıflandırma sonucu — hızlı ön-tahmin
      veri.bbch_sinif = doc["sinif"].as<String>();
      veri.bbch_guven = doc["guven"] | 0.0f;
      const char* src = doc["src"] | "?";
      Serial.printf("[CAM] CV sinif: %s @ %.0f%% (src=%s)\n",
                    veri.bbch_sinif.c_str(), veri.bbch_guven * 100, src);
    } else if (strcmp(type, "pong") == 0) {
      Serial.println("[CAM] PONG (heartbeat OK)");
    }
  }
}

// ════════════════════════════════════════════════════════════════════
// Sensor ölçüm
// ════════════════════════════════════════════════════════════════════
void sensorOlc() {
  // ─── SEN0193 toprak nemi (tek sensör) ───
  int soil1_raw = analogRead(SEN0193_1_PIN);
  veri.nem1_pct = adcToNem(soil1_raw);
  TPRINTF("[SOIL] raw=%d pct=%.1f%%\n", soil1_raw, veri.nem1_pct);
  veri.nem2_pct = NEM2_SENSOR_PRESENT
                ? adcToNem(analogRead(SEN0193_2_PIN))
                : -1.0f;

  // ─── DHT22 hava sıcaklık + nem ───
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t)) veri.hava_temp_c = t;
  if (!isnan(h)) veri.hava_nem    = h;

  // ─── HC-SR04 mesafe (flag'lere göre) ───
  veri.engel_on   = HCSR04_F_PRESENT
                  ? mesafeOlc(HCSR04_F_TRIG, HCSR04_F_ECHO) : -1;
  veri.engel_arka = HCSR04_B_PRESENT
                  ? mesafeOlc(HCSR04_B_TRIG, HCSR04_B_ECHO) : -1;

  // ─── GPS (TinyGPS++ son geçerli okuma) ───
  if (gps.location.isValid()) {
    veri.gps_lat   = gps.location.lat();
    veri.gps_lon   = gps.location.lng();
    veri.gps_valid = true;
  } else {
    veri.gps_valid = false;
  }
  TPRINTF("[GPS] Sat:%u Chars:%lu Sentences:%lu Failed:%lu Fix:%s\n",
          gps.satellites.isValid() ? gps.satellites.value() : 0,
          gps.charsProcessed(), gps.sentencesWithFix(),
          gps.failedChecksum(),
          gps.location.isValid() ? "VAR" : "yok");

  // ─── Kamera CAPTURE komutu + cevap parse ───
  camCapture();
  delay(300);            // CAM JPEG hazırlama süresi
  camVerisiOku();

  // ─── Özet log (Serial + Telnet) ───
  auto engelStr = [](long cm) -> String {
    if (cm < 0)    return String("yok");
    if (cm == 999) return String("999cm(echo yok)");
    return String(cm) + "cm";
  };
  if (veri.nem2_pct >= 0) {
    TPRINTF("[SENSOR] Nem1:%.1f%% Nem2:%.1f%% Temp:%.1f HavaNem:%.0f%% EngelOn:%s EngelArka:%s [%s]\n",
            veri.nem1_pct, veri.nem2_pct, veri.hava_temp_c, veri.hava_nem,
            engelStr(veri.engel_on).c_str(),
            engelStr(veri.engel_arka).c_str(),
            modeStr(g_mode));
  } else {
    TPRINTF("[SENSOR] Nem:%.1f%% Temp:%.1f%% HavaNem:%.0f%% EngelOn:%s EngelArka:%s [%s]\n",
            veri.nem1_pct, veri.hava_temp_c, veri.hava_nem,
            engelStr(veri.engel_on).c_str(),
            engelStr(veri.engel_arka).c_str(),
            modeStr(g_mode));
  }
}

// ════════════════════════════════════════════════════════════════════
// MQTT publish (online → direkt, offline → SPIFFS kuyruk)
// ════════════════════════════════════════════════════════════════════
void mqttYayinla() {
  JsonDocument doc;
  doc["timestamp"]      = millis();
  doc["rover_id"]       = MQTT_CLIENT;
  doc["saha_id"]        = SAHA_ID;
  doc["tarla_id"]       = TARLA_ID;        // dashboard "Tarla ID" alanı + DB FK
  doc["durum"]          = modeStr(g_mode);

  doc["gps_lat"]        = veri.gps_lat;
  doc["gps_lon"]        = veri.gps_lon;
  doc["gps_valid"]      = veri.gps_valid;

  doc["nem_1_pct"]      = veri.nem1_pct;
  if (veri.nem2_pct >= 0) doc["nem_2_pct"] = veri.nem2_pct;

  doc["hava_temp_c"]    = veri.hava_temp_c;
  doc["hava_nem_pct"]   = veri.hava_nem;

  if (veri.engel_on   >= 0) doc["engel_on_cm"]   = veri.engel_on;
  if (veri.engel_arka >= 0) doc["engel_arka_cm"] = veri.engel_arka;

  doc["bbch_sinif"]     = veri.bbch_sinif;
  doc["bbch_guven"]     = veri.bbch_guven;
  doc["waypoint_id"]    = g_current_wp;
  if (g_current_wp >= 0 && g_current_wp < WAYPOINT_COUNT) {
    doc["waypoint_label"] = WAYPOINTS[g_current_wp].label;
  }
  if (veri.image_b64.length() > 0) doc["image"] = veri.image_b64;

  String payload;
  serializeJson(doc, payload);

  if (mqtt.connected()) {
    kuyrukDrain();   // offline kayitlari önce gönder
    bool ok = mqtt.publish(MQTT_TOPIC,
                           (const uint8_t*)payload.c_str(), payload.length());
    if (ok) {
      TPRINTF("[MQTT] Paket gonderildi (%d byte)\n", payload.length());
    } else {
      Serial.println("[MQTT] Publish basarisiz -> kuyruga");
      kuyrukAppend(payload);
    }
  } else {
    if (kuyrukAppend(payload)) {
      TPRINTF("[MQTT] Offline -> kuyruga (%d byte)\n", payload.length());
    }
  }
  veri.image_b64 = "";   // RAM serbest
}

// ════════════════════════════════════════════════════════════════════
// MQTT komut alıcı (dashboard → rover)
//   ACTIVATE / SLEEP — sistem aktivite kontrolü (her zaman geçerli)
//   STOP             — motoru durdur, 5sn manuel block
//   AUTO             — otonom nav devam (sadece ACTIVE moddayken)
//   FORWARD/BACK/LEFT/RIGHT — manuel sürüş, duration_ms süre sonra otomatik dur
//                            (mod IDLE'da bile çalışır, kullanıcı kontrolünde)
// ════════════════════════════════════════════════════════════════════
void mqttKomutAl(char* topic, byte* payload, unsigned int length) {
  char buf[128];
  unsigned int n = length < sizeof(buf) - 1 ? length : sizeof(buf) - 1;
  memcpy(buf, payload, n);
  buf[n] = '\0';
  TPRINTF("[CMD] %s <- %s\n", topic, buf);

  JsonDocument doc;
  if (deserializeJson(doc, buf)) {
    Serial.println("[CMD] JSON parse hatasi");
    return;
  }
  const char* cmd = doc["cmd"] | "";
  int duration = doc["duration_ms"] | 1000;
  if (duration < 100)  duration = 100;
  if (duration > 5000) duration = 5000;

  if (strcmp(cmd, "ACTIVATE") == 0) {
    g_mode = MODE_ACTIVE;
    TPRINTLN("[CMD] ACTIVATE - sistem ACTIVE moda gecti");
    return;
  }
  if (strcmp(cmd, "SLEEP") == 0) {
    g_mode = MODE_IDLE;
    motorDur();
    TPRINTLN("[CMD] SLEEP - sistem IDLE moda gecti, motor durdu");
    return;
  }
  if (strcmp(cmd, "STOP") == 0) {
    motorDur();
    g_manual_until_ms = millis() + 5000;
    TPRINTLN("[CMD] STOP - 5sn manuel block");
    return;
  }
  if (strcmp(cmd, "AUTO") == 0) {
    if (g_mode != MODE_ACTIVE) {
      TPRINTLN("[CMD] AUTO REDDEDILDI - once ACTIVATE gerekli");
      return;
    }
    g_manual_until_ms = 0;
    TPRINTLN("[CMD] AUTO - otonom nav devam");
    return;
  }

  // Manuel sürüş — IDLE modda da çalışır (kullanıcı yetkili)
  if      (strcmp(cmd, "FORWARD") == 0) { motorIleri();   g_manual_until_ms = millis() + duration + 2000; }
  else if (strcmp(cmd, "BACK")    == 0) { motorGeri();    g_manual_until_ms = millis() + duration + 2000; }
  else if (strcmp(cmd, "LEFT")    == 0) { motorSolaDon(); g_manual_until_ms = millis() + duration + 2000; }
  else if (strcmp(cmd, "RIGHT")   == 0) { motorSagaDon();g_manual_until_ms = millis() + duration + 2000; }
  else { TPRINTF("[CMD] Bilinmeyen komut: '%s'\n", cmd); return; }

  TPRINTF("[CMD] %s %dms -> otomatik dur\n", cmd, duration);
  delay(duration);
  motorDur();
}

// ════════════════════════════════════════════════════════════════════
// WiFi & MQTT bağlantı
// ════════════════════════════════════════════════════════════════════
void wifiBaglan() {
  Serial.printf("[WiFi] Baglaniyor: %s\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int i = 0;
  while (WiFi.status() != WL_CONNECTED && i < 20) {
    delay(500);
    Serial.print(".");
    i++;
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("[WiFi] Baglandi!");
    Serial.printf("[WiFi] IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("[WiFi] Baglanti basarisiz - offline modda devam");
  }
}

void mqttBaglan() {
  if (WiFi.status() != WL_CONNECTED) return;
  Serial.printf("[MQTT] Broker: %s\n", MQTT_HOST);
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(mqttKomutAl);
  int i = 0;
  while (!mqtt.connected() && i < 5) {
    if (mqtt.connect(MQTT_CLIENT)) {
      Serial.println("[MQTT] Baglandi!");
      mqtt.subscribe(MQTT_TOPIC_CMD);
      Serial.printf("[MQTT] Komut topic'ine abone: %s\n", MQTT_TOPIC_CMD);
      return;
    }
    delay(2000);
    i++;
  }
  if (!mqtt.connected()) {
    Serial.println("[MQTT] Baglanti basarisiz - offline modda devam");
  }
}

// ════════════════════════════════════════════════════════════════════
// OTA — WiFi üzerinden firmware update
// ════════════════════════════════════════════════════════════════════
void otaBaslat() {
  ArduinoOTA.setHostname(OTA_HOSTNAME);
  ArduinoOTA.setPassword(OTA_PASSWORD);
  ArduinoOTA.onStart([]() {
    g_ota_in_progress = true;
    motorDur();              // güvenlik: motor durdur
    mqtt.disconnect();       // WiFi bandwidth OTA'ya
    Serial.println("[OTA] Update basliyor - minimal mode");
  });
  ArduinoOTA.onEnd([]() {
    g_ota_in_progress = false;
    Serial.println("\n[OTA] Tamamlandi, restart...");
  });
  ArduinoOTA.onProgress([](unsigned int p, unsigned int t) {
    Serial.printf("[OTA] %u%%\r", (p / (t / 100)));
  });
  ArduinoOTA.onError([](ota_error_t error) {
    g_ota_in_progress = false;   // hata sonrası recovery
    Serial.printf("[OTA] Hata kodu: %u\n", error);
  });
  ArduinoOTA.begin();
  Serial.printf("[OTA] Hazir -> IP=%s hostname=%s.local sifre=%s\n",
                WiFi.localIP().toString().c_str(),
                OTA_HOSTNAME, OTA_PASSWORD);
}

// ════════════════════════════════════════════════════════════════════
// Waypoint Navigasyon (state machine: DRIVING → STOPPED → DONE)
// ════════════════════════════════════════════════════════════════════
void waypointNavigasyon() {
  // ─── Mod kontrolü — IDLE'da otonom yok ───
  if (g_mode != MODE_ACTIVE) {
    static unsigned long lastIdleLog = 0;
    if (millis() - lastIdleLog > 30000) {
      Serial.println("[NAV] IDLE - dashboard'dan ACTIVATE komutu bekleniyor");
      lastIdleLog = millis();
    }
    return;
  }
  // ─── Manuel override aktif mi? ───
  if (g_manual_until_ms != 0 && millis() < g_manual_until_ms) return;

  // ─── DONE — tüm waypointler tamamlandı ───
  if (g_nav == NAV_DONE) {
    motorDur();
    static bool doneLogged = false;
    if (!doneLogged) {
      TPRINTLN("[NAV] Tum waypointler tamamlandi");
      doneLogged = true;
      g_mode = MODE_IDLE;     // tamamlanınca uykuya
    }
    return;
  }

  // ─── STOPPED — 5sn bekle, ölçüm + yayın, sonraki WP ───
  if (g_nav == NAV_STOPPED) {
    if (millis() - g_stopped_at_ms < STOP_DURATION_MS) return;
    TPRINTF("[NAV] WP%d (%s) olcum bitti -> sonraki WP\n",
            g_current_wp, WAYPOINTS[g_current_wp].label);
    sensorOlc();
    mqttYayinla();
    g_current_wp++;
    if (g_current_wp >= WAYPOINT_COUNT) {
      g_nav = NAV_DONE;
    } else {
      g_nav = NAV_DRIVING;
      TPRINTF("[NAV] Sonraki hedef: WP%d (%s)\n",
              g_current_wp, WAYPOINTS[g_current_wp].label);
    }
    return;
  }

  // ─── DRIVING — hedefe doğru sür ───

  // Engel kontrolü (sadece sensor takiliysa)
  if (veri.engel_on >= 0 && veri.engel_on < ENGEL_ESIK_CM &&
      (millis() - g_last_obstacle_ms) > 2000) {
    TPRINTF("[NAV] Engel %ldcm - 2sn dur + 500ms geri\n", veri.engel_on);
    motorDur();
    delay(2000);
    motorGeri(MOTOR_SPEED_SLOW);
    delay(500);
    motorDur();
    g_last_obstacle_ms = millis();
    return;
  }

  // GPS yoksa dur ve bekle
  if (!veri.gps_valid) {
    motorDur();
    static unsigned long lastNogpsLog = 0;
    if (millis() - lastNogpsLog > 10000) {
      Serial.println("[NAV] GPS fix yok - bekleniyor");
      lastNogpsLog = millis();
    }
    return;
  }

  const Waypoint& wp = WAYPOINTS[g_current_wp];
  double dist = haversine_m(veri.gps_lat, veri.gps_lon, wp.lat, wp.lon);
  double brng = bearing_deg(veri.gps_lat, veri.gps_lon, wp.lat, wp.lon);

  // Periyodik durum log'u (her 5sn)
  static unsigned long lastNavLog = 0;
  if (millis() - lastNavLog > 5000) {
    TPRINTF("[NAV] WP%d (%s) mesafe=%.1fm bearing=%.0f%c\n",
            g_current_wp, wp.label, dist, brng, '\xB0');
    lastNavLog = millis();
  }

  // Ulaştık mı?
  if (dist <= WAYPOINT_RADIUS_M) {
    TPRINTF("[NAV] WP%d ulasildi (%.1fm) - STOPPED %lu ms\n",
            g_current_wp, dist, STOP_DURATION_MS);
    motorDur();
    g_nav = NAV_STOPPED;
    g_stopped_at_ms = millis();
    return;
  }

  // Yön sürüş — 4 yön mantığı (kullanıcı algoritması)
  //   0-45° veya 315-360° → ileri
  //   135-225°            → geri
  //   45-135°             → sağ dön
  //   225-315°            → sol dön
  if      (brng < 45 || brng >= 315)   motorIleri(DRIVE_SPEED);
  else if (brng >= 135 && brng < 225)  motorGeri(DRIVE_SPEED);
  else if (brng >= 45  && brng < 135)  motorSagaDon();
  else                                 motorSolaDon();
}

// ════════════════════════════════════════════════════════════════════
// setup() — donanım init
// ════════════════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println("══════════════════════════════════════════════");
  Serial.println("  TRAK-AI Tarım Rover (ESP32 Edge Layer)");
  Serial.printf ("  Saha=%s Client=%s\n", SAHA_ID, MQTT_CLIENT);
  Serial.println("══════════════════════════════════════════════");
  Serial.println("[BOOT] Mode: IDLE (dashboard ACTIVATE bekleniyor)");

  // 1) SPIFFS — store-and-forward kuyrugu
  kuyrukHazirla();

  // 2) MQTT buffer büyüt (kamera JPEG payload için)
  mqtt.setBufferSize(65535);

  // 3) L298N motor pinleri + PWM (LEDC)
  pinMode(MOTOR_IN1, OUTPUT); pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_IN3, OUTPUT); pinMode(MOTOR_IN4, OUTPUT);
  ledcSetup(LEDC_ENA, 5000, 8);   // 5kHz, 8-bit
  ledcSetup(LEDC_ENB, 5000, 8);
  ledcAttachPin(MOTOR_ENA, LEDC_ENA);
  ledcAttachPin(MOTOR_ENB, LEDC_ENB);
  motorDur();
  Serial.printf("[SETUP] L298N hazir: IN1=%d IN2=%d IN3=%d IN4=%d ENA=%d ENB=%d\n",
                MOTOR_IN1, MOTOR_IN2, MOTOR_IN3, MOTOR_IN4, MOTOR_ENA, MOTOR_ENB);

  // 4) HC-SR04 (takılı olanlar)
  if (HCSR04_F_PRESENT) {
    pinMode(HCSR04_F_TRIG, OUTPUT); pinMode(HCSR04_F_ECHO, INPUT);
    Serial.printf("[SETUP] HC-SR04 on: TRIG=%d ECHO=%d\n",
                  HCSR04_F_TRIG, HCSR04_F_ECHO);
  }
  if (HCSR04_B_PRESENT) {
    pinMode(HCSR04_B_TRIG, OUTPUT); pinMode(HCSR04_B_ECHO, INPUT);
  }

  // 5) DHT22
  dht.begin();
  Serial.printf("[SETUP] DHT22 hazir: GPIO %d\n", DHT22_PIN);

  // 6) ADC (toprak nemi tam 0-3.3V range için 11dB attenuation)
  analogSetPinAttenuation(SEN0193_1_PIN, ADC_11db);

  // 7) UART2 — GPS NEO-6M
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  Serial.printf("[SETUP] GPS UART2: RX=GPIO%d TX=GPIO%d @ %d baud\n",
                GPS_RX_PIN, GPS_TX_PIN, GPS_BAUD);

  // 8) UART1 — ESP32-CAM (büyük RX buffer + uzun timeout)
  camSerial.setRxBufferSize(16384);   // 15KB JPEG için
  camSerial.begin(CAM_BAUD, SERIAL_8N1, CAM_RX_PIN, CAM_TX_PIN);
  camSerial.setTimeout(3000);         // readStringUntil için 3sn
  Serial.printf("[SETUP] CAM UART1: RX=GPIO%d TX=GPIO%d @ %d baud (16KB RX buf)\n",
                CAM_RX_PIN, CAM_TX_PIN, CAM_BAUD);

  // 9) WiFi + MQTT + OTA + Telnet
  wifiBaglan();
  if (WiFi.status() == WL_CONNECTED) {
    mqttBaglan();
    otaBaslat();
    telnetBaslat();
  } else {
    Serial.println("[SETUP] WiFi yok - offline mode, telemetri SPIFFS kuyruguna yazilacak");
  }

  // 10) İlk waypoint hedefi
  g_nav = NAV_DRIVING;
  g_current_wp = 0;
  Serial.printf("[NAV] Ilk hedef: WP%d (%s)\n",
                g_current_wp, WAYPOINTS[g_current_wp].label);

  Serial.println("══════════════════════════════════════════════");
  Serial.println("[SETUP] HAZIR -> dashboard'dan 'BASLAT' (ACTIVATE) gonderin");
  Serial.println("══════════════════════════════════════════════");
}

// ════════════════════════════════════════════════════════════════════
// loop() — ana iş döngüsü
// ════════════════════════════════════════════════════════════════════
void loop() {
  // 1. OTA handle — en başta, paket kaçırmamak için
  ArduinoOTA.handle();

  // 2. OTA aktif iken minimal mode
  if (g_ota_in_progress) { delay(1); return; }

  // 3. Telnet client kabul
  telnetLoop();

  // 4. WiFi + MQTT bağlantı kontrolü
  if (WiFi.status() == WL_CONNECTED && !mqtt.connected()) {
    static unsigned long lastReconnect = 0;
    if (millis() - lastReconnect > 5000) {
      mqttBaglan();
      lastReconnect = millis();
    }
  }
  mqtt.loop();   // PubSubClient keepalive + callback

  // 5. GPS karakterlerini sürekli parse et (TinyGPS++ buffer)
  while (gpsSerial.available()) gps.encode(gpsSerial.read());

  // 6. Sensor ölçüm (30sn'de bir)
  unsigned long now = millis();
  if (now - g_last_sensor_ms >= SENSOR_INTERVAL_MS) {
    sensorOlc();
    g_last_sensor_ms = now;
  }

  // 7. MQTT publish (30sn'de bir; offline → SPIFFS kuyruga)
  if (now - g_last_mqtt_ms >= MQTT_INTERVAL_MS) {
    mqttYayinla();
    g_last_mqtt_ms = now;
  }

  // 8. Waypoint navigasyon (mod ACTIVE ise)
  waypointNavigasyon();

  // 9. CPU nefes — ACTIVE'de hızlı, IDLE'da yavaş (modem-sleep boost)
  delay(g_mode == MODE_ACTIVE ? 100 : 500);
}
