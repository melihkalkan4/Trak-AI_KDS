#include <Arduino.h>
#include <ArduinoJson.h>
#include "esp_camera.h"

// AI Thinker ESP32-CAM Pin Tanımları
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

// BBCH Sınıf Etiketleri
const char* BBCH_SINIFLAR[] = {
  "BBCH_00_10",
  "BBCH_10_19",
  "BBCH_20_29",
  "BBCH_30_39",
  "BBCH_51_59",
  "BBCH_60_69",
  "BBCH_71_79",
  "BBCH_81_89",
  "SAGLIKLI",
  "HASTALIKLI",
};

unsigned long lastInferenceTime = 0;
const unsigned long INFERENCE_INTERVAL_MS = 5000;

struct InferenceResult {
  int   sinifIndex;
  float guvenSkoru;
};

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
  config.frame_size    = FRAMESIZE_QVGA;
  config.jpeg_quality  = 12;
  config.fb_count      = 1;
  config.grab_mode     = CAMERA_GRAB_WHEN_EMPTY;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAM] Hata: 0x%x\n", err);
    return false;
  }
  Serial.println("[CAM] Kamera başlatıldı.");
  return true;
}

// Mock inference - YOLOv8 TFLite model gelince burası güncellenecek
InferenceResult mockInference(camera_fb_t* fb) {
  uint32_t toplam = 0;
  int ornekSayisi = min((int)fb->len, 1000);
  for (int i = 0; i < ornekSayisi; i++) toplam += fb->buf[i];
  float ort = (float)toplam / ornekSayisi;

  InferenceResult sonuc;
  if (ort > 180)      { sonuc.sinifIndex = 8; sonuc.guvenSkoru = 0.82f; }
  else if (ort > 120) { sonuc.sinifIndex = 5; sonuc.guvenSkoru = 0.76f; }
  else                { sonuc.sinifIndex = 9; sonuc.guvenSkoru = 0.71f; }
  return sonuc;
}

void sonucGonder(InferenceResult& sonuc) {
  StaticJsonDocument<128> doc;
  doc["bbch"]  = BBCH_SINIFLAR[sonuc.sinifIndex];
  doc["guven"] = sonuc.guvenSkoru;
  doc["sinif"] = sonuc.sinifIndex;
  String json;
  serializeJson(doc, json);
  Serial.println(json);
}

void setup() {
  Serial.begin(115200);
  Serial.println("=== TRAK-AI ESP32-CAM BAŞLIYOR ===");
  if (!kameraBaslat()) {
    delay(3000);
    ESP.restart();
  }
  Serial.println("[SETUP] Hazır!");
}

void loop() {
  unsigned long now = millis();
  if (now - lastInferenceTime >= INFERENCE_INTERVAL_MS) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("[CAM] Görüntü alınamadı!");
      lastInferenceTime = now;
      return;
    }
    InferenceResult sonuc = mockInference(fb);
    esp_camera_fb_return(fb);
    sonucGonder(sonuc);
    Serial.printf("[INF] %s (güven: %.2f)\n",
      BBCH_SINIFLAR[sonuc.sinifIndex], sonuc.guvenSkoru);
    lastInferenceTime = now;
  }
  delay(100);
}