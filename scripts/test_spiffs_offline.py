"""
TRAK-AI Rover — SPIFFS Store-and-Forward Offline Test
======================================================

Amaç: ESP32'nin WiFi koptuğunda veriyi SPIFFS kuyruğuna yazıp, bağlantı
gelince geri yayınlama özelliğini doğrulamak.

Test akışı:
  1. mosquitto_sub başlat → trakaia/rover/data dinle
  2. 60 sn izle, baseline mesaj sayısını not al
  3. Kullanıcı router'a gidip ESP32'yi WiFi'dan koparır
     (router engelle veya ESP32'yi WiFi kapsama dışına çıkar)
  4. 5 dakika offline kal (ESP32 SPIFFS'e yazsın)
  5. Kullanıcı WiFi'ı geri ver
  6. Script "drain" anını yakalar: art arda hızlı mesaj akışı

Kullanım:
  python scripts/test_spiffs_offline.py

NOT: Bu script PASSİF dinleyici. ESP32'yi fiziksel olarak WiFi'dan koparmak
kullanıcının sorumluluğu — yazılımdan WiFi'ı disabling yok (henüz).
"""
from __future__ import annotations

import json
import sys
import time
from collections import deque
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("paho-mqtt eksik. pip install paho-mqtt")
    sys.exit(1)


MQTT_BROKER = "localhost"
MQTT_PORT   = 1883
TOPIC       = "trakaia/rover/data"

# Drain detection: 5 saniyede 3+ mesaj akarsa "drain anı" olarak işaretle
DRAIN_WINDOW_SEC = 5
DRAIN_THRESHOLD  = 3

# Mesajlar arası beklenen aralık (saniye) — normal aralıkta 30sn olmalı (IDLE)
# Bunun çok altı → SPIFFS drain demektir
EXPECTED_GAP_SEC = 30


class OfflineTest:
    def __init__(self) -> None:
        self.start_ts = time.time()
        self.last_msg_ts: float | None = None
        self.msg_history: deque[float] = deque(maxlen=20)
        self.total_messages = 0
        self.online_messages = 0
        self.offline_gap_max = 0.0
        self.drain_events = 0
        self.last_payload: dict | None = None

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(TOPIC)
            print(f"[{self._t()}] ✓ MQTT bağlantı OK, dinleyici {TOPIC}")
        else:
            print(f"[{self._t()}] ✗ MQTT bağlantı RC={rc}")

    def on_message(self, client, userdata, msg):
        now = time.time()
        try:
            payload = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
        self.total_messages += 1
        self.last_payload = payload

        gap = (now - self.last_msg_ts) if self.last_msg_ts else 0
        if self.last_msg_ts is not None:
            self.offline_gap_max = max(self.offline_gap_max, gap)

        # Drain detection
        self.msg_history.append(now)
        recent = [t for t in self.msg_history if (now - t) <= DRAIN_WINDOW_SEC]
        is_drain = len(recent) >= DRAIN_THRESHOLD

        timestamp_field = payload.get("timestamp", "?")
        nem = payload.get("nem_1_pct", "?")
        durum = payload.get("durum", "?")

        if is_drain and gap < 3.0:
            self.drain_events += 1
            marker = "🌊 DRAIN!"
        elif gap > 60:
            marker = f"⚠️ uzun gap ({gap:.0f}s)"
        else:
            marker = "✓"

        print(f"[{self._t()}] {marker} #{self.total_messages} "
              f"ESP_ts={timestamp_field} Nem={nem!s:>6} [{durum}] gap={gap:.1f}s")
        self.last_msg_ts = now

    def _t(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def print_summary(self) -> None:
        elapsed = time.time() - self.start_ts
        print()
        print("=" * 60)
        print(f"TEST SONUCU — Toplam süre: {elapsed:.0f} saniye")
        print("=" * 60)
        print(f"  Alınan mesaj sayısı:     {self.total_messages}")
        print(f"  En uzun gap (offline?):  {self.offline_gap_max:.0f} saniye")
        print(f"  Drain event sayısı:      {self.drain_events}")
        print()
        if self.drain_events > 0:
            print("✅ SPIFFS store-and-forward ÇALIŞIYOR")
            print("   ESP32 offline kayıtları biriktirdi, online olunca toplu gönderdi")
        elif self.offline_gap_max > 60:
            print("⚠️ Uzun gap algılandı ama drain event yakalanmadı")
            print("   Olası nedenler: ESP32 hiç offline olmadı, drain mesajları kaçtı")
        else:
            print("ℹ️ Sürekli online davranış — offline test başarısız")
            print("   ESP32'yi WiFi'dan kopararak test tekrarlanmalı")
        print("=" * 60)


def main() -> None:
    print(f"""
{'=' * 60}
TRAK-AI Rover — SPIFFS Offline Test Monitörü
{'=' * 60}

TEST PROSEDÜRÜ:
  1. Bu script çalışıyor, ESP32 mesajlarını izliyor
  2. NORMAL: 30 saniyede bir mesaj görmelisin (IDLE modda)
  3. ESP32'yi WiFi'dan kopar (router engelle veya cihazı uzaklaştır)
     → 2-5 dakika offline tut
  4. WiFi'ı geri ver → ESP32 yeniden bağlanır
  5. BEKLENEN: art arda HIZLI mesaj akışı (SPIFFS drain) — script
     "🌊 DRAIN!" olarak işaretler

Ctrl+C ile bitir, özet rapor alacaksın.
{'=' * 60}
""")
    test = OfflineTest()
    try:
        client = mqtt.Client(client_id=f"spiffs-test-{int(time.time())}",
                             callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    except (AttributeError, TypeError):
        client = mqtt.Client(client_id=f"spiffs-test-{int(time.time())}")
    client.on_connect = test.on_connect
    client.on_message = test.on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except ConnectionRefusedError:
        print(f"✗ Mosquitto broker'a ({MQTT_BROKER}:{MQTT_PORT}) bağlanamadı")
        sys.exit(1)
    client.loop_start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()
        test.print_summary()


if __name__ == "__main__":
    main()
