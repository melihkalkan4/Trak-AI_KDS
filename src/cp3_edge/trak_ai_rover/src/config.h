#pragma once
/*
 * TRAK-AI Tarım Rover - config.h
 *
 * Tüm pin, kalibrasyon, WiFi/MQTT, OTA ve waypoint sabitleri tek dosyada.
 * Donanım üzerinde fiziksel değişiklik yapıldığında SADECE bu dosya güncellenir.
 *
 * DONANIM HARITASI (ESP32 WROOM-32):
 *   SEN0193 toprak nemi   → GPIO 34  (ADC1_CH6, input-only, TEK sensör)
 *   DHT22 hava sıc/nem    → GPIO 4
 *   HC-SR04 ön mesafe     → TRIG GPIO 5, ECHO GPIO 18
 *   GPS NEO-6M            → UART2, RX GPIO 16, TX GPIO 17, 9600 baud
 *   ESP32-CAM             → UART1, RX GPIO 22, TX GPIO 23, 115200 baud
 *                           (CAM modülünün U0T/U0R pinlerine kablo gider)
 *   L298N motor sürücü    → IN1 GPIO 27, IN2 GPIO 26, IN3 GPIO 25, IN4 GPIO 33
 *                           ENA GPIO 14 (PWM ch0), ENB GPIO 12 (PWM ch1)
 */

// Sırlar (WiFi kimlik bilgileri, OTA şifresi) secrets.h içindedir; secrets.h
// gitignore'ludur. secrets.template.h dosyasını secrets.h'ye kopyalayıp gerçek
// değerleri doldurun. Depoya gerçek şifre COMMIT ETMEYİN.
#include "secrets.h"

// ════════════════════════════════════════════════════════════════════
// WiFi & MQTT
// ════════════════════════════════════════════════════════════════════
// WIFI_SSID ve WIFI_PASSWORD secrets.h içinde tanımlıdır.
#define MQTT_HOST         "192.168.1.107"
#define MQTT_BROKER       MQTT_HOST                    // legacy alias
#define MQTT_PORT         1883
#define MQTT_TOPIC        "trakaia/rover/data"         // outbound telemetri
#define MQTT_TOPIC_CMD    "trakaia/rover/cmd"          // inbound dashboard komutu
#define MQTT_CLIENT       "trak-ai-rover-01"
#define SAHA_ID           "EVR_01"
#define TARLA_ID          1                          // EVR_01 saha → tarla 1 (DB foreign key)

// ════════════════════════════════════════════════════════════════════
// OTA (Over-The-Air firmware update)
// ════════════════════════════════════════════════════════════════════
#define OTA_HOSTNAME      "trak-ai-rover"
// OTA_PASSWORD secrets.h içinde tanımlıdır.
#define OTA_PORT          3232

// ════════════════════════════════════════════════════════════════════
// Sensör pinleri
// ════════════════════════════════════════════════════════════════════
#define DHT22_PIN         4

#define SEN0193_1_PIN     34         // ana toprak nemi (tek sensör)
#define SEN0193_2_PIN     35         // ikinci sensör pini (şu an batarya için kullanılabilir)
#define SOIL_PIN          34         // legacy alias

#define HCSR04_F_TRIG     5
#define HCSR04_F_ECHO     18
#define HCSR04_B_TRIG     19
#define HCSR04_B_ECHO     21

// ════════════════════════════════════════════════════════════════════
// GPS NEO-6M (UART2)
// ════════════════════════════════════════════════════════════════════
#define GPS_RX_PIN        16         // ESP32 RX2 ← GPS TX
#define GPS_TX_PIN        17         // ESP32 TX2 → GPS RX
#define GPS_BAUD          9600

// ════════════════════════════════════════════════════════════════════
// ESP32-CAM (UART1)
// NOT: ESP32-CAM modülünün kendi pinleri U0T (GPIO 1) ve U0R (GPIO 3).
// Bunlar ana ESP32'nin GPIO 22 ve 23'üne bağlanır (UART1 custom pins).
// Ana ESP32'nin UART0'ı USB Serial Monitor için kullanılmaktadır,
// dolayısıyla CAM için UART1 kullanılır.
// ════════════════════════════════════════════════════════════════════
#define CAM_RX_PIN        22         // ESP32 RX1 ← CAM U0T (TX0=GPIO1 of CAM)
#define CAM_TX_PIN        23         // ESP32 TX1 → CAM U0R (RX0=GPIO3 of CAM)
#define CAM_BAUD          115200

// ════════════════════════════════════════════════════════════════════
// L298N motor sürücü (kullanıcı donanım spec'i)
// ════════════════════════════════════════════════════════════════════
#define MOTOR_IN1         27         // sol motor yön A
#define MOTOR_IN2         26         // sol motor yön B
#define MOTOR_IN3         25         // sağ motor yön A
#define MOTOR_IN4         33         // sağ motor yön B
#define MOTOR_ENA         14         // sol motor PWM hız (GPIO 14 → LEDC ch0)
#define MOTOR_ENB         12         // sağ motor PWM hız (GPIO 12 → LEDC ch1)

#define LEDC_ENA          0          // ledcSetup kanalı (motor sol)
#define LEDC_ENB          1          // ledcSetup kanalı (motor sağ)

#define MOTOR_SPEED_NORMAL  180      // 0-255 PWM, ileri-geri için
#define MOTOR_SPEED_SLOW    130      // dönüş + engel manevrası için
#define ENGEL_ESIK_CM        25      // bu mesafenin altında engel say

// ════════════════════════════════════════════════════════════════════
// Sensör mevcudiyet bayrakları
// false ise: pin floating noise vermesin diye okuma atlanır, sentinel -1
// yazılır ve MQTT JSON'a dahil edilmez (orchestrator hayalet anomali görmesin)
// ════════════════════════════════════════════════════════════════════
#define NEM2_SENSOR_PRESENT  false   // ikinci toprak nemi yok
#define HCSR04_F_PRESENT     true    // ÖN mesafe sensörü takılı
#define HCSR04_B_PRESENT     false   // ARKA mesafe sensörü yok

// ════════════════════════════════════════════════════════════════════
// SEN0193 kalibrasyon (lineer interpolasyon)
//
// İKİ SENSÖR VARYANTI VAR:
//   Normal:  DRY_RAW > WET_RAW  (klasik SEN0193, kuru=yüksek V, ıslak=düşük V)
//   Ters:    DRY_RAW < WET_RAW  (bazı klonlar, kuru=düşük V, ıslak=yüksek V)
//
// adcToNem() fonksiyonu otomatik algılar — sadece doğru sayıları gir.
// Kalibrasyon adımı:
//   1. Sensörü kuru havada tut, [SOIL] raw=XXX değerini not al → DRY_RAW
//   2. Probe kısmını suya batır, raw=YYY → WET_RAW
//
// Mevcut sensör: TERS yönlü (raw suya girince ARTıyor)
// ════════════════════════════════════════════════════════════════════
#define SOIL_DRY_RAW       200       // kuru havada raw (düşük çıkıyor)
#define SOIL_WET_RAW       750       // suya batırılmış raw (yüksek çıkıyor)

// ════════════════════════════════════════════════════════════════════
// Zamanlama
// ════════════════════════════════════════════════════════════════════
#define SENSOR_INTERVAL_MS  30000UL  // ACTIVE modda 30sn sensor ölçüm
#define MQTT_INTERVAL_MS    30000UL  // ACTIVE modda 30sn MQTT publish

// ════════════════════════════════════════════════════════════════════
// Waypoint navigasyon (EVR_01 proxy koordinatlar)
// ════════════════════════════════════════════════════════════════════
struct Waypoint {
  float lat;
  float lon;
  char  label[12];
};

#define WAYPOINT_COUNT 4
const Waypoint WAYPOINTS[WAYPOINT_COUNT] = {
  { 41.0450f, 27.2050f, "W1_kuzey" },
  { 41.0445f, 27.2055f, "W2_dogu"  },
  { 41.0440f, 27.2050f, "W3_guney" },
  { 41.0445f, 27.2045f, "W4_bati"  }
};

#define WAYPOINT_RADIUS_M    3.0f    // hedefe bu kadar yaklaşınca "ulaştı"
#define STOP_DURATION_MS     5000UL  // STOPPED state'te ölçüm için bekleme
#define DRIVE_SPEED          180     // ana sürüş PWM hızı

// ════════════════════════════════════════════════════════════════════
// Batarya monitor (opsiyonel — şu an dashboard'da gizli)
// Voltage divider gerekli: BATT → R1=100k → ADC pini → R2=100k → GND
// ════════════════════════════════════════════════════════════════════
#define BATT_ADC_PIN         35      // input-only ADC1
#define BATT_PRESENT         false   // true yapınca firmware loglarında görünür
#define BATT_VDIV_R1         100000.0f
#define BATT_VDIV_R2         100000.0f
#define BATT_ADC_VREF        3.3f
#define BATT_ADC_MAX         4095.0f
#define BATT_VOLT_FULL       4.20f
#define BATT_VOLT_EMPTY      3.00f
