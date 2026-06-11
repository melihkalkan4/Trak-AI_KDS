"""
TRAK-AI Saha Verisi Master İşleyici
=====================================

DB'deki rover_olcumler kayıtlarını tüm model pipeline'larından geçirir:
  1. Anomali tespiti (eksik olanlar için) — orchestrator detect_anomalies()
  2. CP-2 LSTM tarla tahminleri (predict_all_tarlalar.py)
  3. Saha bazlı LLM tavsiyesi (yeni kaynak için)
  4. Foto sınıflandırma (manuel script ayrı çalışır)

Streamlit dashboard açılışında otomatik tetiklenir.

Kullanım:
    python scripts/process_field_data.py
    python scripts/process_field_data.py --skip-lstm          # CP-2 tahmin atla
    python scripts/process_field_data.py --skip-advisory      # LLM advisory atla
    python scripts/process_field_data.py --kaynak gercek_saha_27may2026
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

THIS_DIR    = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
SRC_DIR     = PROJECT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from database import init_db, get_connection             # noqa: E402


# ════════════════════════════════════════════════════════════════════
# Anomali tespiti — detect_anomalies'i orchestrator'dan import
# ════════════════════════════════════════════════════════════════════
def import_orchestrator_anomaly_fn():
    """orchestrator.detect_anomalies'i ve throttle dict'ini import et."""
    try:
        from mqtt_orchestrator import detect_anomalies, _last_anomaly_fire
        return detect_anomalies, _last_anomaly_fire
    except Exception as e:
        print(f"[ANOMALY] orchestrator import HATASI: {e}")
        return None, None


def build_payload_from_record(record: dict) -> dict:
    """rover_olcumler satırı → detect_anomalies() için MQTT payload formatı."""
    payload = {
        "rover_id":     record.get("rover_id") or "trak-ai-rover-01",
        "tarla_id":     record.get("tarla_id") or 1,
        "timestamp":    record.get("timestamp"),
        "gps_lat":      record.get("gps_lat"),
        "gps_lon":      record.get("gps_lon"),
        "nem_1_pct":    record.get("nem_1_pct"),
        "hava_temp_c":  record.get("hava_temp_c"),
        "hava_nem_pct": record.get("hava_nem_pct"),
        "bbch_sinif":   record.get("bbch_sinif") or "BILINMIYOR",
        "bbch_guven":   record.get("bbch_guven") or 0,
    }
    if record.get("nem_2_pct") is not None and record["nem_2_pct"] >= 0:
        payload["nem_2_pct"] = record["nem_2_pct"]
    if record.get("hastalik"):
        payload["hastalik"] = record["hastalik"]
        payload["hastalik_guven"] = record.get("hastalik_guven") or 0
    if record.get("engel_on_cm") is not None and record["engel_on_cm"] >= 0:
        payload["engel_on_cm"] = record["engel_on_cm"]
    return payload


def process_anomalies(kaynak_filter: str | None = None) -> dict:
    """Eksik anomali tespitlerini batch olarak yap."""
    detect_anomalies, throttle_dict = import_orchestrator_anomaly_fn()
    if detect_anomalies is None:
        return {"processed": 0, "skipped": 0, "errors": 1, "anomali_total": 0}

    # Throttling'i geçici devre dışı bırak (batch için)
    if throttle_dict is not None:
        throttle_dict.clear()

    init_db()

    with get_connection() as c:
        # Eksik kayıtlar: anomaliler IS NULL (henüz işlenmemiş)
        q = ("SELECT * FROM rover_olcumler "
             "WHERE anomaliler IS NULL ")
        params: list = []
        if kaynak_filter:
            q += "AND kaynak = ? "
            params.append(kaynak_filter)
        q += "ORDER BY id ASC"
        rows = c.execute(q, params).fetchall()
        records = [dict(r) for r in rows]

    if not records:
        print("[ANOMALY] Eksik kayıt yok — atlandı")
        return {"processed": 0, "skipped": 0, "errors": 0, "anomali_total": 0}

    print(f"[ANOMALY] İşlenecek: {len(records)} kayıt")
    print(f"[ANOMALY] Throttling devre dışı (batch mode)")

    processed = 0
    errors = 0
    total_anomali = 0
    anomali_tipleri: dict[str, int] = {}

    for rec in records:
        # Her kayıt için throttle'ı sıfırla — aynı anomaliler birbirini engellemesin
        if throttle_dict is not None:
            throttle_dict.clear()
        payload = build_payload_from_record(rec)
        try:
            anomalies = detect_anomalies(payload, cp2_result={}, weather=None,
                                          forecast=None)
            n_anom = len(anomalies)
            total_anomali += n_anom
            for a in anomalies:
                anomali_tipleri[a["tip"]] = anomali_tipleri.get(a["tip"], 0) + 1

            anomaliler_str = (json.dumps([a["aciklama"] for a in anomalies],
                                          ensure_ascii=False)
                              if anomalies else None)

            # DB'ye yaz
            with get_connection() as c2:
                c2.execute(
                    "UPDATE rover_olcumler SET anomali_sayisi=?, anomaliler=? "
                    "WHERE id=?",
                    (n_anom, anomaliler_str, rec["id"])
                )
                c2.commit()
            processed += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"[ANOMALY] HATA id={rec['id']}: {e}")

    print(f"[ANOMALY] " + "-" * 40)
    print(f"[ANOMALY] İşlenen: {processed}/{len(records)}, hata: {errors}")
    print(f"[ANOMALY] Toplam tespit edilen anomali: {total_anomali}")
    if anomali_tipleri:
        print(f"[ANOMALY] Tip dağılımı:")
        for tip, n in sorted(anomali_tipleri.items(), key=lambda x: -x[1]):
            print(f"            {n:4d}x  {tip}")

    return {
        "processed": processed,
        "errors": errors,
        "anomali_total": total_anomali,
        "anomali_tipleri": anomali_tipleri,
    }


# ════════════════════════════════════════════════════════════════════
# CP-2 LSTM tahmin (predict_all_tarlalar.py — subprocess)
# ════════════════════════════════════════════════════════════════════
def run_lstm_predictions() -> dict:
    """Frozen LSTM ile tarla tahmin pipeline'ını tetikle."""
    script = PROJECT_DIR / "scripts" / "predict_all_tarlalar.py"
    if not script.exists():
        print(f"[LSTM] Script bulunamadı: {script}")
        return {"ok": False, "reason": "missing_script"}

    print(f"[LSTM] predict_all_tarlalar.py çalıştırılıyor...")
    t0 = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(PROJECT_DIR), capture_output=True, timeout=600,
        )
        dur = time.time() - t0
        if result.returncode == 0:
            print(f"[LSTM] Tamamlandı ({dur:.0f}sn)")
            return {"ok": True, "duration_sec": dur}
        else:
            err = (result.stderr.decode("utf-8", errors="replace")[:300]
                   if result.stderr else "?")
            print(f"[LSTM] Hata kodu {result.returncode}: {err}")
            return {"ok": False, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        print(f"[LSTM] TIMEOUT (10 dakika)")
        return {"ok": False, "reason": "timeout"}
    except Exception as e:
        print(f"[LSTM] Exception: {e}")
        return {"ok": False, "reason": str(e)}


# ════════════════════════════════════════════════════════════════════
# Saha advisory — eksik kaynaklar için
# ════════════════════════════════════════════════════════════════════
def run_field_advisories() -> dict:
    """saha_raporlari'nda eksik kaynaklar için LLM advisory üret."""
    init_db()
    with get_connection() as c:
        all_kaynaks = c.execute(
            "SELECT DISTINCT kaynak FROM rover_olcumler "
            "WHERE kaynak IS NOT NULL "
        ).fetchall()
        existing = c.execute(
            "SELECT DISTINCT kaynak FROM saha_raporlari"
        ).fetchall()

    all_set = {r["kaynak"] for r in all_kaynaks}
    existing_set = {r["kaynak"] for r in existing}
    missing = all_set - existing_set

    if not missing:
        print(f"[ADVISORY] Tüm {len(all_set)} kaynak için LLM tavsiyesi var, atlandı")
        return {"ok": True, "generated": 0, "skipped": len(all_set)}

    print(f"[ADVISORY] {len(missing)} kaynak için LLM tavsiyesi üretilecek")
    script = PROJECT_DIR / "scripts" / "generate_field_advisory.py"
    if not script.exists():
        print(f"[ADVISORY] Script bulunamadı: {script}")
        return {"ok": False}

    generated = 0
    for kaynak in sorted(missing):
        print(f"[ADVISORY] Kaynak: {kaynak} (LLM ~2 dakika)")
        try:
            r = subprocess.run(
                [sys.executable, str(script), "--kaynak", kaynak],
                cwd=str(PROJECT_DIR), capture_output=True, timeout=600,
            )
            if r.returncode == 0:
                generated += 1
                print(f"[ADVISORY]   OK")
            else:
                err = (r.stderr.decode("utf-8", errors="replace")[:200]
                       if r.stderr else "?")
                print(f"[ADVISORY]   HATA: {err}")
        except subprocess.TimeoutExpired:
            print(f"[ADVISORY]   TIMEOUT")
        except Exception as e:
            print(f"[ADVISORY]   Exception: {e}")

    return {"ok": True, "generated": generated, "skipped": len(existing_set)}


# ════════════════════════════════════════════════════════════════════
# Ana akış
# ════════════════════════════════════════════════════════════════════
def main() -> None:
    ap = argparse.ArgumentParser(description="DB'deki saha verisini tüm modellerden geçir")
    ap.add_argument("--kaynak", default=None,
                    help="Sadece bu kaynak için işle (default: hepsi)")
    ap.add_argument("--skip-anomaly", action="store_true",
                    help="Anomali tespitini atla")
    ap.add_argument("--skip-lstm", action="store_true",
                    help="CP-2 LSTM tahminini atla")
    ap.add_argument("--skip-advisory", action="store_true",
                    help="LLM advisory üretimini atla")
    ap.add_argument("--json-output", action="store_true",
                    help="Sonuç özet JSON formatında yaz (dashboard auto-trigger için)")
    args = ap.parse_args()

    print("=" * 60)
    print("  TRAK-AI Saha Verisi Master İşleyici")
    print("=" * 60)
    t0 = time.time()

    summary: dict = {"start_ts": time.time(), "steps": {}}

    # 1. Anomali tespiti
    if args.skip_anomaly:
        print("[STEP 1] Anomali tespiti — atlandı (--skip-anomaly)")
        summary["steps"]["anomaly"] = {"skipped": True}
    else:
        print()
        print("[STEP 1] Anomali tespiti")
        summary["steps"]["anomaly"] = process_anomalies(args.kaynak)

    # 2. CP-2 LSTM tahmin
    if args.skip_lstm:
        print("[STEP 2] CP-2 LSTM — atlandı (--skip-lstm)")
        summary["steps"]["lstm"] = {"skipped": True}
    else:
        print()
        print("[STEP 2] CP-2 LSTM tarla tahminleri")
        summary["steps"]["lstm"] = run_lstm_predictions()

    # 3. LLM advisory
    if args.skip_advisory:
        print("[STEP 3] LLM advisory — atlandı (--skip-advisory)")
        summary["steps"]["advisory"] = {"skipped": True}
    else:
        print()
        print("[STEP 3] LLM advisory (eksik kaynaklar için)")
        summary["steps"]["advisory"] = run_field_advisories()

    total_dur = time.time() - t0
    summary["duration_sec"] = round(total_dur, 1)

    print()
    print("=" * 60)
    print(f"TAMAMLANDI — toplam {total_dur:.0f} saniye")
    print("=" * 60)

    if args.json_output:
        print()
        print("---JSON-OUTPUT-START---")
        print(json.dumps(summary, ensure_ascii=False, default=str))
        print("---JSON-OUTPUT-END---")


if __name__ == "__main__":
    main()
