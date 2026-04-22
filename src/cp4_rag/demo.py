"""
TRAK-AI KDS — Tam Demo: ÇP-2 + ÇP-4 Entegre Sistem
======================================================
Rover olmadan çalışan tam versiyon.
ÇP-2 tahmin modeli + ÇP-4 RAG/LLM birlikte çalışır.
Önce otomatik tarla analizi, sonra interaktif chatbot.

Kullanım: python demo.py
"""
import sys
import os
import time
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src", "cp2_model"))
sys.path.insert(0, os.path.dirname(__file__))

from config import ANOMALY_THRESHOLDS
from build_index import load_faiss_index
from retriever import tri_rag_retrieve, format_context
from llm_engine import query_llm, check_ollama_connection


def print_banner():
    print("\n" + "=" * 60)
    print("  TRAK-AI KDS — Canli Demo")
    print("  Trakya Akilli Tarim Karar Destek Sistemi")
    print("  CP-2 (Tahmin) + CP-4 (RAG/LLM) Entegre Calisma")
    print("  Tamamen Yerel | Internet Gerektirmez")
    print("=" * 60)


def get_cp2_prediction():
    """
    CP-2 inference ciktisini al.
    Once gercek modeli dener, basarisiz olursa simule eder.
    """
    print("\n[CP-2] Tahmin modeli calistiriliyor...")

    try:
        from inference_cp2 import run_inference
        result = run_inference()
        print("[CP-2] Gercek model ciktisi alindi!")
        return result, True
    except Exception as e:
        print(f"[CP-2] Gercek model yuklenemedi: {type(e).__name__}")
        print("[CP-2] Simulasyon modu kullaniliyor...")

    simulated = {
        "bugday": {
            "ndvi_current": 0.4675,
            "ndvi_predicted_t7": 0.4413,
            "trend": "STABLE",
            "trend_pct": -5.6,
            "health": "IYI - Saglikli bitki ortusu",
            "model_type": "Conv-LSTM (residual delta)",
            "last_15d": {
                "precip_mm": 12.3,
                "temp_max": 22.5,
                "temp_min": 8.2,
                "radiation_mj": 18.5,
                "e_sum": -0.12,
            }
        },
        "aycicegi": {
            "ndvi_current": 0.6334,
            "ndvi_predicted_t7": 0.5890,
            "trend": "DUSUS",
            "trend_pct": -7.0,
            "health": "ORTA - Stres belirtileri basliyor",
            "model_type": "LSTM",
            "last_15d": {
                "precip_mm": 3.1,
                "temp_max": 31.2,
                "temp_min": 16.8,
                "radiation_mj": 24.5,
                "e_sum": -0.22,
            }
        }
    }
    return simulated, False


def get_rover_reading():
    """Rover sensor verisini simule et."""
    print("[ROVER] Sensor verisi simule ediliyor...\n")

    return {
        "bugday": {
            "nem": 22,
            "bbch": 65,
            "hastalik": None,
            "guven": 0,
            "ndvi_gozlem": 0.45,
            "ec": 1.4,
        },
        "aycicegi": {
            "nem": 11,
            "bbch": 61,
            "hastalik": "mildiyo",
            "guven": 0.87,
            "ndvi_gozlem": 0.38,
            "ec": 0.9,
        }
    }


def detect_anomalies(cp2_data, rover_data):
    """Model tahmini vs Rover olcumu karsilastir."""
    anomalies = []

    ndvi_fark = abs(cp2_data["ndvi_current"] - rover_data["ndvi_gozlem"])
    if ndvi_fark >= ANOMALY_THRESHOLDS["ndvi_fark_min"]:
        anomalies.append({
            "tip": "NDVI_SAPMA",
            "aciklama": f"Bitki sagligi sapmasi: Model {cp2_data['ndvi_current']:.2f}, "
                        f"Rover {rover_data['ndvi_gozlem']:.2f} olctu (fark: {ndvi_fark:.2f})",
            "seviye": "YUKSEK" if ndvi_fark > 0.20 else "ORTA",
        })

    if rover_data["nem"] < 15:
        anomalies.append({
            "tip": "DUSUK_NEM",
            "aciklama": f"Kritik dusuk toprak nemi: %{rover_data['nem']}",
            "seviye": "KRITIK" if rover_data["nem"] < 10 else "YUKSEK",
        })

    if rover_data["hastalik"] and rover_data["guven"] >= ANOMALY_THRESHOLDS["hastalik_guven_min"]:
        anomalies.append({
            "tip": "HASTALIK",
            "aciklama": f"Hastalik tespit edildi: {rover_data['hastalik']} "
                        f"(guven: %{int(rover_data['guven']*100)})",
            "seviye": "YUKSEK",
        })

    if cp2_data["trend_pct"] < -10:
        anomalies.append({
            "tip": "HIZLI_DUSUS",
            "aciklama": f"7 gunluk tahminde hizli dusus: {cp2_data['trend_pct']}%",
            "seviye": "ORTA",
        })

    return anomalies


def display_field_status(cp2, rover, crop_display, crop_key):
    """Tek bir urunu analiz et ve goster."""
    cd = cp2[crop_key]
    rd = rover[crop_key]

    print(f"\n  {'.' * 56}")
    print(f"  URUN: {crop_display.upper()}")
    print(f"  Model: {cd.get('model_type', 'bilinmiyor')}")
    print(f"  {'.' * 56}")

    print(f"\n  --- CP-2 Model Tahmini (7 gunluk) ---")
    print(f"  Mevcut NDVI       : {cd['ndvi_current']:.4f}")
    print(f"  Tahmini (t+7)     : {cd['ndvi_predicted_t7']:.4f}")
    print(f"  Trend             : {cd['trend']} ({cd['trend_pct']}%)")
    print(f"  Saglik durumu     : {cd['health']}")
    print(f"  Son 15 gun yagis  : {cd['last_15d']['precip_mm']} mm")
    print(f"  Son 15 gun sicaklik: {cd['last_15d']['temp_min']}-{cd['last_15d']['temp_max']} C")
    print(f"  Radyasyon         : {cd['last_15d']['radiation_mj']} MJ/m2")

    print(f"\n  --- Rover Sensor Okumasi ---")
    print(f"  Toprak nemi       : %{rd['nem']}")
    print(f"  BBCH evresi       : {rd['bbch']}")
    print(f"  NDVI gozlem       : {rd['ndvi_gozlem']}")
    print(f"  EC                : {rd['ec']} dS/m")
    print(f"  Hastalik          : {rd['hastalik'] or 'tespit yok'}")
    if rd['hastalik']:
        print(f"  Guven skoru       : %{int(rd['guven']*100)}")

    anomalies = detect_anomalies(cd, rd)

    if not anomalies:
        print(f"\n  SONUC: NORMAL - {crop_display} tarlasi saglıklı gorunuyor.")
        return anomalies

    print(f"\n  !!! {len(anomalies)} ANOMALI TESPIT EDILDI !!!")
    for a in anomalies:
        severity_icon = "!!!" if a["seviye"] == "KRITIK" else "! " if a["seviye"] == "YUKSEK" else "* "
        print(f"  {severity_icon} [{a['seviye']}] {a['aciklama']}")

    return anomalies


def generate_advisory(anomalies, cp2_data, rover_data, crop_display, vectorstore, chunks):
    """Anomali icin RAG tabanli tavsiye uret."""

    anomaly_texts = [a["aciklama"] for a in anomalies]
    search_query = f"{crop_display} {' '.join(anomaly_texts)} Trakya tavsiye sulama hastalik"

    print(f"\n  Bilgi tabaninda araniyor...")
    results = tri_rag_retrieve(search_query, vectorstore, chunks)
    context = format_context(results)

    prompt = f"""TARLA DURUM RAPORU:
Urun: {crop_display}
Konum: Trakya bolgesi (Kirklareli, Vize)
Tarih: {datetime.now().strftime('%d.%m.%Y')}

MODEL TAHMINI:
- Mevcut NDVI: {cp2_data['ndvi_current']}
- 7 gun sonrasi: {cp2_data['ndvi_predicted_t7']}
- Trend: {cp2_data['trend']} ({cp2_data['trend_pct']}%)
- Son 15 gun yagis: {cp2_data['last_15d']['precip_mm']} mm
- Sicaklik araligi: {cp2_data['last_15d']['temp_min']}-{cp2_data['last_15d']['temp_max']} C

ROVER OLCUMU:
- Toprak nemi: %{rover_data['nem']}
- BBCH evresi: {rover_data['bbch']}
- Hastalik: {rover_data['hastalik'] or 'yok'}

TESPIT EDILEN ANOMALILER:
{chr(10).join('- ' + a['aciklama'] for a in anomalies)}

TARIMSAL BILGI KAYNAKLARI:
{context}

Bu verilere ve kaynaklara dayanarak ciftciye kisa ve net Turkce tavsiye ver."""

    print(f"  Yapay zeka tavsiye uretiyor...")
    llm_result = query_llm(prompt)

    print(f"\n  {'=' * 56}")
    print(f"  CIFTCI BILDIRIMI — {crop_display.upper()}")
    print(f"  {'=' * 56}")
    print(f"\n  {llm_result['answer']}")
    print(f"\n  Sure: {llm_result['duration_sec']}sn | Kaynaklar: ", end="")
    print(", ".join(r['metadata'].get('source', '?')[:30] for r in results))

    return results


def interactive_chat(cp2, rover, vectorstore, chunks, crops):
    """Interaktif chatbot modu."""
    print(f"\n{'=' * 60}")
    print(f"  TRAK-AI Tarim Danismani — Soru-Cevap Modu")
    print(f"  Tarimla ilgili istediginiz soruyu sorun.")
    print(f"")
    print(f"  Ozel komutlar:")
    print(f"    durum   -> Tarla durumunu goster")
    print(f"    analiz  -> Anomali analizini tekrar calistir")
    print(f"    q       -> Cikis")
    print(f"{'=' * 60}")

    while True:
        print()
        try:
            user_input = input("  Siz: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cikiliyor...")
            break

        if not user_input:
            continue

        if user_input.lower() in ["q", "quit", "cik", "exit", "cikis"]:
            print("\n  Iyi hasat dilerim!")
            break

# Ozel komut: durum — LLM ile dogal dilde tarla ozeti
        if user_input.lower() in ["durum", "tarla", "tarla durumu", "ozet"]:
            durum_text = f"""TARLA VERILERI:

BUGDAY TARLASI:
- Bitki sagligi (NDVI): {cp2['bugday']['ndvi_current']:.2f} (7 gun sonra tahmini: {cp2['bugday']['ndvi_predicted_t7']:.2f})
- Trend: {cp2['bugday']['trend']} ({cp2['bugday']['trend_pct']}%)
- Toprak nemi: %{rover['bugday']['nem']}
- Buyume evresi (BBCH): {rover['bugday']['bbch']}
- Hastalik: {rover['bugday']['hastalik'] or 'tespit yok'}
- Son 15 gun yagis: {cp2['bugday']['last_15d']['precip_mm']} mm
- Sicaklik: {cp2['bugday']['last_15d']['temp_min']}-{cp2['bugday']['last_15d']['temp_max']} C

AYCICEGI TARLASI:
- Bitki sagligi (NDVI): {cp2['aycicegi']['ndvi_current']:.2f} (7 gun sonra tahmini: {cp2['aycicegi']['ndvi_predicted_t7']:.2f})
- Trend: {cp2['aycicegi']['trend']} ({cp2['aycicegi']['trend_pct']}%)
- Toprak nemi: %{rover['aycicegi']['nem']}
- Buyume evresi (BBCH): {rover['aycicegi']['bbch']}
- Hastalik: {rover['aycicegi']['hastalik'] or 'tespit yok'}
- Son 15 gun yagis: {cp2['aycicegi']['last_15d']['precip_mm']} mm
- Sicaklik: {cp2['aycicegi']['last_15d']['temp_min']}-{cp2['aycicegi']['last_15d']['temp_max']} C

Konum: Trakya, Kirklareli Vize | Tarih: {datetime.now().strftime('%d.%m.%Y')}"""

            prompt = f"""{durum_text}

Yukaridaki verilere bakarak ciftciye tarlalarinin genel durumunu anlat.
Teknik terim kullanma, komsusuna anlatir gibi yaz.
Iyi olan seyleri de soyle, sorunlu olan seyleri de belirt.
Kisa ve anlasilir tut."""

            print(f"\n  Dusunuyor...")
            llm_result = query_llm(prompt)
            print(f"\n  TRAK-AI: {llm_result['answer']}")
            print(f"\n  ({llm_result['duration_sec']}sn)")
            continue

        # Ozel komut: analiz — LLM ile ne yapilmasi gerektigini anlat
        if user_input.lower() in ["analiz", "anomali", "kontrol", "ne yapmaliyim"]:
            all_anomalies = []
            anomaly_details = ""
            for crop_display, crop_key in crops:
                cd = cp2[crop_key]
                rd = rover[crop_key]
                anomalies = detect_anomalies(cd, rd)
                if anomalies:
                    all_anomalies.extend(anomalies)
                    anomaly_details += f"\n{crop_display}:\n"
                    for a in anomalies:
                        anomaly_details += f"  - [{a['seviye']}] {a['aciklama']}\n"

            if not all_anomalies:
                print("\n  TRAK-AI: Tarlalarinizda su an bir sorun gorunmuyor. Her sey yolunda!")
                continue

            search_query = " ".join([a["aciklama"] for a in all_anomalies]) + " Trakya tavsiye"
            print(f"\n  Bilgi tabaninda araniyor...")
            results = tri_rag_retrieve(search_query, vectorstore, chunks)
            context = format_context(results)

            prompt = f"""TESPIT EDILEN SORUNLAR:
{anomaly_details}

TARLA BILGILERI:
Bugday: Nem %{rover['bugday']['nem']}, BBCH {rover['bugday']['bbch']}
Aycicegi: Nem %{rover['aycicegi']['nem']}, BBCH {rover['aycicegi']['bbch']}, Hastalik: {rover['aycicegi']['hastalik'] or 'yok'}
Konum: Trakya | Tarih: {datetime.now().strftime('%d.%m.%Y')}

TARIMSAL BILGI KAYNAKLARI:
{context}

Yukaridaki sorunlara ve kaynaklara dayanarak ciftciye ne yapmasi gerektigini anlat.
Her sorun icin ayri ayri madde halinde yaz.
Oncelik sirasina gore sirala - en acil olan en basta.
Ne zaman, ne kadar, nasil yapilacagini somut olarak belirt."""

            print(f"  Dusunuyor...")
            llm_result = query_llm(prompt)
            print(f"\n  TRAK-AI: {llm_result['answer']}")
            print(f"\n  ({llm_result['duration_sec']}sn | ", end="")
            src_names = [r['metadata'].get('source', '?')[:25] for r in results]
            print("Kaynaklar: " + ", ".join(src_names) + ")")
            continue

        # Normal RAG sorgusu
        print(f"\n  Bilgi tabaninda araniyor...")
        results = tri_rag_retrieve(user_input, vectorstore, chunks)
        context = format_context(results)

        field_summary = f"""MEVCUT TARLA BILGISI:
Bugday: NDVI {cp2['bugday']['ndvi_current']:.2f}, Nem %{rover['bugday']['nem']}, BBCH {rover['bugday']['bbch']}, Hastalik: {rover['bugday']['hastalik'] or 'yok'}
Aycicegi: NDVI {cp2['aycicegi']['ndvi_current']:.2f}, Nem %{rover['aycicegi']['nem']}, BBCH {rover['aycicegi']['bbch']}, Hastalik: {rover['aycicegi']['hastalik'] or 'yok'}
Konum: Trakya (Kirklareli, Vize) | Tarih: {datetime.now().strftime('%d.%m.%Y')}"""

        prompt = f"""{field_summary}

CIFTCININ SORUSU: {user_input}

KAYNAK BELGELER:
{context}

Yukaridaki tarla bilgilerine ve kaynak belgelere dayanarak ciftcinin sorusunu yanitla."""

        print(f"  Dusunuyor...")
        llm_result = query_llm(prompt)

        print(f"\n  TRAK-AI: {llm_result['answer']}")
        print(f"\n  ({llm_result['duration_sec']}sn | ", end="")
        src_names = [r['metadata'].get('source', '?')[:25] for r in results]
        print("Kaynaklar: " + ", ".join(src_names) + ")")


def run_demo():
    """Ana demo akisi."""
    print_banner()

    # 1. Sistem kontrolu
    print("\n[SISTEM] Bilesenler kontrol ediliyor...")
    if not check_ollama_connection():
        return

    # 2. FAISS yukle
    print("[SISTEM] Bilgi tabani yukleniyor...")
    vectorstore, chunks = load_faiss_index()
    if vectorstore is None:
        return

    # 3. CP-2 tahmin al
    cp2, is_real = get_cp2_prediction()
    mode = "GERCEK MODEL" if is_real else "SIMULASYON"
    print(f"[CP-2] Mod: {mode}")

    # 4. Rover okumasi
    rover = get_rover_reading()

    # 5. Urun listesi
    crops = [
        ("Bugday", "bugday"),
        ("Aycicegi", "aycicegi"),
    ]

    # 6. Otomatik tarla analizi
    print(f"\n{'=' * 60}")
    print(f"  OTOMATIK TARLA ANALIZI BASLIYOR")
    print(f"  Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"  Konum: Trakya — Kirklareli, Vize, Evrenli")
    print(f"{'=' * 60}")

    for crop_display, crop_key in crops:
        cd = cp2[crop_key]
        rd = rover[crop_key]
        anomalies = display_field_status(cp2, rover, crop_display, crop_key)

        if anomalies:
            generate_advisory(anomalies, cd, rd, crop_display, vectorstore, chunks)

    # 7. Chatbot modu
    interactive_chat(cp2, rover, vectorstore, chunks, crops)

    # Final
    print(f"\n{'=' * 60}")
    print(f"  TRAK-AI KDS v1.0")
    print(f"  Tamamen Yerel | Internet Gerektirmez | {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    run_demo()