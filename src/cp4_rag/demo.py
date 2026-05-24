"""
TRAK-AI KDS — Tam Demo: CP-2 + CP-4 Entegre Sistem
======================================================
CP-2 tahmin modelini gercek calistirip, sonuclari CP-4 RAG/LLM
ile birlestirerek Turkce ciftci tavsiyesi uretir.
Rover verisi mock (CP-3 tamamlanana kadar).

Kullanim: python demo.py
"""
import sys
import os
import time
from datetime import datetime

# Path ayarlari
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CP2_DIR = os.path.join(PROJECT_ROOT, "src", "cp2_model")
sys.path.insert(0, CP2_DIR)
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
    CP-2 inference_cp2.py'nin predict() fonksiyonunu cagir.
    Basarisiz olursa simulasyon kullan.
    """
    print("\n[CP-2] Tahmin modeli calistiriliyor...")

    try:
        from inference_cp2 import predict, get_field_summary

        field_summary = get_field_summary()
        wheat_result = predict("Wheat", field_summary=field_summary)
        sunflower_result = predict("Sunflower", field_summary=field_summary)

        print("[CP-2] GERCEK MODEL ciktisi alindi!")
        print(f"  Bugday:    NDVI {wheat_result['current_ndvi']:.4f} -> "
              f"{wheat_result['predicted_ndvi']:.4f} (t+7) [{wheat_result['architecture']}]")
        print(f"  Aycicegi:  NDVI {sunflower_result['current_ndvi']:.4f} -> "
              f"{sunflower_result['predicted_ndvi']:.4f} (t+7) [{sunflower_result['architecture']}]")

        cp2 = {
            "bugday": {
                "ndvi_current": wheat_result["current_ndvi"],
                "ndvi_predicted_t7": wheat_result["predicted_ndvi"],
                "trend": wheat_result["trend"]["trend"],
                "trend_pct": wheat_result["trend"]["pct_change"],
                "health": f"{wheat_result['health']['status']} - {wheat_result['health']['desc']}",
                "alert": wheat_result["trend"]["alert"],
                "action": wheat_result["health"]["action"],
                "model_type": wheat_result["architecture"],
                "field_summary": wheat_result["field_summary"],
                "llm_context": wheat_result["llm_context"],
            },
            "aycicegi": {
                "ndvi_current": sunflower_result["current_ndvi"],
                "ndvi_predicted_t7": sunflower_result["predicted_ndvi"],
                "trend": sunflower_result["trend"]["trend"],
                "trend_pct": sunflower_result["trend"]["pct_change"],
                "health": f"{sunflower_result['health']['status']} - {sunflower_result['health']['desc']}",
                "alert": sunflower_result["trend"]["alert"],
                "action": sunflower_result["health"]["action"],
                "model_type": sunflower_result["architecture"],
                "field_summary": sunflower_result["field_summary"],
                "llm_context": sunflower_result["llm_context"],
            },
        }

        # ─── ÇP-2.5 v2 Verim Tahmini Köprüsü ────────────────────────
        try:
            from inference_cp2 import predict_yield_kg_da
            for crop_key, crop_name, il_default, ilce_default in [
                ("bugday",   "Wheat",     "Kırklareli", 1505),  # Lüleburgaz
                ("aycicegi", "Sunflower", "Tekirdağ",   1258),  # Çorlu
            ]:
                try:
                    y = predict_yield_kg_da(
                        crop_type=crop_name,
                        ndvi_predicted=cp2[crop_key]["ndvi_predicted_t7"],
                        il=il_default, ilce_id=ilce_default,
                    )
                    cp2[crop_key]["yield_kg_da"]    = y["yield_kg_da"]
                    cp2[crop_key]["yield_pi_lower"] = y["yield_kg_da_lower"]
                    cp2[crop_key]["yield_pi_upper"] = y["yield_kg_da_upper"]
                    cp2[crop_key]["lokal_22yil_ortalama"] = y["lokal_22yil_ortalama"]
                    cp2[crop_key]["sapma_pct"]     = y["sapma_pct"]
                    cp2[crop_key]["sapma_yorum"]   = y["sapma_yorum"]
                    cp2[crop_key]["top_3_features"]= y["top_3_features"]
                    cp2[crop_key]["cp25_model"]    = y["champion_model"]
                    cp2[crop_key]["cp25_layer"]    = y["layer"]
                    print(f"[CP-2.5] {crop_name:9s} → {y['yield_kg_da']:.0f} kg/da  "
                          f"(PI95: {y['yield_kg_da_lower']:.0f}-{y['yield_kg_da_upper']:.0f})  "
                          f"sapma %{y['sapma_pct']:+.1f}  ({y['sapma_yorum']})  "
                          f"[Layer {y['layer']}/{y['champion_model']}]")
                except Exception as _exc:
                    print(f"[CP-2.5] {crop_name} verim tahmini hatasi: {_exc}")
        except ImportError:
            print("[CP-2.5] predict_yield_kg_da modulu yok — verim tahmini atlandi")

        return cp2, True

    except Exception as e:
        print(f"[CP-2] Model yuklenemedi: {e}")
        print("[CP-2] Simulasyon modu kullaniliyor...")

        return {
            "bugday": {
                "ndvi_current": 0.4675,
                "ndvi_predicted_t7": 0.4413,
                "trend": "STABLE",
                "trend_pct": -5.6,
                "health": "FAIR - Acceptable vegetation health",
                "alert": "Minor decline expected, monitor conditions",
                "action": "Continue standard management",
                "model_type": "Conv-LSTM (simulasyon)",
                "field_summary": "Last 15 Days: Precip=12.3mm, Max Temp=22.5C, Min Temp=8.2C",
                "llm_context": "Simulasyon verisi",
            },
            "aycicegi": {
                "ndvi_current": 0.6334,
                "ndvi_predicted_t7": 0.5890,
                "trend": "SLIGHT_DECLINE",
                "trend_pct": -7.0,
                "health": "GOOD - Healthy vegetation cover",
                "alert": "Minor decline expected, monitor conditions",
                "action": "Maintain current practices",
                "model_type": "LSTM (simulasyon)",
                "field_summary": "Last 15 Days: Precip=3.1mm, Max Temp=31.2C, Min Temp=16.8C",
                "llm_context": "Simulasyon verisi",
            },
        }, False


def get_rover_reading():
    """
    Rover sensor verisi — MOCK.
    CP-3 tamamlaninca burasi gercek MQTT verisine baglanacak.
    """
    print("[ROVER] Mock sensor verisi yukleniyor (CP-3 bekliyor)...\n")

    return {
        "bugday": {
            "nem": 22,
            "bbch": 65,
            "hastalik": None,
            "guven": 0,
            "ndvi_gozlem": 0.45,
        },
        "aycicegi": {
            "nem": 11,
            "bbch": 61,
            "hastalik": "mildiyo",
            "guven": 0.87,
            "ndvi_gozlem": 0.38,
        },
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
                        f"(guven: %{int(rover_data['guven'] * 100)})",
            "seviye": "YUKSEK",
        })

    return anomalies


def display_field_status(cp2_data, rover_data, crop_display):
    """Tek bir urun icin tarla durumunu goster."""
    cd = cp2_data
    rd = rover_data

    print(f"\n  {'.' * 56}")
    print(f"  URUN: {crop_display.upper()}")
    print(f"  Model: {cd['model_type']}")
    print(f"  {'.' * 56}")

    print(f"\n  --- CP-2 Tahmin ---")
    print(f"  Mevcut NDVI       : {cd['ndvi_current']:.4f}")
    print(f"  Tahmini (t+7)     : {cd['ndvi_predicted_t7']:.4f}")
    print(f"  Trend             : {cd['trend']} ({cd['trend_pct']}%)")
    print(f"  Durum             : {cd['health']}")
    print(f"  Uyari             : {cd['alert']}")
    print(f"  {cd['field_summary']}")

    print(f"\n  --- Rover Olcumu (mock) ---")
    print(f"  Toprak nemi       : %{rd['nem']}")
    print(f"  BBCH evresi       : {rd['bbch']}")
    print(f"  NDVI gozlem       : {rd['ndvi_gozlem']}")
    print(f"  Hastalik          : {rd['hastalik'] or 'tespit yok'}")
    if rd["hastalik"]:
        print(f"  Guven skoru       : %{int(rd['guven'] * 100)}")

    anomalies = detect_anomalies(cd, rd)

    if not anomalies:
        print(f"\n  SONUC: NORMAL — {crop_display} tarlasi saglikli gorunuyor.")
    else:
        print(f"\n  !!! {len(anomalies)} ANOMALI TESPIT EDILDI !!!")
        for a in anomalies:
            icon = "!!!" if a["seviye"] == "KRITIK" else "! " if a["seviye"] == "YUKSEK" else "* "
            print(f"  {icon} [{a['seviye']}] {a['aciklama']}")

    return anomalies


def generate_advisory(anomalies, cp2_data, rover_data, crop_display, vectorstore, chunks):
    """Anomali icin RAG tabanli tavsiye uret."""
    anomaly_texts = [a["aciklama"] for a in anomalies]
    search_query = f"{crop_display} {' '.join(anomaly_texts)} Trakya tavsiye"

    print(f"\n  Bilgi tabaninda araniyor...")
    results = tri_rag_retrieve(search_query, vectorstore, chunks)
    context = format_context(results)

    prompt = f"""TARLA DURUM RAPORU:
Urun: {crop_display}
Konum: Trakya bolgesi (Kirklareli, Vize)
Tarih: {datetime.now().strftime('%d.%m.%Y')}

MODEL TAHMINI (CP-2 {cp2_data['model_type']}):
{cp2_data['llm_context']}

ROVER OLCUMU:
- Toprak nemi: %{rover_data['nem']}
- BBCH evresi: {rover_data['bbch']}
- Hastalik: {rover_data['hastalik'] or 'yok'}

TESPIT EDILEN ANOMALILER:
{chr(10).join('- ' + a['aciklama'] for a in anomalies)}

TARIMSAL BILGI KAYNAKLARI:
{context}

Bu verilere ve kaynaklara dayanarak ciftciye kisa ve net Turkce tavsiye ver.
En acil sorundan basla."""

    print(f"  Yapay zeka tavsiye uretiyor...")
    llm_result = query_llm(prompt)

    print(f"\n  {'=' * 56}")
    print(f"  CIFTCI BILDIRIMI — {crop_display.upper()}")
    print(f"  {'=' * 56}")
    print(f"\n  {llm_result['answer']}")
    print(f"\n  Sure: {llm_result['duration_sec']}sn | Kaynaklar: ", end="")
    print(", ".join(r["metadata"].get("source", "?")[:30] for r in results))

    return results


def interactive_chat(cp2, rover, vectorstore, chunks, crops):
    """Interaktif chatbot modu."""
    print(f"\n{'=' * 60}")
    print(f"  TRAK-AI Tarim Danismani — Soru-Cevap Modu")
    print(f"  Tarimla ilgili istediginiz soruyu sorun.")
    print(f"")
    print(f"  Ozel komutlar:")
    print(f"    durum    -> Tarla durumunu dogal dilde anlat")
    print(f"    analiz   -> Anomali tespiti ve tavsiye uret")
    print(f"    q        -> Cikis")
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

        # DURUM — LLM ile dogal dilde tarla ozeti
        if user_input.lower() in ["durum", "tarla", "tarla durumu", "ozet"]:
            durum_text = f"""TARLA VERILERI:

BUGDAY TARLASI:
- Bitki sagligi (NDVI): {cp2['bugday']['ndvi_current']:.4f}
- 7 gun sonrasi tahmini: {cp2['bugday']['ndvi_predicted_t7']:.4f}
- Trend: {cp2['bugday']['trend']} ({cp2['bugday']['trend_pct']}%)
- Durum: {cp2['bugday']['health']}
- Toprak nemi: %{rover['bugday']['nem']}
- BBCH evresi: {rover['bugday']['bbch']}
- Hastalik: {rover['bugday']['hastalik'] or 'tespit yok'}
- {cp2['bugday']['field_summary']}

AYCICEGI TARLASI:
- Bitki sagligi (NDVI): {cp2['aycicegi']['ndvi_current']:.4f}
- 7 gun sonrasi tahmini: {cp2['aycicegi']['ndvi_predicted_t7']:.4f}
- Trend: {cp2['aycicegi']['trend']} ({cp2['aycicegi']['trend_pct']}%)
- Durum: {cp2['aycicegi']['health']}
- Toprak nemi: %{rover['aycicegi']['nem']}
- BBCH evresi: {rover['aycicegi']['bbch']}
- Hastalik: {rover['aycicegi']['hastalik'] or 'tespit yok'}
- {cp2['aycicegi']['field_summary']}

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

        # ANALIZ — anomali tespiti + RAG tavsiye
        if user_input.lower() in ["analiz", "anomali", "kontrol", "ne yapmaliyim"]:
            has_anomaly = False
            for crop_display, crop_key in crops:
                cd = cp2[crop_key]
                rd = rover[crop_key]
                anomalies = detect_anomalies(cd, rd)
                if anomalies:
                    has_anomaly = True
                    print(f"\n  {crop_display.upper()} — {len(anomalies)} anomali:")
                    for a in anomalies:
                        print(f"    [{a['seviye']}] {a['aciklama']}")

                    search_query = f"{crop_display} {' '.join(a['aciklama'] for a in anomalies)} Trakya"
                    print(f"\n  Bilgi tabaninda araniyor...")
                    results = tri_rag_retrieve(search_query, vectorstore, chunks)
                    context = format_context(results)

                    prompt = f"""TESPIT EDILEN SORUNLAR ({crop_display}):
{chr(10).join('- ' + a['aciklama'] for a in anomalies)}

TARLA: Nem %{rd['nem']}, BBCH {rd['bbch']}, Hastalik: {rd['hastalik'] or 'yok'}
Konum: Trakya | Tarih: {datetime.now().strftime('%d.%m.%Y')}

KAYNAKLAR:
{context}

Bu sorunlara dayanarak ciftciye ne yapmasi gerektigini anlat.
Her sorun icin ayri madde yaz. En acil olan en basta.
Ne zaman, ne kadar, nasil yapilacagini somut belirt."""

                    print(f"  Dusunuyor...")
                    llm_result = query_llm(prompt)
                    print(f"\n  TRAK-AI: {llm_result['answer']}")
                    print(f"\n  ({llm_result['duration_sec']}sn | ", end="")
                    print("Kaynaklar: " + ", ".join(r["metadata"].get("source", "?")[:25] for r in results) + ")")

            if not has_anomaly:
                print("\n  TRAK-AI: Tarlalarinizda su an bir sorun gorunmuyor. Her sey yolunda!")
            continue

        # SERBEST SORU — RAG + tarla verisi
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
        print("Kaynaklar: " + ", ".join(r["metadata"].get("source", "?")[:25] for r in results) + ")")


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

    # 3. CP-2 tahmin al (gercek model veya simulasyon)
    cp2, is_real = get_cp2_prediction()
    mode = "GERCEK MODEL" if is_real else "SIMULASYON"
    print(f"[CP-2] Mod: {mode}")

    # 4. Rover okumasi (mock — CP-3 bekleniyor)
    rover = get_rover_reading()

    # 5. Urun listesi
    crops = [
        ("Bugday", "bugday"),
        ("Aycicegi", "aycicegi"),
    ]

    # 6. Otomatik tarla analizi
    print(f"\n{'=' * 60}")
    print(f"  OTOMATIK TARLA ANALIZI")
    print(f"  Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"  Konum: Trakya — Kirklareli, Vize, Evrenli")
    print(f"  CP-2 Mod: {mode}")
    print(f"  Rover: Mock (CP-3 bekleniyor)")
    print(f"{'=' * 60}")

    for crop_display, crop_key in crops:
        cd = cp2[crop_key]
        rd = rover[crop_key]
        anomalies = display_field_status(cd, rd, crop_display)

        if anomalies:
            generate_advisory(anomalies, cd, rd, crop_display, vectorstore, chunks)

    # 7. Chatbot modu
    interactive_chat(cp2, rover, vectorstore, chunks, crops)

    # Final
    print(f"\n{'=' * 60}")
    print(f"  TRAK-AI KDS v1.0")
    print(f"  Tamamen Yerel | Internet Gerektirmez")
    print(f"  {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    run_demo()