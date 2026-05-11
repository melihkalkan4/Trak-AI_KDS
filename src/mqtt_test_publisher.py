"""
TRAK-AI KDS — MQTT Test Publisher
===================================
Mock rover verisi gonderir; mqtt_orchestrator.py'yi test etmek icin kullanilir.

Senaryo A: Normal tarla (nem %28, saglikli bitki, BBCH uyumlu)
Senaryo B: 3 anomali (nem farki 17pt, Mildiyoe guven %82, BBCH sapmasi)

Kullanim: python src/mqtt_test_publisher.py
"""
import sys
import json
import time
from datetime import datetime

import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
PUBLISH_TOPIC = "trakaia/rover/data"
INTERVAL_SEC = 5

# Senaryo A: Normal tarla — anomali beklenmez
SENARYO_A = {
    "gps_lat": 41.6940,
    "gps_lon": 27.1050,
    "gps_valid": True,
    "nem_1_pct": 28.0,
    "nem_2_pct": 26.5,
    "hava_temp_c": 20.5,
    "hava_nem_pct": 62.0,
    "engel_on_cm": 200,
    "engel_arka_cm": 999,
    "bbch_sinif": "BBCH_50_59",   # Mayis icin bugday beklentisi: 50-79
    "bbch_guven": 0.88,
    "waypoint_id": 1,
    "rover_id": "trak-ai-rover-01",
}

# Senaryo B: 3 anomali — LLM tetiklenmeli
#   1) NEM_FARKI: abs(11.0 - 28.0) = 17 > 10
#   2) DUSUK_NEM: ort=(11+28)/2 = 19.5 < 20
#   3) HASTALIK:  Mildiyoe guven 0.82 > 0.70
#   4) BBCH_SAPMASI: BBCH_10_19 Mayis icin 50-79 araliginin disinda
SENARYO_B = {
    "gps_lat": 41.6940,
    "gps_lon": 27.1050,
    "gps_valid": True,
    "nem_1_pct": 11.0,
    "nem_2_pct": 28.0,
    "hava_temp_c": 28.5,
    "hava_nem_pct": 45.0,
    "engel_on_cm": 120,
    "engel_arka_cm": 999,
    "bbch_sinif": "BBCH_10_19",   # Yanlis evre — anomali tetikler
    "bbch_guven": 0.71,
    "hastalik": "Mildiyoe",
    "hastalik_guven": 0.82,
    "waypoint_id": 3,
    "rover_id": "trak-ai-rover-01",
}


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def publish_scenario(client, name: str, data: dict) -> None:
    data["timestamp"] = int(time.time())
    payload = json.dumps(data, ensure_ascii=False)
    client.publish(PUBLISH_TOPIC, payload)
    log(f"Senaryo {name} gonderildi ({len(payload)} byte)")
    log(f"  nem_1={data['nem_1_pct']}% / nem_2={data['nem_2_pct']}% | BBCH: {data['bbch_sinif']}")
    if data.get("hastalik"):
        log(f"  Hastalik: {data['hastalik']} (guven: {data.get('hastalik_guven', 0):.0%})")


def main():
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        client = mqtt.Client()

    log(f"MQTT broker'a baglaniliyor: {MQTT_BROKER}:{MQTT_PORT}")
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except ConnectionRefusedError:
        log("HATA: MQTT broker'a baglanamadi. 'mosquitto' ile broker'i calistirin.")
        return

    client.loop_start()
    log(f"Test yayincisi hazir — topic: {PUBLISH_TOPIC}")
    log("=" * 50)

    log("=== SENARYO A: Normal Tarla ===")
    log("Beklenen: 0 anomali, LLM tetiklenmemeli")
    publish_scenario(client, "A", SENARYO_A)

    log(f"{INTERVAL_SEC} saniye bekleniyor...")
    time.sleep(INTERVAL_SEC)

    log("")
    log("=== SENARYO B: Coklu Anomali ===")
    log("Beklenen: 3-4 anomali, LLM tetiklenmeli (LLM yaniti ~30-60 sn surebilir)")
    publish_scenario(client, "B", SENARYO_B)

    log("Orchestrator yaniti bekleniyor (60 sn)...")
    time.sleep(60)

    client.loop_stop()
    client.disconnect()
    log("Test tamamlandi.")


if __name__ == "__main__":
    main()
