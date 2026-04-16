"""
TRAK-AI KDS — ÇP-4 Ana RAG Pipeline
======================================
Tüm parçaları birleştiren ana dosya. Üç modda çalışır:

  python main_rag.py build              → PDF'leri oku, FAISS indeksi oluştur
  python main_rag.py query "sorunuz"    → Bilgi tabanına soru sor
  python main_rag.py test               → Hazır senaryolarla sistemi dene
  python main_rag.py info               → İndeks bilgisini göster

Akış: PDF → Chunk → Embedding → FAISS → Tri-RAG → Ollama LLM → Türkçe Tavsiye
"""
import sys
import json
from datetime import datetime
from pathlib import Path

from config import FAISS_DIR, ANOMALY_THRESHOLDS
from build_index import build_faiss_index, load_faiss_index
from retriever import tri_rag_retrieve, format_context
from llm_engine import rag_query, rover_alert_query, check_ollama_connection


# ============================================================
# 1. BUILD — Bilgi tabanı oluştur
# ============================================================
def cmd_build():
    """PDF'leri oku → chunk'la → FAISS indeksi oluştur."""
    print("\n" + "=" * 55)
    print("  TRAK-AI KDS — Bilgi Tabanı Oluşturuluyor")
    print("=" * 55)
    
    vectorstore = build_faiss_index()
    
    if vectorstore:
        print("\nBaşarılı! Şimdi dene:")
        print('  python main_rag.py query "Buğdayda sulama zamanı ne zaman?"')


# ============================================================
# 2. QUERY — Soru sor
# ============================================================
def cmd_query(question: str):
    """Bilgi tabanına soru sor → Tri-RAG → LLM → Türkçe yanıt."""
    
    # Ollama çalışıyor mu?
    if not check_ollama_connection():
        return
    
    # FAISS indeksini yükle
    vectorstore, chunks = load_faiss_index()
    if vectorstore is None:
        return
    
    print(f"\nSORU: {question}")
    print("-" * 55)
    
    # Tri-RAG ile en alakalı chunk'ları bul
    print("\n[1/2] Bilgi tabanında aranıyor (Tri-RAG)...")
    results = tri_rag_retrieve(question, vectorstore, chunks)
    context = format_context(results)
    
    # LLM'e gönder
    print("\n[2/2] LLM'den yanıt alınıyor...")
    llm_result = rag_query(question, context)
    
    # Sonucu göster
    print(f"\n{'=' * 55}")
    print(f"YANIT:")
    print(f"{'=' * 55}")
    print(llm_result["answer"])
    print(f"\n--- Bilgi ---")
    print(f"Süre: {llm_result['duration_sec']} sn | Token: {llm_result['tokens']}")
    print(f"Kaynaklar:")
    for r in results:
        src = r["metadata"].get("source", "?")
        method = r["method"]
        boost = " ★" if r.get("boosted") else ""
        print(f"  - {src} ({method}{boost})")


# ============================================================
# 3. ROVER SİMÜLASYONU — ÇP-2 çıktısı ile anomali testi
# ============================================================
def cmd_rover_test():
    """
    Rover anomali senaryosunu simüle et.
    ÇP-2'nin inference çıktısını taklit ederek tam pipeline'ı test eder.
    """
    if not check_ollama_connection():
        return
    
    vectorstore, chunks = load_faiss_index()
    if vectorstore is None:
        return
    
    print("\n" + "=" * 55)
    print("  TRAK-AI KDS — Rover Anomali Simülasyonu")
    print("=" * 55)
    
    # ÇP-2 inference çıktısını simüle et (gerçekte inference_cp2.py'den gelecek)
    model_prediction = {
        "ndvi_current": 0.4675,
        "ndvi_predicted_t7": 0.4413,
        "trend": "STABLE",
        "trend_pct": -5.6,
        "crop": "Buğday",
    }
    
    # Rover sensör verisini simüle et (gerçekte ESP32 MQTT'den gelecek)
    rover_data = {
        "nem": 12,
        "bbch": 60,
        "hastalik": "sarı pas",
        "guven": 0.88,
        "ndvi_gozlem": 0.31,
    }
    
    # Anomali kontrolü
    ndvi_fark = abs(model_prediction["ndvi_current"] - rover_data["ndvi_gozlem"])
    anomalies = []
    
    if ndvi_fark >= ANOMALY_THRESHOLDS["ndvi_fark_min"]:
        anomalies.append(f"NDVI sapması: Model {model_prediction['ndvi_current']:.2f} vs "
                        f"Rover {rover_data['ndvi_gozlem']:.2f} (fark: {ndvi_fark:.2f})")
    
    if rover_data["nem"] < 15:
        anomalies.append(f"Kritik düşük nem: %{rover_data['nem']}")
    
    if rover_data["hastalik"] and rover_data["guven"] >= ANOMALY_THRESHOLDS["hastalik_guven_min"]:
        anomalies.append(f"Hastalık: {rover_data['hastalik']} (güven: {rover_data['guven']})")
    
    if not anomalies:
        print("\nAnomali yok — sistem normal.")
        return
    
    # Anomali var — RAG'dan bilgi çek
    print(f"\n{'!' * 55}")
    print(f"  {len(anomalies)} ANOMALİ TESPİT EDİLDİ!")
    for a in anomalies:
        print(f"  → {a}")
    print(f"{'!' * 55}")
    
    # Anomali tipine göre arama sorgusu oluştur
    search_query = (f"{model_prediction['crop']} {' '.join(anomalies)} "
                    f"Trakya sulama hastalık mücadele")
    
    print("\n[1/3] Bilgi tabanında aranıyor...")
    results = tri_rag_retrieve(search_query, vectorstore, chunks)
    field_context = format_context(results)
    
    # Anomali context oluştur
    anomaly_text = f"""Ürün: {model_prediction['crop']}
Konum: Trakya (Kırklareli, Vize)
Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}

ÇP-2 Model Tahmini (7 gün):
  - Mevcut NDVI: {model_prediction['ndvi_current']}
  - Tahmini NDVI (t+7): {model_prediction['ndvi_predicted_t7']}
  - Trend: {model_prediction['trend']} ({model_prediction['trend_pct']}%)

Rover Ölçümleri:
  - Toprak nemi: %{rover_data['nem']}
  - BBCH evresi: {rover_data['bbch']}
  - Gözlenen NDVI: {rover_data['ndvi_gozlem']}
  - Hastalık: {rover_data['hastalik']} (güven: {rover_data['guven']})

Tespit Edilen Anomaliler:
{chr(10).join('  - ' + a for a in anomalies)}"""

    print("\n[2/3] Anomali bağlamı oluşturuldu.")
    
    # LLM'e gönder
    print("\n[3/3] LLM'den çiftçi tavsiyesi alınıyor...")
    llm_result = rover_alert_query(anomaly_text, field_context)
    
    # Sonuç
    print(f"\n{'=' * 55}")
    print(f"ÇİFTÇİ BİLDİRİMİ:")
    print(f"{'=' * 55}")
    print(llm_result["answer"])
    print(f"\n--- Bilgi ---")
    print(f"Süre: {llm_result['duration_sec']} sn | Model: {llm_result['model']}")
    print(f"Kaynaklar:")
    for r in results:
        print(f"  - {r['metadata'].get('source', '?')}")


# ============================================================
# 4. INFO — İndeks bilgisi
# ============================================================
def cmd_info():
    """Mevcut FAISS indeksinin detaylarını göster."""
    vectorstore, chunks = load_faiss_index()
    if vectorstore is None:
        return
    
    print(f"\n{'=' * 55}")
    print(f"  TRAK-AI KDS — Bilgi Tabanı Özeti")
    print(f"{'=' * 55}")
    print(f"  Vektör sayısı: {vectorstore.index.ntotal}")
    print(f"  Chunk sayısı:  {len(chunks)}")
    
    # Belge bazında dağılım
    sources = {}
    for c in chunks:
        src = c["metadata"]["source"]
        sources[src] = sources.get(src, 0) + 1
    
    print(f"  Benzersiz belge: {len(sources)}")
    print(f"\n  Belge detayları:")
    for src, count in sorted(sources.items()):
        cat = next((c["metadata"]["category"] for c in chunks 
                    if c["metadata"]["source"] == src), "?")
        print(f"    [{cat}] {src}: {count} chunk")


# ============================================================
# 5. TEST — Hazır sorularla sistemi dene
# ============================================================
def cmd_test():
    """Üç farklı senaryo ile sistemi test et."""
    if not check_ollama_connection():
        return
    
    vectorstore, chunks = load_faiss_index()
    if vectorstore is None:
        return
    
    test_queries = [
        "Trakya'da buğdayı ne zaman sulamalıyım?",
        "Ayçiçeğinde mildiyö hastalığı görüldü, ne yapmalıyım?",
        "BBCH 60 evresinde toprak nemi %12'ye düştü, acil durum mu?",
    ]
    
    print("\n" + "=" * 55)
    print("  TRAK-AI KDS — Otomatik Test")
    print("=" * 55)
    
    for i, q in enumerate(test_queries, 1):
        print(f"\n{'─' * 55}")
        print(f"TEST {i}/3: {q}")
        print(f"{'─' * 55}")
        
        results = tri_rag_retrieve(q, vectorstore, chunks)
        context = format_context(results)
        llm_result = rag_query(q, context)
        
        print(f"\nYANIT ({llm_result['duration_sec']} sn):")
        print(llm_result["answer"][:400])
        if len(llm_result["answer"]) > 400:
            print("...")
    
    # Rover simülasyonu da çalıştır
    print(f"\n{'─' * 55}")
    print(f"TEST 4/4: Rover Anomali Simülasyonu")
    print(f"{'─' * 55}")
    cmd_rover_test()


# ============================================================
# CLI — Komut satırı arayüzü
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""
TRAK-AI KDS — ÇP-4 Yerel RAG Sistemi
======================================
Kullanım:
  python main_rag.py build              PDF'lerden bilgi tabanı oluştur
  python main_rag.py query "sorunuz"    Bilgi tabanına soru sor
  python main_rag.py test               Hazır senaryolarla test et
  python main_rag.py rover              Rover anomali simülasyonu
  python main_rag.py info               İndeks bilgisini göster

İlk kullanım sırası:
  1. docs/ klasörüne PDF'leri koy
  2. python main_rag.py build
  3. python main_rag.py query "Buğdayda sulama zamanı?"
        """)
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "build":
        cmd_build()
    
    elif command == "query":
        if len(sys.argv) < 3:
            print("Kullanım: python main_rag.py query \"sorunuz\"")
            sys.exit(1)
        question = " ".join(sys.argv[2:])
        cmd_query(question)
    
    elif command == "test":
        cmd_test()
    
    elif command == "rover":
        cmd_rover_test()
    
    elif command == "info":
        cmd_info()
    
    else:
        print(f"Bilinmeyen komut: {command}")
        print("Geçerli komutlar: build, query, test, rover, info")