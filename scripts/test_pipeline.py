"""
TRAK-AI KDS — End-to-End Pipeline Stress Test
==============================================

Mock rover'dan N farklı senaryo mesajı atar, orchestrator'ın
trakaia/db/pending'e yazdığı kayıtları izler, başarı oranı raporu üretir.

Akış:
  1. mosquitto_sub → trakaia/db/pending (orchestrator çıkışı)
  2. Mock rover → trakaia/rover/data (test mesajları)
  3. Her test mesajının orchestrator tarafında işlendiğini kontrol et
  4. LLM süresi, anomali sayısı, throttle olan vs.

Gerekli:
  - Mosquitto broker çalışıyor (localhost:1883)
  - mqtt_orchestrator.py çalışıyor (DASHBOARD_APPROVAL_MODE=True)
  - Ollama + gemma3:4b yüklü

Kullanım:
  python scripts/test_pipeline.py             # 5 mesaj test
  python scripts/test_pipeline.py --count 20  # 20 mesaj
  python scripts/test_pipeline.py --interval 10  # 10sn aralık

Çıktı: success_rate, avg_llm_time, anomali_freq, throttle_count
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("paho-mqtt eksik. pip install paho-mqtt")
    sys.exit(1)


MQTT_BROKER = "localhost"
MQTT_PORT   = 1883
DATA_TOPIC    = "trakaia/rover/data"
PENDING_TOPIC = "trakaia/db/pending"
ADVISORY_TOPIC = "trakaia/kds/advisory"

# Test senaryoları (mock_rover'daki ile aynı yapı)
SCENARIOS = {
    "normal": {
        "nem_1_pct": 28.0, "hava_temp_c": 22.0, "hava_nem_pct": 60.0,
        "bbch_sinif": "BBCH_50_59", "bbch_guven": 0.88,
    },
    "dusuk_nem": {
        "nem_1_pct": 12.0, "hava_temp_c": 28.0, "hava_nem_pct": 45.0,
        "bbch_sinif": "BBCH_50_59", "bbch_guven": 0.85,
    },
    "hastalik": {
        "nem_1_pct": 22.0, "hava_temp_c": 25.0, "hava_nem_pct": 78.0,
        "bbch_sinif": "BBCH_60_69", "bbch_guven": 0.91,
        "hastalik": "Mildiyoe", "hastalik_guven": 0.95,
    },
    "sicak_stres": {
        "nem_1_pct": 14.0, "hava_temp_c": 42.5, "hava_nem_pct": 28.0,
        "bbch_sinif": "BBCH_50_59", "bbch_guven": 0.85,
    },
}


class PipelineTest:
    def __init__(self, count: int, interval: int) -> None:
        self.count = count
        self.interval = interval
        self.sent_messages: list[dict] = []
        self.received_pending: list[dict] = []
        self.received_advisories: list[dict] = []
        self.start_ts = time.time()
        self.first_sent_ts: float | None = None
        self.last_pending_ts: float | None = None

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(PENDING_TOPIC)
            client.subscribe(ADVISORY_TOPIC)
            print(f"[{self._t()}] ✓ MQTT bağlı, dinleyici {PENDING_TOPIC} + {ADVISORY_TOPIC}")
        else:
            print(f"[{self._t()}] ✗ MQTT bağlantı RC={rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
        ts = time.time()
        if msg.topic == PENDING_TOPIC:
            self.received_pending.append({"ts": ts, "payload": payload})
            self.last_pending_ts = ts
            anomali_sayisi = payload.get("anomali_sayisi", 0)
            rover_id = payload.get("rover_id", "?")
            print(f"[{self._t()}] 📥 PENDING #{len(self.received_pending)}: "
                  f"rover={rover_id} anomali={anomali_sayisi}")
        elif msg.topic == ADVISORY_TOPIC:
            self.received_advisories.append({"ts": ts, "payload": payload})
            tip = payload.get("anomali_tipi") or payload.get("anomali") or "?"
            print(f"[{self._t()}] 🤖 ADVISORY #{len(self.received_advisories)}: {tip}")

    def _t(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def send_test_messages(self, client) -> None:
        """Mock rover gibi davran: N senaryo gönder."""
        scenarios = list(SCENARIOS.keys())
        print(f"\n[{self._t()}] 🚀 {self.count} test mesajı gönderiliyor "
              f"(her {self.interval} saniyede bir)\n")

        for i in range(self.count):
            name = scenarios[i % len(scenarios)]
            base = dict(SCENARIOS[name])
            # Jitter
            base["nem_1_pct"]    = round(base["nem_1_pct"]    + random.uniform(-2, 2), 1)
            base["hava_temp_c"]  = round(base["hava_temp_c"]  + random.uniform(-1, 1), 1)
            base["hava_nem_pct"] = round(base["hava_nem_pct"] + random.uniform(-3, 3), 1)
            base["rover_id"]     = "PIPELINE_TEST_01"
            base["saha_id"]      = "TEST"
            base["tarla_id"]     = 2     # test tarlası (mock tarafı)
            base["timestamp"]    = int(time.time())
            base["gps_lat"]      = 41.6940
            base["gps_lon"]      = 27.1050
            base["gps_valid"]    = True
            base["scenario_name"] = name
            base["waypoint_id"]  = i % 4
            base["waypoint_label"] = ["W1", "W2", "W3", "W4"][i % 4]

            payload = json.dumps(base, ensure_ascii=False)
            client.publish(DATA_TOPIC, payload)
            if i == 0:
                self.first_sent_ts = time.time()
            self.sent_messages.append({"ts": time.time(), "name": name, "payload": base})

            anomali_var = name != "normal"
            marker = "⚠️ " if anomali_var else "✓"
            print(f"[{self._t()}] {marker} {i+1}/{self.count} gönderildi: {name} "
                  f"(nem={base['nem_1_pct']}% temp={base['hava_temp_c']}°C)")

            if i < self.count - 1:
                time.sleep(self.interval)

        print(f"\n[{self._t()}] ✓ Tüm test mesajları gönderildi. "
              f"Orchestrator işliyor, 2 dakika bekleniyor...\n")

    def print_summary(self) -> None:
        total_time = time.time() - self.start_ts
        sent = len(self.sent_messages)
        received = len(self.received_pending)
        advisories = len(self.received_advisories)

        print()
        print("=" * 60)
        print(f"PİPELİNE TEST SONUCU")
        print("=" * 60)
        print(f"  Toplam süre:               {total_time:.0f} saniye")
        print(f"  Gönderilen mesaj:          {sent}")
        print(f"  Alınan DB pending kayıt:   {received}")
        print(f"  Alınan advisory mesaj:     {advisories}")
        success_rate = (received / sent * 100) if sent > 0 else 0
        print(f"  Başarı oranı:              {success_rate:.1f}%")
        print()

        # Anomali tipleri
        if self.received_pending:
            anomali_tipleri = {}
            for rec in self.received_pending:
                anomaliler_str = rec["payload"].get("anomaliler", "[]")
                try:
                    anomaliler = json.loads(anomaliler_str) if isinstance(anomaliler_str, str) else anomaliler_str
                except Exception:
                    anomaliler = []
                for a in anomaliler or []:
                    # Anomaly açıklamasından tipini çıkar
                    tip = a.split(":")[0] if ":" in a else a[:30]
                    anomali_tipleri[tip] = anomali_tipleri.get(tip, 0) + 1

            if anomali_tipleri:
                print("  Anomali dağılımı:")
                for tip, count in sorted(anomali_tipleri.items(), key=lambda x: -x[1]):
                    print(f"    {count:3d}x  {tip}")
                print()

        # LLM süresi (advisory'lerden)
        if self.received_advisories:
            print(f"  LLM advisory üretildi:     {advisories} kez")
            # Süre bilgisi advisory'de yok, manuel ölçüm gerekli

        # Throttle tespiti
        throttled = sent - received
        if throttled > 0:
            print(f"  Throttle olan (10dk lock): {throttled} (beklenmiş)")

        print()
        if success_rate >= 80:
            print("✅ PIPELINE SAĞLAM — başarı oranı yüksek")
        elif success_rate >= 50:
            print("⚠️ PIPELINE KISMEN ÇALIŞIYOR — kayıp var, throttling normal olabilir")
        else:
            print("❌ PIPELINE PROBLEMLİ — orchestrator çalışıyor mu? LLM hatası mı?")
        print("=" * 60)


def main() -> None:
    ap = argparse.ArgumentParser(description="TRAK-AI Pipeline Stress Test")
    ap.add_argument("--count", type=int, default=5,
                    help="Test mesaj sayısı (default 5)")
    ap.add_argument("--interval", type=int, default=15,
                    help="Mesajlar arası saniye (default 15)")
    args = ap.parse_args()

    test = PipelineTest(args.count, args.interval)
    try:
        client = mqtt.Client(client_id=f"pipeline-test-{int(time.time())}",
                             callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    except (AttributeError, TypeError):
        client = mqtt.Client(client_id=f"pipeline-test-{int(time.time())}")
    client.on_connect = test.on_connect
    client.on_message = test.on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=600)
    except ConnectionRefusedError:
        print(f"✗ Mosquitto bağlantı reddedildi ({MQTT_BROKER}:{MQTT_PORT})")
        sys.exit(1)
    client.loop_start()

    # Subscribe'ların aktive olmasını bekle
    time.sleep(2)

    try:
        test.send_test_messages(client)
        # LLM'in işlemesini bekle (her mesaj için ~60sn)
        wait_total = max(120, args.count * 60)
        wait_start = time.time()
        while time.time() - wait_start < wait_total:
            remaining = wait_total - (time.time() - wait_start)
            if len(test.received_pending) >= test.count:
                print(f"\n[{test._t()}] ✓ Tüm pending kayıtları alındı, erken bitir")
                break
            time.sleep(5)
            print(f"[{test._t()}] Beklenmekte... pending={len(test.received_pending)}/{test.count} "
                  f"(kalan ~{remaining:.0f}s)")
    except KeyboardInterrupt:
        print(f"\n[{test._t()}] Kullanıcı Ctrl+C ile iptal etti")
    finally:
        client.loop_stop()
        client.disconnect()
        test.print_summary()


if __name__ == "__main__":
    main()
