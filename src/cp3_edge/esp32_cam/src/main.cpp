/*
 * TRAK-AI ESP32-CAM — Edge CV Pipeline
 *
 * İki ana görev:
 *   1. JPEG yakala + base64 encode + ana ESP32'ye UART üzerinden yolla
 *      → Cloud / orchestrator detaylı işler (BBCH classifier model çağrı)
 *   2. Yerel basit sınıflandırma (placeholder — TFlite Micro entegrasyonu için iskelet)
 *      → ana ESP32'ye {"type":"classify", "sinif":..., "guven":...} de yollar
 *      → orchestrator'a hızlı bir ön-tahmin sağlar
 *
 * Mevcut durum: classify_image() placeholder. Gerçek TFlite model
 * eklenince burası gerçek inferans yapar (TFLite Micro + .tflite model).
 *
 * UART protokolü (115200 baud, UART0):
 *   CAPTURE\n      → image JSON + classify JSON cevabı
 *   CLASSIFY\n     → sadece classify JSON cevabı (image yok, hafif)
 *   PING\n         → heartbeat cevabı
 *
 * Cevap formatları:
 *   {"type":"image","fmt":"jpeg","w":W,"h":H,"bytes":N,"data":"<base64>"}
 *   {"type":"classify","sinif":"BBCH_60_69","guven":0.87}
 *   {"type":"pong","cam_ok":true,"uptime_ms":N}
 */
#include <Arduino.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include "mbedtls/base64.h"

// ─── AI Thinker ESP32-CAM Pin Tanımları ──────────────────────────────
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Periyodik capture aralığı (ana ESP32 zaten 30sn'de bir CAPTURE yolluyor,
// bu otomatik yayın yedek mekanizma)
unsigned long lastCaptureTime = 0;
const unsigned long CAPTURE_INTERVAL_MS = 30000;   // ana ESP32 ile uyumlu

// Kamera durumu (stub mod desteği)
bool g_camera_ok = false;

// ════════════════════════════════════════════════════════════════════
// Kamera initialize
// ════════════════════════════════════════════════════════════════════
bool kameraBaslat() {
  camera_config_t config;
  config.ledc_channel  = LEDC_CHANNEL_0;
  config.ledc_timer    = LEDC_TIMER_0;
  config.pin_d0        = Y2_GPIO_NUM;
  config.pin_d1        = Y3_GPIO_NUM;
  config.pin_d2        = Y4_GPIO_NUM;
  config.pin_d3        = Y5_GPIO_NUM;
  config.pin_d4        = Y6_GPIO_NUM;
  config.pin_d5        = Y7_GPIO_NUM;
  config.pin_d6        = Y8_GPIO_NUM;
  config.pin_d7        = Y9_GPIO_NUM;
  config.pin_xclk      = XCLK_GPIO_NUM;
  config.pin_pclk      = PCLK_GPIO_NUM;
  config.pin_vsync     = VSYNC_GPIO_NUM;
  config.pin_href      = HREF_GPIO_NUM;
  config.pin_sscb_sda  = SIOD_GPIO_NUM;
  config.pin_sscb_scl  = SIOC_GPIO_NUM;
  config.pin_pwdn      = PWDN_GPIO_NUM;
  config.pin_reset     = RESET_GPIO_NUM;
  config.xclk_freq_hz  = 20000000;
  config.pixel_format  = PIXFORMAT_JPEG;
  config.frame_size    = FRAMESIZE_QVGA;   // 320x240
  config.jpeg_quality  = 15;
  config.fb_count      = 1;
  config.grab_mode     = CAMERA_GRAB_WHEN_EMPTY;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAM] Init hata: 0x%x\n", err);
    return false;
  }
  Serial.println("[CAM] Kamera baslatildi. (QVGA, quality=15)");
  return true;
}

// ════════════════════════════════════════════════════════════════════
// Yerel CV sınıflandırma — TFlite Micro entegrasyonu için iskelet
//
// Şu an placeholder dummy classifier. Gerçek model entegrasyonu için
// TODO listesi:
//   1. TensorFlowLite_ESP32 kütüphanesi ekle (platformio.ini)
//   2. .tflite modelini PROGMEM array olarak ekle
//   3. tflite::MicroInterpreter ile inferans yap
//   4. Output → sinif + güven değeri
//
// Eğitim datası: BBCH evreleri foto + hastalık sınıfları
//   - Hugging Face PlantVillage dataset
//   - Türkiye sağlam veriseti için: Trakya bölgesi tarla foto'ları (manuel etiketleme)
//
// Hedef model: MobileNetV3 quantized (~500KB) veya EfficientNet-Lite
//   - Input: 96x96 veya 160x160 RGB
//   - Output: 10-20 sınıf (BBCH + 5 hastalık tipi)
//   - Inference: ~1-2 saniye (ESP32-S3 daha hızlı)
// ════════════════════════════════════════════════════════════════════
struct CVResult {
  String sinif;   // örn "BBCH_50_59" veya "Mildiyoe"
  float  guven;   // 0.0 - 1.0
  bool   valid;
};

CVResult classify_image(camera_fb_t* fb) {
  CVResult out{"BILINMIYOR", 0.0f, false};
  if (!fb || fb->len == 0) return out;

  // PLACEHOLDER: Gerçek inference yerine basit heuristik
  // JPEG boyutuna göre "karmaşıklık" tahmin et (saçma ama placeholder):
  //   küçük JPEG (~5KB)  → düz renk (toprak, gökyüzü) → BILINMIYOR
  //   orta JPEG (~10-15KB) → karışık (bitki) → BBCH_50_59 (tahmin)
  //   büyük JPEG (~20KB+) → çok karmaşık → muhtemel hastalık tutulmuş
  //
  // GERÇEK İMPLEMENTASYON BURAYA GELECEK:
  //   1. JPEG decode → RGB buffer (96x96)
  //   2. Normalize [0, 1] veya [-1, 1]
  //   3. tflite interpreter invoke
  //   4. Softmax output → en yüksek sınıf
  out.valid = true;
  if (fb->len < 7000) {
    out.sinif = "BILINMIYOR";   // düz/boş kare
    out.guven = 0.30f;
  } else if (fb->len < 13000) {
    out.sinif = "BBCH_50_59";   // muhtemel başaklanma
    out.guven = 0.65f;          // placeholder güven (gerçek model yüksek olmalı)
  } else {
    out.sinif = "BBCH_60_69";   // çiçek/olgunlaşma
    out.guven = 0.58f;
  }
  return out;
}

// ════════════════════════════════════════════════════════════════════
// JSON gönderim helper'ları
// ════════════════════════════════════════════════════════════════════
void goruntuyuGonder(camera_fb_t* fb) {
  size_t b64_len = 0;
  mbedtls_base64_encode(NULL, 0, &b64_len, fb->buf, fb->len);

  uint8_t* b64_buf = (uint8_t*)malloc(b64_len + 1);
  if (!b64_buf) {
    Serial.println("[CAM] malloc hata — goruntu gonderilemedi");
    return;
  }

  mbedtls_base64_encode(b64_buf, b64_len, &b64_len, fb->buf, fb->len);
  b64_buf[b64_len] = '\0';

  // JSON tek satır — ana ESP32 readStringUntil('\n') okuyor
  Serial.print("{\"type\":\"image\",\"fmt\":\"jpeg\",\"w\":320,\"h\":240,\"bytes\":");
  Serial.print((int)fb->len);
  Serial.print(",\"data\":\"");
  Serial.print((char*)b64_buf);
  Serial.println("\"}");

  Serial.printf("[CAM] Goruntu gonderildi: %d byte JPEG -> %d byte base64\n",
                (int)fb->len, (int)b64_len);
  free(b64_buf);
}

void cvSonucGonder(const CVResult& result) {
  if (!result.valid) return;
  JsonDocument doc;
  doc["type"]  = "classify";
  doc["sinif"] = result.sinif;
  doc["guven"] = result.guven;
  doc["src"]   = "edge_cam";       // ana ESP32 ve orchestrator filtre yapsın
  String out;
  serializeJson(doc, out);
  Serial.println(out);
  Serial.printf("[CAM] CV sonuc: %s @ %.0f%%\n",
                result.sinif.c_str(), result.guven * 100);
}

void pingCevap() {
  JsonDocument doc;
  doc["type"]      = "pong";
  doc["cam_ok"]    = g_camera_ok;
  doc["uptime_ms"] = millis();
  String out;
  serializeJson(doc, out);
  Serial.println(out);
}

// ════════════════════════════════════════════════════════════════════
// Komut işleme
// ════════════════════════════════════════════════════════════════════
void handleCommand(const String& cmd) {
  if (cmd == "CAPTURE") {
    if (!g_camera_ok) {
      Serial.println("{\"type\":\"image\",\"fmt\":\"none\",\"stub\":true,\"data\":\"\"}");
      Serial.println("[CAM] STUB: CAPTURE alindi, kamera yok");
      return;
    }
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("[CAM] CAPTURE hatasi: goruntu alinamadi");
      return;
    }
    // 1) JPEG'i ana ESP32'ye yolla (cloud detaylı işleme için)
    goruntuyuGonder(fb);
    // 2) Yerel CV sınıflandırma (hızlı ön-tahmin)
    CVResult cv = classify_image(fb);
    cvSonucGonder(cv);
    esp_camera_fb_return(fb);
  }
  else if (cmd == "CLASSIFY") {
    // Sadece sınıflandırma (image yok — bandwidth tasarrufu)
    if (!g_camera_ok) {
      Serial.println("{\"type\":\"classify\",\"sinif\":\"BILINMIYOR\",\"guven\":0,\"stub\":true}");
      return;
    }
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("[CAM] CLASSIFY hatasi: goruntu alinamadi");
      return;
    }
    CVResult cv = classify_image(fb);
    cvSonucGonder(cv);
    esp_camera_fb_return(fb);
  }
  else if (cmd == "PING") {
    pingCevap();
  }
  else if (cmd.length() > 0) {
    Serial.printf("[CAM] Bilinmeyen komut: '%s'\n", cmd.c_str());
  }
}

// ════════════════════════════════════════════════════════════════════
// setup() & loop()
// ════════════════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println("══════════════════════════════════════════════");
  Serial.println("  TRAK-AI ESP32-CAM Edge CV Pipeline");
  Serial.println("══════════════════════════════════════════════");
  g_camera_ok = kameraBaslat();
  if (!g_camera_ok) {
    Serial.println("[CAM] STUB MOD — kamera takili degil, demo modda devam");
    Serial.println("[CAM] CAPTURE komutu gelirse bos JSON donulecek");
  }
  Serial.println("[SETUP] Hazir!");
  Serial.println("[SETUP] Komutlar: CAPTURE (JPEG+CV), CLASSIFY (sadece CV), PING");
}

void loop() {
  // Ana rover'dan UART komut bekle
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    handleCommand(cmd);
  }

  // Periyodik otomatik capture (ana rover komut yollamasa bile)
  // Stub modda atlanır.
  if (g_camera_ok) {
    unsigned long now = millis();
    if (now - lastCaptureTime >= CAPTURE_INTERVAL_MS) {
      camera_fb_t* fb = esp_camera_fb_get();
      if (!fb) {
        Serial.println("[CAM] Periyodik capture hata: goruntu alinamadi");
        lastCaptureTime = now;
        return;
      }
      goruntuyuGonder(fb);
      CVResult cv = classify_image(fb);
      cvSonucGonder(cv);
      esp_camera_fb_return(fb);
      lastCaptureTime = now;
    }
  } else {
    // Stub heartbeat — her 60 sn'de bir
    static unsigned long lastStub = 0;
    if (millis() - lastStub > 60000) {
      Serial.println("[CAM] STUB heartbeat — kamera bekleniyor");
      lastStub = millis();
    }
  }

  delay(100);
}
