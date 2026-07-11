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


def get_llm_engine():
    """Return {'model', 'base_url'} dict if Ollama is reachable, else None.

    Mirrors the contract of src/llm_engine.get_llm_engine so dashboard pages
    (settings.py) can read engine health regardless of which `llm_engine`
    module wins on sys.path (cp4_rag/ vs src/).
    """
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if resp.status_code != 200:
            return None
        models = [m.get("name", "") for m in resp.json().get("models", [])]
        if not models:
            return None
        # Prefer configured model when present, else first available.
        chosen = OLLAMA_MODEL if OLLAMA_MODEL in models else models[0]
        return {"model": chosen, "base_url": OLLAMA_BASE_URL}
    except (requests.RequestException, ValueError):
        return None


def llm_status_text() -> str:
    """One-line health string for sidebar/settings panel."""
    eng = get_llm_engine()
    if eng is None:
        return "🔴 Ollama kapalı / model yok"
    return f"🟢 {eng['model']}"


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

        if not answer:
            print(f"  UYARI: Ollama bos yanit dondu. Ham yanit: {str(result)[:200]}")
            answer = "Ollama yanit uretmedi. 'ollama serve' calisiyorsa modeli kontrol edin: ollama list"

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
    """Tüm sistemden güncel veri toplayıp tek bir bağlam metni oluşturur.

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

    sections = []

    # ── 1. Bitki Sağlık Tahmini (ConvLSTM/LSTM) ──────────────────────────
    try:
        from inference_cp2 import predict

        wheat = predict("Wheat")
        gc.collect()
        sunflower = predict("Sunflower")
        gc.collect()

        w_ndvi  = wheat.get("current_ndvi", 0)
        w_pred  = wheat.get("predicted_ndvi", 0)
        w_delta = wheat.get("trend", {}).get("delta", 0)
        w_pct   = wheat.get("trend", {}).get("pct_change", 0)
        w_health = wheat.get("health", {}).get("status", "Bilinmiyor")
        w_desc   = wheat.get("health", {}).get("desc", "")
        w_action = wheat.get("health", {}).get("action", "")
        w_summary = wheat.get("field_summary", "")

        s_ndvi  = sunflower.get("current_ndvi", 0)
        s_pred  = sunflower.get("predicted_ndvi", 0)
        s_delta = sunflower.get("trend", {}).get("delta", 0)
        s_pct   = sunflower.get("trend", {}).get("pct_change", 0)
        s_health = sunflower.get("health", {}).get("status", "Bilinmiyor")
        s_desc   = sunflower.get("health", {}).get("desc", "")
        s_action = sunflower.get("health", {}).get("action", "")

        sections.append(
            "BİTKİ SAĞLIK TAHMİNİ (ConvLSTM/LSTM derin öğrenme modeli, Trakya 2017-2024 verisiyle eğitildi):\n\n"
            f"Buğday tarlası:\n"
            f"  Şu anki bitki sağlık endeksi (NDVI): {w_ndvi:.4f}\n"
            f"  7 gün sonrası tahmini: {w_pred:.4f} (değişim: {w_delta:+.4f}, %{w_pct:+.1f})\n"
            f"  Genel durum: {w_health} — {w_desc}\n"
            f"  Tavsiye edilen eylem: {w_action}\n"
            + (f"  Son 15 gün özeti: {w_summary}\n" if w_summary else "")
            + "\n"
            f"Ayçiçeği tarlası:\n"
            f"  Şu anki NDVI: {s_ndvi:.4f}\n"
            f"  7 gün sonrası tahmini: {s_pred:.4f} (değişim: {s_delta:+.4f}, %{s_pct:+.1f})\n"
            f"  Genel durum: {s_health} — {s_desc}\n"
            f"  Tavsiye edilen eylem: {s_action}\n\n"
            "NOT: NDVI ölçeği: 0.0–0.25=Kritik (bitki ölüyor), 0.25–0.40=Zayıf, "
            "0.40–0.55=Orta, 0.55–0.70=İyi, 0.70+=Mükemmel"
        )
    except Exception as e:
        sections.append(f"[Bitki sağlık tahmini alınamadı: {e}]")

    # ── 2. Verim Tahmini (XGBoost) ─────────────────────────────────────────
    try:
        from inference_yield import predict_yield

        wy = predict_yield("Wheat")
        sy = predict_yield("Sunflower")

        def _yield_faktorler(r):
            faktorler = r.get("en_etkili_faktorler", [])[:3]
            return ", ".join(f.get("ozellik", "") for f in faktorler if f.get("ozellik"))

        if wy.get("tahmini_verim_kg_dekar") is not None:
            sections.append(
                "VERİM TAHMİNİ (XGBoost regresyon modeli, TÜİK verileriyle eğitildi):\n\n"
                f"Buğday:\n"
                f"  Tahmini verim: {wy['tahmini_verim_kg_dekar']:.1f} kg/dekar\n"
                f"  Trakya bölge ortalaması: {wy['trakya_ortalama']:.0f} kg/dekar\n"
                f"  Karşılaştırma: ortalamanın %{wy['yuzde_karsilastirma']:+.1f}\n"
                f"  Güven aralığı: {wy['guven_araligi']['alt']:.0f}–{wy['guven_araligi']['ust']:.0f} kg/dekar\n"
                f"  Trend: {wy.get('trend', '?')}\n"
                f"  Risk: {wy['risk_analizi']}\n"
                + (f"  En etkili faktörler: {_yield_faktorler(wy)}\n" if _yield_faktorler(wy) else "")
                + (f"  NOT: {wy['uyari']}\n" if wy.get("uyari") else "")
                + "\n"
                f"Ayçiçeği:\n"
                f"  Tahmini verim: {sy['tahmini_verim_kg_dekar']:.1f} kg/dekar\n"
                f"  Trakya bölge ortalaması: {sy['trakya_ortalama']:.0f} kg/dekar\n"
                f"  Karşılaştırma: ortalamanın %{sy['yuzde_karsilastirma']:+.1f}\n"
                f"  Trend: {sy.get('trend', '?')}\n"
                f"  Risk: {sy['risk_analizi']}"
            )
    except Exception:
        pass  # Verim tahmini yoksa sessizce devam et

    # ── 3. Hava Durumu ─────────────────────────────────────────────────────
    weather = None
    forecast = None
    try:
        from weather_service import get_current_weather, get_7day_forecast, get_weather_alerts

        weather  = get_current_weather()
        forecast = get_7day_forecast()
        alerts   = get_weather_alerts(forecast) if forecast else []

        if weather:
            sections.append(
                "ANLIK HAVA DURUMU (Open-Meteo, Kırklareli-Vize pilot tarlası):\n"
                f"  Hava sıcaklığı: {weather.get('temp_c', '?')}°C\n"
                f"  Hava nemi: %{weather.get('humidity', '?')}\n"
                f"  Toprak sıcaklığı: {weather.get('soil_temp_c', '?')}°C\n"
                f"  Toprak nemi: %{weather.get('soil_moisture', '?')}\n"
                f"  Yağış: {weather.get('precipitation_mm', 0)} mm\n"
                f"  Rüzgar: {weather.get('wind_kmh', '?')} km/h"
            )

        if forecast:
            toplam_yagis = sum(d.get("precip_mm", 0) for d in forecast[:7])
            yagissiz_gun = sum(1 for d in forecast[:7] if d.get("precip_mm", 0) < 1)
            fc_lines = ["7 GÜNLÜK HAVA TAHMİNİ:"]
            for day in forecast[:7]:
                fc_lines.append(
                    f"  {day.get('date', '')}: "
                    f"{day.get('temp_min', '')}–{day.get('temp_max', '')}°C, "
                    f"Yağış: {day.get('precip_mm', 0)}mm "
                    f"(%{day.get('precip_prob', 0)} olasılık)"
                )
            fc_lines.append(
                f"  ÖZET: 7 günde toplam {toplam_yagis:.1f}mm yağış, {yagissiz_gun} gün kuru"
            )
            sections.append("\n".join(fc_lines))

        if alerts:
            alert_texts = [a["text"] if isinstance(a, dict) else str(a) for a in alerts]
            sections.append("HAVA UYARILARI: " + " | ".join(alert_texts))
    except Exception:
        pass

    # ── 4. Fenolojik Takvim + Sulama + Gübreleme ───────────────────────────
    try:
        from agro_calendar import (
            get_current_phenology, get_irrigation_advice, get_fertilization_advice,
        )
        from datetime import datetime

        month = datetime.now().month
        soil_m = weather.get("soil_moisture", 25.0) if weather else 25.0

        wp = get_current_phenology("Wheat", month)
        sp = get_current_phenology("Sunflower", month)

        fenoloji_lines = [
            f"FENOLOJİK TAKVİM (Trakya, {datetime.now().strftime('%d %B %Y')}):\n",
            f"Buğday: {wp.get('evre', '?')} evresi (BBCH {wp.get('bbch_aralik', '?')})",
            f"  Açıklama: {wp.get('aciklama', '')}",
            f"  {'KRİTİK DÖNEM — bu evrede su stresi verimi ciddi düşürür!' if wp.get('kritik_mi') else 'Normal dönem.'}",
            "",
            f"Ayçiçeği: {sp.get('evre', '?')} evresi (BBCH {sp.get('bbch_aralik', '?')})",
            f"  Açıklama: {sp.get('aciklama', '')}",
            f"  {'KRİTİK DÖNEM — bu evrede su stresi verimi ciddi düşürür!' if sp.get('kritik_mi') else 'Normal dönem.'}",
        ]
        sections.append("\n".join(fenoloji_lines))

        wi = get_irrigation_advice("Wheat", month, soil_m, forecast)
        si = get_irrigation_advice("Sunflower", month, soil_m, forecast)

        sulama_lines = ["SULAMA DEĞERLENDİRMESİ:"]
        for label, irr in [("Buğday", wi), ("Ayçiçeği", si)]:
            if irr.get("sulama_gerekli"):
                sulama_lines.append(
                    f"  {label}: {irr.get('aciliyet', '?')} — {irr.get('gerekce', '')} "
                    f"| Öneri: {irr.get('miktar_ton_dekar', '?')} ton/dekar, {irr.get('zamanlama', '')}"
                )
            else:
                sulama_lines.append(f"  {label}: Şu an sulama gerekmiyor. {irr.get('gerekce', '')}")
        sections.append("\n".join(sulama_lines))

        gubre_lines = ["GÜBRELEME TAKVİMİ:"]
        for label, crop_key in [("Buğday", "Wheat"), ("Ayçiçeği", "Sunflower")]:
            gf = get_fertilization_advice(crop_key, month)
            if gf.get("gubre_zamani"):
                gubre_lines.append(f"  {label}: EVET — {gf.get('tip', '')}, {gf.get('doz', '')}")
            else:
                gubre_lines.append(f"  {label}: Bu dönemde gübreleme yok.")
        sections.append("\n".join(gubre_lines))
    except Exception:
        pass  # Fenoloji/sulama/gubre yoksa sessizce devam et

    # ── 5. Ekim Penceresi ──────────────────────────────────────────────────
    try:
        from agro_calendar import evaluate_planting_window

        we = evaluate_planting_window("Wheat", weather, forecast)
        se = evaluate_planting_window("Sunflower", weather, forecast)
        sections.append(
            "EKİM PENCERESİ:\n"
            f"  Buğday: {we.get('kategori', '?')} (skor: {we.get('skor', '?')}/100) — {we.get('gerekce', '')}\n"
            f"  Ayçiçeği: {se.get('kategori', '?')} (skor: {se.get('skor', '?')}/100) — {se.get('gerekce', '')}"
        )
    except Exception:
        pass

    # ── 6. Toprak Profili (statik) ─────────────────────────────────────────
    sections.append(
        "TOPRAK PROFİLİ (SoilGrids 2.0):\n"
        "  Kil: %30.97, Kum: %34.99, Silt: %34.04, pH: 7.11\n"
        "  Tip: Killi-tınlı (clay-loam), su tutma kapasitesi orta-yüksek\n"
        "  Konum: Kırklareli-Vize, 41.694°N 27.105°E"
    )

    # ── 7. Son Kamera Analizi ──────────────────────────────────────────────
    try:
        import sys as _sys
        _src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if _src not in _sys.path:
            _sys.path.insert(0, _src)
        from database import get_rover_olcumler
        son_olcumler = get_rover_olcumler(1, limit=5)
        kamera_satir = next((r for r in son_olcumler if r.get("hastalik")), None)
        if kamera_satir:
            sections.append(
                f"SON KAMERA ANALİZİ:\n"
                f"- Tespit: {kamera_satir['hastalik']} "
                f"(%{(kamera_satir.get('hastalik_guven') or 0)*100:.0f} güven)\n"
                f"- Waypoint: {kamera_satir.get('waypoint_label','?')}\n"
                f"- Tarih: {kamera_satir.get('timestamp','?')}"
            )
    except Exception:
        pass

    # ── 8. Hava Durumu Geçmişi (Son 30 Gün) ──────────────────────────────
    try:
        from database import get_weather_stats
        ws = get_weather_stats(1, days=30)  # Buğday tarlası (tarla_id=1) referans
        if ws and ws.get("gun_sayisi", 0) > 0:
            sections.append(
                f"HAVA DURUMU GEÇMİŞİ (Son {ws['gun_sayisi']} gün, Edirne-Merkez referans):\n"
                f"  Ortalama sıcaklık: {ws.get('avg_temp', '?')}°C\n"
                f"  Maksimum: {ws.get('max_temp', '?')}°C | Minimum: {ws.get('min_temp', '?')}°C\n"
                f"  Toplam yağış: {ws.get('toplam_yagis', 0):.0f}mm ({ws.get('yagisli_gun', 0)} yağışlı gün)\n"
                f"  Kümülatif GDD (baz 10°C): {ws.get('son_gdd_kum', 0):.0f}\n"
                + (f"  Don günü sayısı: {ws['don_gun']} (gece ≤2°C)\n" if ws.get("don_gun", 0) > 0 else "")
                + (f"  Sıcak stres günü: {ws['sicak_gun']} (gündüz ≥30°C)\n" if ws.get("sicak_gun", 0) > 0 else "")
            )
    except Exception:
        pass

    return "\n\n".join(sections)


def rag_query(query: str, context: str, rich_context: str = None) -> dict:
    """RAG sorgusu: soru + tarla verileri + belgeler → LLM → Türkçe yanıt."""
    rich_block = f"{rich_context}\n\n" if rich_context else ""
    rag_block = f"İlgili tarımsal belgelerden bilgi:\n{context}\n\n" if context else ""

    full_prompt = (
        f"{query}\n\n"
        "---\n"
        "Aşağıda tarla hakkında güncel veriler var. Yanıtında bunlardan yararlan:\n\n"
        f"{rich_block}"
        f"{rag_block}"
    )

    return query_llm(full_prompt)


_VERI_KEYWORDS = [
    "tarlam", "verim", "su", "sulama", "rapor", "durum", "hava",
    "ekim zamanı", "ekim zamani", "nasıl gidiyor", "nasil gidiyor",
    "ne zaman", "sensor", "nem", "sıcaklık", "sicaklik", "tahmin",
    "ndvi", "hastalık var mı", "hastalik var mi",
]
_BILGI_KEYWORDS = [
    "nedir", "nelerdir", "nasıl yapılır", "nasil yapilir", "belirtisi",
    "ilaç", "ilac", "doz", "mildiyö", "mildyo", "pas", "sclerotinia",
    "hastalık", "hastalik", "gübreleme", "gubreleme", "bbch", "fungisit",
    "herbisit", "pestisit", "tohum", "çeşit", "cesit", "rotasyon",
]


def classify_query(question: str) -> str:
    """Soruyu VERI / BILGI / GENEL olarak sınıflandır."""
    q = question.lower()
    for kw in _VERI_KEYWORDS:
        if kw in q:
            return "VERI"
    for kw in _BILGI_KEYWORDS:
        if kw in q:
            return "BILGI"
    return "GENEL"


def build_smart_rag_queries(rich_context: str) -> list:
    """rich_context içindeki sorunları tespit ederek hedefli RAG sorguları üret."""
    ctx = rich_context.lower()
    queries = []
    if ("sulama gerekl" in ctx or "acil" in ctx) and ("nem" in ctx or "kuraklık" in ctx or "kuraklik" in ctx):
        queries.append("sulama zamanı miktarı Trakya buğday ayçiçeği toprak nemi")
    if "kritik dönem" in ctx or "kritik donem" in ctx:
        queries.append("su stresi verim kaybı çiçeklenme başaklanma kritik dönem")
    if "hastalık" in ctx or "mildiy" in ctx or "pas" in ctx or "fusarium" in ctx:
        queries.append("hastalık mücadele ilaçlama fungisit önerisi Trakya")
    if ("düşü" in ctx or "dusu" in ctx) and "verim" in ctx:
        queries.append("verim kaybı önleme gübreleme sulama Trakya buğday ayçiçeği")
    if "ekim" in ctx and ("uygun" in ctx or "pencere" in ctx or "skor" in ctx):
        queries.append("ekim zamanı toprak sıcaklığı don riski Trakya")
    if "gübre" in ctx or "gubre" in ctx:
        queries.append("Trakya buğday ayçiçeği gübreleme takvimi doz")
    if "don riski" in ctx or "don_riski" in ctx:
        queries.append("don riski önlem bitki koruma Trakya")
    if not queries:
        queries.append("Trakya bölgesi tarım bakım takvimi buğday ayçiçeği")
    return queries


def generate_chat_response(
    user_question: str,
    vectorstore=None,
    chunks: list = None,
    rag_context: str = "",
) -> dict:
    """Akıllı sohbet modu: sorgu tipine göre RAG stratejisi seçer.

    VERI  → rich_context'ten sorun tespiti → hedefli RAG sorguları → LLM
    BILGI → kullanıcı sorusunu RAG'a gönder → LLM
    GENEL → doğrudan LLM (RAG yok)
    """
    from retriever import tri_rag_retrieve, format_context

    query_type = classify_query(user_question)
    print(f"[LLM] Sorgu tipi: {query_type} | Soru: {user_question[:60]}")

    rich_context = build_rich_context()
    # Prompt cok uzunsa kisalt (gemma3:4b 4096 token = ~12k karakter, guvenli marj 6500)
    if len(rich_context) > 6500:
        rich_context = rich_context[:6500] + "\n...(kisaltildi)"
    print(f"[LLM] Rich context uzunlugu: {len(rich_context)} karakter")

    sources = []
    rag_mode = "YOK"
    final_rag_context = rag_context

    if query_type == "VERI" and vectorstore is not None and chunks:
        smart_queries = build_smart_rag_queries(rich_context)
        all_docs = []
        for sq in smart_queries[:2]:
            all_docs.extend(tri_rag_retrieve(sq, vectorstore, chunks))
        seen = set()
        unique_docs = []
        for d in all_docs:
            key = d.get("text", "")[:80]
            if key not in seen:
                seen.add(key)
                unique_docs.append(d)
        unique_docs = unique_docs[:3]
        sources = unique_docs
        final_rag_context = format_context(unique_docs) if unique_docs else ""
        rag_mode = "AKILLI"

    elif query_type == "BILGI" and vectorstore is not None and chunks:
        docs = tri_rag_retrieve(user_question, vectorstore, chunks)
        sources = docs[:4]
        final_rag_context = format_context(sources) if sources else ""
        rag_mode = "DOGRUDAN"

    print(f"[LLM] RAG chunk sayisi: {len(sources)} | RAG modu: {rag_mode}")
    print(f"[LLM] RAG context uzunlugu: {len(final_rag_context)} karakter")
    print(f"[LLM] Ollama cagriliyor...")

    result = rag_query(user_question, final_rag_context, rich_context)

    answer = result.get("answer", "")
    print(f"[LLM] Yanit alindi: {len(answer)} karakter | Sure: {result.get('duration_sec',0):.1f}s")
    if not answer.strip():
        print("[LLM] UYARI: Bos yanit geldi!")

    result["query_type"] = query_type
    result["rag_used"] = rag_mode != "YOK"
    result["rag_mode"] = rag_mode
    result["sources"] = sources
    return result


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
    weather_block = f"\nHAVA DURUMU:\n{weather_context}\n" if weather_context else ""
    agro_block = f"\nAGRONOMİK TAKVİM:\n{agro_context}\n" if agro_context else ""

    prompt = (
        f"Bu anomali raporu için çiftçiye Türkçe tavsiye ver:\n\n"
        f"ANOMALİ:\n{anomaly_context}{weather_block}{agro_block}\n"
        f"İLGİLİ TARIMSAL BİLGİ:\n{field_context}"
    )

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