"""
TRAK-AI KDS — Ollama LLM Motoru
=================================
Bu modül şunları yapar:
1. Ollama'da çalışan yerel LLM'e (Llama-3-8B) bağlanır
2. Tri-RAG'dan gelen bağlam + soruyu birleştirip prompt oluşturur
3. LLM'den Türkçe tavsiye alır
4. Yanıt süresini ve token sayısını loglar

Tamamen offline çalışır — internet gerekmez.
Tek gereksinim: arka planda "ollama serve" çalışıyor olması.
"""
import time
import requests

from config import (
    OLLAMA_BASE_URL, OLLAMA_MODEL,
    LLM_TEMPERATURE, LLM_NUM_CTX,
    SYSTEM_PROMPT,
)


def check_ollama_connection() -> bool:
    """Ollama sunucusunun çalışıp çalışmadığını kontrol et."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            if models:
                print(f"  Ollama bağlantısı OK. Yüklü modeller: {', '.join(models)}")
            else:
                print(f"  Ollama çalışıyor ama model yüklü değil!")
                print(f"  Terminalde çalıştır: ollama pull {OLLAMA_MODEL}")
            return True
        return False
    except requests.exceptions.ConnectionError:
        print("[HATA] Ollama'ya bağlanılamadı!")
        print("Çözüm: Ayrı bir terminal aç ve şunu çalıştır:")
        print("  ollama serve")
        return False


def query_llm(prompt: str, system_prompt: str = None) -> dict:
    """
    Ollama API üzerinden yerel LLM'e soru gönder.
    
    Args:
        prompt: Ana soru/bağlam metni
        system_prompt: LLM'in rolünü tanımlayan sistem mesajı
                       (None ise config'deki SYSTEM_PROMPT kullanılır)
    
    Returns:
        dict: {"answer": "yanıt", "duration_sec": 12.3, "tokens": 150}
    """
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT
    
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": LLM_TEMPERATURE,
            "num_ctx": LLM_NUM_CTX,
        },
    }
    
    print(f"\n  LLM'e sorgu gönderiliyor ({OLLAMA_MODEL})...")
    print(f"  (CPU modda 30-90 sn sürebilir, bekle...)")
    t0 = time.time()
    
    try:
        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()
        result = resp.json()
        elapsed = time.time() - t0
        
        answer = result.get("response", "").strip()
        eval_count = result.get("eval_count", 0)
        
        print(f"  Yanıt alındı! ({elapsed:.1f} sn, {eval_count} token)")
        
        return {
            "answer": answer,
            "duration_sec": round(elapsed, 1),
            "tokens": eval_count,
            "model": OLLAMA_MODEL,
        }
        
    except requests.exceptions.ConnectionError:
        return {
            "answer": "[HATA] Ollama bağlantısı yok. 'ollama serve' çalıştır.",
            "duration_sec": 0,
            "tokens": 0,
            "model": OLLAMA_MODEL,
        }
    except requests.exceptions.Timeout:
        return {
            "answer": "[HATA] LLM yanıt süresi 5 dakikayı aştı. Daha küçük model dene.",
            "duration_sec": 300,
            "tokens": 0,
            "model": OLLAMA_MODEL,
        }
    except Exception as e:
        # Hata detayını göster
        error_detail = str(e)
        try:
            error_detail = resp.text
        except:
            pass
        return {
            "answer": f"[HATA] {error_detail}",
            "duration_sec": 0,
            "tokens": 0,
            "model": OLLAMA_MODEL,
        }


def build_rich_context() -> str:
    """
    Tüm sistemden güncel veri toplayıp LLM bağlam metni oluşturur.

    CP-2 model tahminleri + Open-Meteo hava durumu + agronomik takvim
    + statik toprak profili tek bir metin bloğuna birleştirilir.
    Her kaynak try/except ile korunur — bir kaynak başarısız olursa devam eder.
    """
    import sys
    import os
    import gc

    _this_dir = os.path.dirname(os.path.abspath(__file__))
    _src_dir = os.path.dirname(_this_dir)
    _cp2_dir = os.path.join(_src_dir, "cp2_model")
    for d in [_src_dir, _cp2_dir]:
        if d not in sys.path:
            sys.path.insert(0, d)

    parts = []

    # 1. CP-2 Model Tahminleri
    try:
        from inference_cp2 import predict
        wheat = predict("Wheat")
        gc.collect()
        sunflower = predict("Sunflower")
        gc.collect()

        lines = ["TARLA TAHMİN VERİLERİ (ConvLSTM/LSTM Model):"]
        for label, r in [("Buğday", wheat), ("Ayçiçeği", sunflower)]:
            cur  = r.get("current_ndvi", 0)
            pred = r.get("predicted_ndvi", 0)
            t    = r.get("trend", {})
            h    = r.get("health", {})
            lines.append(
                f"- {label}: Mevcut bitki sağlık endeksi={cur:.4f}, "
                f"7 günlük tahmin={pred:.4f}, "
                f"Değişim={t.get('delta', 0):+.4f} (%{t.get('pct_change', 0):+.1f}), "
                f"Durum={h.get('status','?')} — {h.get('desc','')}"
            )
        lines.append(
            "(Sağlık endeksi: <0.25=KRİTİK, 0.25-0.40=ZAYIF, "
            "0.40-0.55=ORTA, 0.55-0.70=İYİ, >0.70=MÜKEMMEL)"
        )
        parts.append("\n".join(lines))
    except Exception as e:
        parts.append(f"[Model tahmini alınamadı: {e}]")

    # 2. Anlık hava ve 7 günlük tahmin
    try:
        from weather_service import get_current_weather, get_7day_forecast, get_weather_alerts
        weather  = get_current_weather()
        forecast = get_7day_forecast()

        if weather:
            parts.append(
                "ANLIK HAVA DURUMU (Open-Meteo, Kırklareli-Vize):\n"
                f"- Hava sıcaklığı: {weather.get('temp_c','?')}°C\n"
                f"- Hava nemi: %{weather.get('humidity','?')}\n"
                f"- Toprak sıcaklığı (yüzey): {weather.get('soil_temp_c','?')}°C\n"
                f"- Toprak nemi: %{weather.get('soil_moisture','?')}\n"
                f"- Yağış: {weather.get('precipitation_mm',0)} mm\n"
                f"- Rüzgar: {weather.get('wind_kmh','?')} km/h"
            )

        if forecast:
            fc_lines = ["7 GÜNLÜK HAVA TAHMİNİ:"]
            for day in forecast[:7]:
                fc_lines.append(
                    f"  {day.get('date','')}: "
                    f"{day.get('temp_min','')}–{day.get('temp_max','')}°C, "
                    f"Yağış: {day.get('precip_mm',0)}mm "
                    f"(%{day.get('precip_prob',0)} ihtimal)"
                )
            parts.append("\n".join(fc_lines))

        alerts = get_weather_alerts(forecast) if forecast else []
        if alerts:
            texts = [a["text"] if isinstance(a, dict) else str(a) for a in alerts]
            parts.append("HAVA UYARILARI: " + " | ".join(texts))
    except Exception as e:
        parts.append(f"[Hava verisi alınamadı: {e}]")

    # 3. Agronomik takvim
    try:
        from agro_calendar import (
            get_current_phenology, get_irrigation_advice, get_fertilization_advice,
        )
        from datetime import datetime
        month = datetime.now().month

        agro_lines = [f"AGRONOMİK TAKVİM (Trakya, Ay {month}):"]
        for crop_label, crop_key in [("Buğday", "Wheat"), ("Ayçiçeği", "Sunflower")]:
            p = get_current_phenology(crop_key, month)
            kritik = "EVET — DİKKAT!" if p.get("kritik_mi") else "Hayır"
            agro_lines.append(
                f"- {crop_label}: {p.get('aciklama','')} "
                f"(BBCH {p.get('bbch_aralik','?')}), Kritik dönem: {kritik}"
            )

        soil_m = 25.0
        try:
            from weather_service import get_current_weather as _gcw
            _w = _gcw()
            if _w:
                soil_m = _w.get("soil_moisture", 25.0)
        except Exception:
            pass

        agro_lines.append("SULAMA DURUMU:")
        for crop_label, crop_key in [("Buğday", "Wheat"), ("Ayçiçeği", "Sunflower")]:
            irr = get_irrigation_advice(crop_key, month, soil_m)
            agro_lines.append(
                f"  - {crop_label}: {irr.get('aciliyet','?')} — {irr.get('gerekce','')}"
            )

        fert_lines = []
        for crop_label, crop_key in [("Buğday", "Wheat"), ("Ayçiçeği", "Sunflower")]:
            f_ = get_fertilization_advice(crop_key, month)
            if f_.get("gubre_zamani"):
                fert_lines.append(
                    f"  - {crop_label}: EVET — {f_.get('tip','')}, {f_.get('doz','')}"
                )
        if fert_lines:
            agro_lines.append("GÜBRELEME:")
            agro_lines.extend(fert_lines)

        parts.append("\n".join(agro_lines))
    except Exception as e:
        parts.append(f"[Agronomik takvim alınamadı: {e}]")

    # 4. Toprak profili (statik — SoilGrids 2.0, Kırklareli-Vize)
    parts.append(
        "TOPRAK PROFİLİ (SoilGrids 2.0, Kırklareli-Vize):\n"
        "- Kil: %30.97, Kum: %34.99, Silt: %34.04\n"
        "- pH: 7.11 (nötr)\n"
        "- Toprak tipi: Killi-tınlı (clay-loam)\n"
        "- Su tutma kapasitesi: Orta-yüksek"
    )

    return "\n\n".join(parts)


def rag_query(query: str, context: str, rich_context: str = None) -> dict:
    """
    RAG sorgusu: (isteğe bağlı zengin bağlam +) RAG belgeleri + soru → LLM → Türkçe yanıt.

    Args:
        query: Kullanıcının sorusu
        context: format_context()'den gelen kaynak metin
        rich_context: build_rich_context()'den gelen güncel tarla verileri (None ise atlanır)

    Returns:
        dict: {"answer": "...", "duration_sec": ..., "tokens": ...}
    """
    rich_block = (
        "Aşağıda tarla hakkında güncel veriler var. Bu verileri MUTLAKA kullanarak yanıt ver:\n\n"
        f"{rich_context}\n\n"
    ) if rich_context else ""

    full_prompt = (
        f"{rich_block}"
        f"RAG'dan getirilen tarımsal belgeler:\n{context}\n\n"
        f"Çiftçinin sorusu: {query}\n\n"
        "Yukarıdaki TÜM verileri analiz ederek somut, rakamsal, "
        "eyleme dönüştürülebilir Türkçe tavsiye ver."
    )

    return query_llm(full_prompt)


def rover_alert_query(
    anomaly_context: str,
    field_context: str,
    weather_context: str = None,
    agro_context: str = None,
) -> dict:
    """
    Rover anomali senaryosu için özel prompt.

    ÇP-2 inference çıktısı + Rover sensör verisi + RAG belgesi +
    (isteğe bağlı) hava durumu + (isteğe bağlı) agronomik takvim
    birleştirilip LLM'e gönderilir.

    Args:
        anomaly_context: Anomali açıklaması (nem farkı, hastalık vb.)
        field_context: RAG'dan gelen ilgili belge parçaları
        weather_context: Open-Meteo hava durumu özeti (None ise atlanır)
        agro_context: Agronomik takvim ve ekim/sulama/gübre durumu (None ise atlanır)

    Returns:
        dict: LLM yanıtı
    """
    weather_block = f"\nHAVA DURUMU BİLGİSİ:\n{weather_context}\n" if weather_context else ""
    agro_block = f"\nAGRONOMİK TAKVİM BİLGİSİ:\n{agro_context}\n" if agro_context else ""

    prompt = f"""ROVER ANOMALİ RAPORU:
{anomaly_context}{weather_block}{agro_block}
İLGİLİ TARIMSAL BİLGİ:
{field_context}

Yukarıdaki anomali durumuna ve tarımsal bilgilere dayanarak çiftçiye
kısa, net ve acil bir Türkçe tavsiye üret. Şunları belirt:
1. Sorunun ne olduğu (basit dille)
2. Hemen yapılması gereken eylem
3. Yapılmazsa olabilecek risk
4. Tavsiye edilen zamanlama
Bu bilgilere dayanarak ekim zamanı uygunsa ekimi, sulama gerekiyorsa
miktarı ve zamanlamasını, gübreleme zamanıysa dozu ve tipini de belirt."""

    return query_llm(prompt)


# ============================================================
# Doğrudan çalıştırılırsa Ollama bağlantısını test et
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("  TRAK-AI KDS — Ollama LLM Bağlantı Testi")
    print("=" * 50)
    
    if check_ollama_connection():
        print("\nBasit test sorusu gönderiliyor...")
        result = query_llm(
            "Trakya'da buğday ne zaman sulanmalı? Kısa cevap ver.",
        )
        print(f"\nYANIT:\n{result['answer']}")
        print(f"\nSüre: {result['duration_sec']} sn")
        print(f"Token: {result['tokens']}")
    else:
        print("\nOllama çalışmıyor. Önce şunu yap:")
        print("1. Ayrı terminal aç")
        print("2. 'ollama serve' çalıştır")
        print("3. Bu scripti tekrar çalıştır")