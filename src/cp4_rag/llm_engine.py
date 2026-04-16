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
        return {
            "answer": f"[HATA] Beklenmeyen hata: {e}",
            "duration_sec": 0,
            "tokens": 0,
            "model": OLLAMA_MODEL,
        }


def rag_query(query: str, context: str) -> dict:
    """
    RAG sorgusu: Bağlam + soru → LLM → Türkçe yanıt.
    
    Bu fonksiyon retriever.py'den gelen context'i alır ve
    LLM'e göndermek için tam prompt'u oluşturur.
    
    Args:
        query: Kullanıcının sorusu
        context: format_context()'den gelen kaynak metin
    
    Returns:
        dict: {"answer": "...", "duration_sec": ..., "tokens": ...}
    """
    full_prompt = f"""SORU: {query}

KAYNAK BELGELER:
{context}

Yukarıdaki kaynak belgelere dayanarak soruyu Türkçe yanıtla.
Somut tavsiyeler ver: ne yapılmalı, ne zaman, ne kadar.
Emin olmadığın bilgiyi uydurma."""

    return query_llm(full_prompt)


def rover_alert_query(anomaly_context: str, field_context: str) -> dict:
    """
    Rover anomali senaryosu için özel prompt.
    
    ÇP-2'nin inference çıktısı + Rover sensör verisi + RAG belgesi
    birleştirilip LLM'e gönderilir.
    
    Args:
        anomaly_context: Anomali açıklaması (nem farkı, hastalık vb.)
        field_context: RAG'dan gelen ilgili belge parçaları
    
    Returns:
        dict: LLM yanıtı
    """
    prompt = f"""ROVER ANOMALİ RAPORU:
{anomaly_context}

İLGİLİ TARIMSAL BİLGİ:
{field_context}

Yukarıdaki anomali durumuna ve tarımsal bilgilere dayanarak çiftçiye
kısa, net ve acil bir Türkçe tavsiye üret. Şunları belirt:
1. Sorunun ne olduğu (basit dille)
2. Hemen yapılması gereken eylem
3. Yapılmazsa olabilecek risk
4. Tavsiye edilen zamanlama"""

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