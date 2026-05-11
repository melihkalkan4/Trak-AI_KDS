"""
TRAK-AI KDS — MQTT Orchestrator
================================
CP-3 rover'dan gelen MQTT mesajlarini dinler, anomali tespit eder,
CP-4 RAG/LLM ile Turkce tavsiye uretir ve sonucu yayinlar.

Kullanim: python src/mqtt_orchestrator.py
"""
import sys
import os
import json
import time
import gc
from datetime import datetime

import paho.mqtt.client as mqtt

# Path ayarlari (demo.py referans alinarak)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CP2_DIR = os.path.join(PROJECT_ROOT, "src", "cp2_model")
CP4_DIR = os.path.join(PROJECT_ROOT, "src", "cp4_rag")
sys.path.insert(0, CP2_DIR)
sys.path.insert(0, CP4_DIR)

from config import ANOMALY_THRESHOLDS
from build_index import load_faiss_index
from retriever import tri_rag_retrieve, format_context
from llm_engine import check_ollama_connection, rover_alert_query

# MQTT ayarlari
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
SUBSCRIBE_TOPIC = "trakaia/rover/data"
PUBLISH_TOPIC = "trakaia/kds/advisory"

# Anomali esikleri
NEM_FARK_MIN = 10        # iki sensor arasi nem farki %
NEM_DUSUK_ESIK = 20     # mutlak dusuk nem esigi %
HASTALIK_GUVEN_MIN = 0.70

# Bugday icin ay bazli beklenen BBCH araligi (Trakya, Turkiye)
WHEAT_BBCH_BY_MONTH = {
    1: (0, 29), 2: (0, 29), 3: (0, 39),
    4: (30, 59), 5: (50, 79), 6: (60, 89),
    7: (70, 99), 8: (0, 19), 9: (0, 9),
    10: (0, 9), 11: (0, 19), 12: (0, 19),
}

# Global durum
vectorstore = None
chunks = None


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_bbch_low(bbch_sinif: str) -> int:
    """'BBCH_30_39' -> 30"""
    try:
        return int(bbch_sinif.split("_")[1])
    except Exception:
        return -1


def detect_anomalies(payload: dict, cp2_result: dict) -> list:
    anomalies = []
    month = datetime.now().month

    nem_1 = float(payload.get("nem_1_pct", 0))
    nem_2 = float(payload.get("nem_2_pct", 0))
    nem_fark = abs(nem_1 - nem_2)
    nem_ort = (nem_1 + nem_2) / 2

    if nem_fark > NEM_FARK_MIN:
        seviye = "YUKSEK" if nem_fark > 15 else "ORTA"
        anomalies.append({
            "tip": "NEM_FARKI",
            "aciklama": f"Toprak nemi sensorleri arasi fark {nem_fark:.1f}% (esik: {NEM_FARK_MIN}%)",
            "seviye": seviye,
        })

    if nem_ort < NEM_DUSUK_ESIK:
        seviye = "KRITIK" if nem_ort < 15 else "YUKSEK"
        anomalies.append({
            "tip": "DUSUK_NEM",
            "aciklama": f"Ortalama toprak nemi cok dusuk: {nem_ort:.1f}% (esik: {NEM_DUSUK_ESIK}%)",
            "seviye": seviye,
        })

    hastalik = payload.get("hastalik")
    hastalik_guven = float(payload.get("hastalik_guven", 0))
    if hastalik and hastalik_guven > HASTALIK_GUVEN_MIN:
        seviye = "KRITIK" if hastalik_guven > 0.85 else "YUKSEK"
        anomalies.append({
            "tip": "HASTALIK",
            "aciklama": f"{hastalik} tespit edildi, guven: {hastalik_guven:.0%}",
            "seviye": seviye,
        })

    bbch_sinif = payload.get("bbch_sinif", "")
    if bbch_sinif:
        bbch_val = parse_bbch_low(bbch_sinif)
        beklenti = WHEAT_BBCH_BY_MONTH.get(month)
        if beklenti and bbch_val >= 0:
            low, high = beklenti
            if not (low <= bbch_val <= high):
                anomalies.append({
                    "tip": "BBCH_SAPMASI",
                    "aciklama": (
                        f"Buyume evresi beklenenin disinda: {bbch_sinif} "
                        f"(Ay {month} icin beklenen BBCH {low}-{high})"
                    ),
                    "seviye": "ORTA",
                })

    return anomalies


def build_anomaly_context(payload: dict, anomalies: list, cp2_result: dict) -> str:
    lines = [
        f"Rover ID: {payload.get('rover_id', 'bilinmiyor')}",
        f"GPS: {payload.get('gps_lat', 0):.4f}N, {payload.get('gps_lon', 0):.4f}E",
        f"Toprak nemi: sensor1={payload.get('nem_1_pct', 0):.1f}%, sensor2={payload.get('nem_2_pct', 0):.1f}%",
        f"Hava: {payload.get('hava_temp_c', 0):.1f}C, nem %{payload.get('hava_nem_pct', 0):.0f}",
        f"BBCH: {payload.get('bbch_sinif', 'bilinmiyor')} (guven: {payload.get('bbch_guven', 0):.0%})",
    ]
    if payload.get("hastalik"):
        lines.append(
            f"Hastalik: {payload['hastalik']} (guven: {float(payload.get('hastalik_guven', 0)):.0%})"
        )
    lines.append("")
    lines.append("TESPIT EDILEN ANOMALILER:")
    for i, a in enumerate(anomalies, 1):
        lines.append(f"{i}. [{a['seviye']}] {a['tip']}: {a['aciklama']}")

    if cp2_result:
        ctx = cp2_result.get("llm_context", "")[:250]
        if ctx:
            lines.append("")
            lines.append(f"MODEL TAHMINI: {ctx}")

    return "\n".join(lines)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log(f"MQTT broker'a baglandi ({MQTT_BROKER}:{MQTT_PORT})")
        client.subscribe(SUBSCRIBE_TOPIC)
        log(f"Topic dinleniyor: {SUBSCRIBE_TOPIC}")
    else:
        log(f"MQTT baglanti hatasi: rc={rc}")


def on_message(client, userdata, msg):
    log(f"Mesaj alindi — topic={msg.topic}, {len(msg.payload)} byte")

    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError as e:
        log(f"JSON parse hatasi: {e}")
        return

    log(
        f"Rover: {payload.get('rover_id', '?')} | "
        f"GPS: ({payload.get('gps_lat', 0):.4f}, {payload.get('gps_lon', 0):.4f}) | "
        f"Nem: {payload.get('nem_1_pct', 0):.1f}%/{payload.get('nem_2_pct', 0):.1f}% | "
        f"BBCH: {payload.get('bbch_sinif', '?')}"
    )

    # CP-2 tahmini (test modu)
    cp2_result = None
    try:
        log("CP-2 tahmini baslatiliyor (test modu)...")
        from inference_cp2 import predict
        cp2_result = predict("Wheat")
        log(
            f"CP-2 tamamlandi: NDVI={cp2_result.get('current_ndvi', 0):.4f}, "
            f"Saglik={cp2_result.get('health', {}).get('status', '?')}"
        )
        gc.collect()
    except Exception as e:
        log(f"CP-2 hatasi (devam ediliyor): {e}")

    # Anomali tespiti
    anomalies = detect_anomalies(payload, cp2_result)
    log(f"Anomali tespiti: {len(anomalies)} anomali bulundu")

    advisory = None
    duration_sec = None

    if anomalies:
        for a in anomalies:
            log(f"  [{a['seviye']}] {a['tip']}: {a['aciklama']}")

        anomaly_context = build_anomaly_context(payload, anomalies, cp2_result)

        rag_query_text = " ".join(a["aciklama"] for a in anomalies)
        retrieved = tri_rag_retrieve(rag_query_text, vectorstore, chunks)
        field_context = format_context(retrieved)
        log(f"RAG: {len(retrieved)} belge alindi. LLM sorgulanıyor...")

        t0 = time.time()
        try:
            llm_result = rover_alert_query(anomaly_context, field_context)
            duration_sec = round(time.time() - t0, 1)
            advisory = llm_result.get("answer", "")
            log(f"LLM yanit suresi: {duration_sec}s | Token: {llm_result.get('tokens', 0)}")
            log("--- Turkce Tavsiye ---")
            print(advisory, flush=True)
            log("---------------------")
        except Exception as e:
            duration_sec = round(time.time() - t0, 1)
            log(f"LLM hatasi: {e}")
            advisory = f"LLM hatasi: {e}"
    else:
        log("Anomali yok, LLM tetiklenmedi.")
        advisory = "Tarlada anormal durum tespit edilmedi. Sulama ve gubreleme plani devam ediyor."

    result = {
        "rover_id": payload.get("rover_id", "bilinmiyor"),
        "timestamp": datetime.now().isoformat(),
        "gps": {
            "lat": payload.get("gps_lat", 0),
            "lon": payload.get("gps_lon", 0),
            "valid": payload.get("gps_valid", False),
        },
        "sensor_data": {
            "nem_1_pct": payload.get("nem_1_pct"),
            "nem_2_pct": payload.get("nem_2_pct"),
            "hava_temp_c": payload.get("hava_temp_c"),
            "bbch_sinif": payload.get("bbch_sinif"),
        },
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "llm_triggered": len(anomalies) > 0,
        "advisory": advisory,
        "duration_sec": duration_sec,
    }

    payload_out = json.dumps(result, ensure_ascii=False)
    client.publish(PUBLISH_TOPIC, payload_out)
    log(f"Tavsiye yayinlandi: {PUBLISH_TOPIC} ({len(payload_out)} byte)")
    log("-" * 50)


def main():
    global vectorstore, chunks

    log("=" * 50)
    log("TRAK-AI MQTT ORCHESTRATOR BASLATILIYOR")
    log("=" * 50)

    log("Ollama kontrolu...")
    if not check_ollama_connection():
        log("UYARI: Ollama baglantisi yok — LLM adimi basarisiz olacak.")

    log("FAISS indeks yukleniyor...")
    vectorstore, chunks = load_faiss_index()
    if vectorstore is None:
        log("HATA: FAISS indeks bulunamadi. Once 'python main_rag.py build' calistirin.")
        return
    log(f"FAISS yuklendi: {len(chunks)} belge parcasi")

    try:
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        mqtt_client = mqtt.Client()

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    log(f"MQTT broker'a baglaniliyor: {MQTT_BROKER}:{MQTT_PORT}")
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except ConnectionRefusedError:
        log("HATA: MQTT broker'a baglanamadi. Mosquitto calisiyor mu? 'mosquitto' ile baslatin.")
        return

    log("Hazir — mesajlar bekleniyor... (Ctrl+C ile durdur)")
    log("-" * 50)
    mqtt_client.loop_forever()


if __name__ == "__main__":
    main()
