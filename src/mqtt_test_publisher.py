"""
TRAK-AI KDS — Mock Rover (sürekli yayın)
==========================================
Sahte rover; mqtt_orchestrator.py'yi test etmek + dashboard'da
"Mock Rover" sekmesini doldurmak için kullanılır.

Davranış:
  - Sürekli loop (varsayılan 5 sn aralık, --once ile tek atış)
  - 3 senaryo arası rotation:
    A) Normal (anomalisiz)
    B) Çoklu anomali (3-4)
    C) Hafif düşük nem (sınırda)
  - rover_id='MOCK_ROVER_01', tarla_id=2 — gerçek rover'dan ayrı
    DB satırları, dashboard farklı sekmede gösterir.

Kullanım:
  python src/mqtt_test_publisher.py              # sürekli loop
  python src/mqtt_test_publisher.py --once       # eski tek-atış davranışı
  python src/mqtt_test_publisher.py --interval 3 # 3 sn aralık
"""
import argparse
import json
import random
import sys
import time
from datetime import datetime

import paho.mqtt.client as mqtt

MQTT_BROKER   = "localhost"
MQTT_PORT     = 1883
PUBLISH_TOPIC = "trakaia/rover/data"

# Mock rover kimlik bilgileri — gercek rover'dan ayri DB satirlari icin
MOCK_ROVER_ID = "MOCK_ROVER_01"
MOCK_TARLA_ID = 2

# Senaryolar — base degerler, random jitter ile her atista hafif degisir
SCENARIOS = {
    "A_normal": {
        "gps_lat": 41.6940, "gps_lon": 27.1050, "gps_valid": True,
        "nem_1_pct": 28.0, "nem_2_pct": 26.5,
        "hava_temp_c": 20.5, "hava_nem_pct": 62.0,
        "engel_on_cm": 200,
        "bbch_sinif": "BBCH_50_59", "bbch_guven": 0.88,
        "waypoint_id": 1, "waypoint_label": "W1_kuzey",
    },
    "B_coklu_anomali": {
        "gps_lat": 41.6941, "gps_lon": 27.1052, "gps_valid": True,
        "nem_1_pct": 11.0, "nem_2_pct": 28.0,        # NEM_FARKI
        "hava_temp_c": 28.5, "hava_nem_pct": 45.0,
        "engel_on_cm": 120,
        "bbch_sinif": "BBCH_10_19",                   # BBCH sapmasi
        "bbch_guven": 0.71,
        "hastalik": "Mildiyoe", "hastalik_guven": 0.82,
        "waypoint_id": 3, "waypoint_label": "W3_dogu",
    },
    "C_hafif_dusuk": {
        "gps_lat": 41.6939, "gps_lon": 27.1048, "gps_valid": True,
        "nem_1_pct": 21.0, "nem_2_pct": 19.5,        # sinirda
        "hava_temp_c": 24.0, "hava_nem_pct": 55.0,
        "engel_on_cm": 350,
        "bbch_sinif": "BBCH_50_59", "bbch_guven": 0.83,
        "waypoint_id": 2, "waypoint_label": "W2_bati",
    },
    # ── Yeni senaryolar (stress test için) ──────────────────────────
    "D_hastalik_kritik": {
        # Mildiyoe %95 — kritik hastalık alarmı, acil müdahale önerisi
        "gps_lat": 41.6942, "gps_lon": 27.1053, "gps_valid": True,
        "nem_1_pct": 22.0, "nem_2_pct": 21.5,
        "hava_temp_c": 25.0, "hava_nem_pct": 78.0,      # yüksek hava nemi → mildiyö ortamı
        "engel_on_cm": 200,
        "bbch_sinif": "BBCH_60_69", "bbch_guven": 0.91,
        "hastalik": "Mildiyoe", "hastalik_guven": 0.95,
        "waypoint_id": 4, "waypoint_label": "W4_kose",
    },
    "E_sicaklik_stresi": {
        # 40°C+ sıcak stres — orchestrator MEVSIM_DISI veya HEAT_STRESS uyarısı
        "gps_lat": 41.6938, "gps_lon": 27.1051, "gps_valid": True,
        "nem_1_pct": 14.0, "nem_2_pct": 13.0,           # sıcakta kurudu
        "hava_temp_c": 42.5, "hava_nem_pct": 28.0,      # ekstrem
        "engel_on_cm": 280,
        "bbch_sinif": "BBCH_50_59", "bbch_guven": 0.85,
        "waypoint_id": 1, "waypoint_label": "W1_kuzey",
    },
    "F_yagmur_sonrasi": {
        # Yağmur sonrası ıslak toprak — anomali OLMAMALI
        "gps_lat": 41.6940, "gps_lon": 27.1050, "gps_valid": True,
        "nem_1_pct": 88.0, "nem_2_pct": 85.0,
        "hava_temp_c": 18.0, "hava_nem_pct": 92.0,
        "engel_on_cm": 999,
        "bbch_sinif": "BBCH_50_59", "bbch_guven": 0.89,
        "waypoint_id": 2, "waypoint_label": "W2_bati",
    },
}


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def build_payload(scenario_key: str) -> dict:
    """Senaryoyu tabandan al, MOCK_* etiketleri + biraz jitter ekle."""
    base = dict(SCENARIOS[scenario_key])

    # Random jitter (gerçek sensör gürültüsü simülasyonu)
    base["nem_1_pct"]    = round(base["nem_1_pct"]    + random.uniform(-1.5, 1.5), 1)
    base["nem_2_pct"]    = round(base["nem_2_pct"]    + random.uniform(-1.5, 1.5), 1)
    base["hava_temp_c"]  = round(base["hava_temp_c"]  + random.uniform(-0.5, 0.5), 1)
    base["hava_nem_pct"] = round(base["hava_nem_pct"] + random.uniform(-3.0, 3.0), 1)
    base["gps_lat"]      = round(base["gps_lat"]      + random.uniform(-0.0001, 0.0001), 6)
    base["gps_lon"]      = round(base["gps_lon"]      + random.uniform(-0.0001, 0.0001), 6)

    # Kimlik bilgileri — orchestrator + dashboard bunlara göre yönlendiriyor
    base["rover_id"]  = MOCK_ROVER_ID
    base["tarla_id"]  = MOCK_TARLA_ID
    base["scenario"]  = scenario_key
    base["timestamp"] = int(time.time())
    return base


def publish(client, scenario_key: str) -> None:
    payload = build_payload(scenario_key)
    msg = json.dumps(payload, ensure_ascii=False)
    client.publish(PUBLISH_TOPIC, msg)
    extras = f"BBCH={payload['bbch_sinif']}"
    if payload.get("hastalik"):
        extras += f" Hastalik={payload['hastalik']}"
    log(f"[{scenario_key}] gonderildi ({len(msg)}B) | "
        f"Nem1={payload['nem_1_pct']}% Nem2={payload['nem_2_pct']}% "
        f"Temp={payload['hava_temp_c']}C | {extras}")


def connect(broker: str, port: int) -> mqtt.Client:
    try:
        client = mqtt.Client(client_id=f"mock-rover-{int(time.time())}",
                             callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    except (AttributeError, TypeError):
        client = mqtt.Client(client_id=f"mock-rover-{int(time.time())}")
    log(f"MQTT broker'a baglaniliyor: {broker}:{port}")
    try:
        client.connect(broker, port, keepalive=60)
    except ConnectionRefusedError:
        log("HATA: MQTT broker'a baglanamadi. mosquitto calisiyor mu?")
        sys.exit(1)
    client.loop_start()
    return client


def main() -> None:
    ap = argparse.ArgumentParser(description="Trak-AI Mock Rover (continuous)")
    ap.add_argument("--once", action="store_true",
                    help="Eski davranis: A + B birer kez yolla, cik")
    ap.add_argument("--interval", type=int, default=5,
                    help="Yayinlar arasi saniye (default 5)")
    ap.add_argument("--broker", default=MQTT_BROKER)
    ap.add_argument("--port", type=int, default=MQTT_PORT)
    args = ap.parse_args()

    client = connect(args.broker, args.port)
    log(f"Mock rover hazir | rover_id={MOCK_ROVER_ID} tarla_id={MOCK_TARLA_ID} "
        f"| topic={PUBLISH_TOPIC}")

    if args.once:
        log("=" * 50)
        log("--once modu: A + B atislari")
        publish(client, "A_normal")
        time.sleep(args.interval)
        publish(client, "B_coklu_anomali")
        log("60 sn orchestrator yaniti bekleniyor...")
        time.sleep(60)
    else:
        log("=" * 50)
        log("Continuous mode: A → C → B → A → ... (Ctrl+C ile dur)")
        log("=" * 50)
        # B + D + E daha seyrek (kritik anomali); A + C + F normal döngü
        rotation = ["A_normal", "C_hafif_dusuk", "A_normal", "F_yagmur_sonrasi",
                    "C_hafif_dusuk", "B_coklu_anomali",
                    "A_normal", "D_hastalik_kritik",
                    "A_normal", "E_sicaklik_stresi"]
        idx = 0
        try:
            while True:
                publish(client, rotation[idx % len(rotation)])
                idx += 1
                time.sleep(args.interval)
        except KeyboardInterrupt:
            log("Ctrl+C alindi, kapatiliyor...")

    client.loop_stop()
    client.disconnect()
    log("Mock rover durduruldu.")


if __name__ == "__main__":
    main()
