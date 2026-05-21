#include <Arduino.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include "mbedtls/base64.h"

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

unsigned long lastCaptureTime = 0;
const unsigned long CAPTURE_INTERVAL_MS = 5000;

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
  config.frame_size    = FRAMESIZE_QVGA;  // 320x240
  config.jpeg_quality  = 15;              // Küçük boyut (~8-15KB)
  config.fb_count      = 1;
  config.grab_mode     = CAMERA_GRAB_WHEN_EMPTY;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAM] Hata: 0x%x\n", err);
    return false;
  }
  Serial.println("[CAM] Kamera baslatildi. (QVGA, quality=15)");
  return true;
}

// JPEG frame'i base64 encode et, JSON formatında Serial'e gönder
void goruntuyuGonder(camera_fb_t* fb) {
  // Base64 boyutunu hesapla
  size_t b64_len = 0;
  mbedtls_base64_encode(NULL, 0, &b64_len, fb->buf, fb->len);

  // Bellek ayır
  uint8_t* b64_buf = (uint8_t*)malloc(b64_len + 1);
  if (!b64_buf) {
    Serial.println("[CAM] malloc hatasi — goruntusu gonderilemedi");
    return;
  }

  // Encode et
  mbedtls_base64_encode(b64_buf, b64_len, &b64_len, fb->buf, fb->len);
  b64_buf[b64_len] = '\0';

  // JSON: prefix + data + suffix — tek satır (\n ile biter, rover readStringUntil('\n') okur)
  Serial.print("{\"type\":\"image\",\"fmt\":\"jpeg\",\"w\":320,\"h\":240,\"bytes\":");
  Serial.print((int)fb->len);
  Serial.print(",\"data\":\"");
  Serial.print((char*)b64_buf);
  Serial.println("\"}");

  Serial.printf("[CAM] Goruntu gonderildi: %d bytes JPEG -> %d bytes base64\n",
                (int)fb->len, (int)b64_len);
  free(b64_buf);
}

void setup() {
  Serial.begin(115200);
  Serial.println("=== TRAK-AI ESP32-CAM BASLIYOR (Hybrid Edge-Fog) ===");
  if (!kameraBaslat()) {
    delay(3000);
    ESP.restart();
  }
  Serial.println("[SETUP] Hazir! Komutlar: CAPTURE");
}

void loop() {
  // Ana rover'dan CAPTURE komutu gelirse anlik goruntu gonder
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "CAPTURE") {
      camera_fb_t* fb = esp_camera_fb_get();
      if (fb) {
        goruntuyuGonder(fb);
        esp_camera_fb_return(fb);
      } else {
        Serial.println("[CAM] CAPTURE hatasi: goruntu alinamadi");
      }
    }
  }

  // Periyodik otomatik goruntu gonderimi (her 5 saniye)
  unsigned long now = millis();
  if (now - lastCaptureTime >= CAPTURE_INTERVAL_MS) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("[CAM] Goruntu alinamadi!");
      lastCaptureTime = now;
      return;
    }
    goruntuyuGonder(fb);
    esp_camera_fb_return(fb);
    lastCaptureTime = now;
  }

  delay(100);
}
