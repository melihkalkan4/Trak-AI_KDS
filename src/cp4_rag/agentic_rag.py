"""
TRAK-AI KDS — Agentic RAG & Query Routing
===========================================
Gelen soruları BİLGİ, VERİ ve GENEL olarak sınıflandırır.
FAISS üzerinde L2 mesafe tabanlı eşik (threshold) filtresi uygular.
RAG bağlamını oluşturur ve doğrudan LLM'e yönlendirir.
"""

from typing import Dict, List, Any
from llm_engine import query_llm

def get_filtered_context(query: str, vector_db, distance_threshold: float = 1.5) -> str:
    """
    FAISS Eşik Filtresi: L2 > 1.5 olan (semantik benzerlik zayıf) chunk'ları filtreler.
    retriever.py ile tutarlı: L2 mesafesi ARTTIKÇA benzerlik AZALIR.
    Barajı geçen belge yoksa boş string ("") döndür.
    """
    if vector_db is None:
        return ""

    try:
        results = vector_db.similarity_search_with_score(query, k=5)
        filtered_docs = []
        for doc, score in results:
            if float(score) > distance_threshold:  # L2 > 1.5 = semantik benzerlik yok
                continue
                source = doc.metadata.get("source", "Bilinmeyen Kaynak")
                filtered_docs.append(f"[Kaynak: {source} (Mesafe: {score:.3f})]\n{doc.page_content}")
                
        if not filtered_docs:
            return ""
            
        return "\n\n---\n\n".join(filtered_docs)
    except Exception as e:
        print(f"[RAG FAISS Filtre Hatası] {e}")
        return ""

def classify_query(query: str) -> str:
    """
    Niyet Sınıflandırıcı: Sadece anahtar kelimelerle 3'lü sınıflandırma yapar.
    Kelime sayısına bakmaz, böylece kısa soruları doğru yönlendirir.
    """
    q_l = query.lower()
    
    bilgi_keywords = ["nasıl", "hastalık", "doz", "kılavuz", "nedir"]
    veri_keywords = ["tarlam", "durum", "nem", "rapor", "veriler"]
    
    for kw in bilgi_keywords:
        if kw in q_l:
            return "BİLGİ"
            
    for kw in veri_keywords:
        if kw in q_l:
            return "VERİ"
            
    return "GENEL"

def build_smart_rag_queries(tarla_verileri: Dict[str, Any]) -> List[str]:
    """
    Akıllı Sorgu Üretici: Tarlanın mevcut verilerini analiz ederek teknik RAG sorguları üretir.
    """
    queries = []
    urun = str(tarla_verileri.get("urun", "buğday")).lower()
    
    try:
        toprak_nemi = float(str(tarla_verileri.get("toprak_nemi", 100)).replace('%', ''))
        if toprak_nemi < 20:
            queries.append(f"düşük nem su stresi sulama miktarı zamanı {urun}")
    except:
        pass
        
    try:
        sicaklik = float(str(tarla_verileri.get("hava_sicaklik", 0)))
        if sicaklik > 30:
            queries.append(f"yüksek sıcaklık sıcak stresi önlem verim kaybı {urun}")
    except:
        pass
        
    hastalik = str(tarla_verileri.get("hastalik", "")).lower()
    if hastalik and hastalik not in ["yok", "none", "—", "-"]:
        queries.append(f"{hastalik} hastalığı tedavisi ilaçlama fungisit {urun}")
        
    if not queries:
        queries.append(f"Trakya {urun} tarımı genel bakım gübreleme takvimi")
        
    return queries

def handle_user_request(user_query: str, tarla_verileri: Dict[str, Any], vector_db, chat_history: str = "") -> Dict[str, Any]:
    """
    Ana Orkestratör: Kullanıcı sorusunu sınıflandırır, RAG bağlamını oluşturur ve LLM'e yönlendirir.
    """
    # 1. Adım: Çökmeyi önlemek için varsayılan değişkenlerin tanımlanması
    context = ""
    sources = []
    
    # 2. Adım: Niyetin belirlenmesi
    kategori = classify_query(user_query)
    
    # Tarla verilerini okunabilir bir metne dönüştür
    tarla_str = ""
    if tarla_verileri:
        for k, v in tarla_verileri.items():
            if v and v != "Bilinmiyor":
                tarla_str += f"- {k.replace('_', ' ').title()}: {v}\n"
    if not tarla_str.strip():
        tarla_str = "- Güncel tarla verisi bulunmuyor.\n"
        
    # 3. Adım: İf/Else Bloklarının ve Promptların Tasarımı
    if kategori == "GENEL":
        system_msg = (
            "Sen bir tarım asistanısın, geçmiş sohbete bakarak doğal cevap ver, rakamlara boğma."
        )
        prompt = (
            f"Geçmiş Sohbet:\n{chat_history}\n\n"
            f"Kullanıcı Sorusu: {user_query}"
        )
        rag_mode = "YOK"
        # sources boş liste olarak kalacak
        
    elif kategori == "BİLGİ":
        context = get_filtered_context(user_query, vector_db, distance_threshold=1.1)
        if context:
            sources = [{"metadata": {"source": "RAG"}, "method": "Kılavuz Araması"}]
            system_msg = (
                "Sen uzman bir tarım asistanısın. Kullanıcı spesifik teknik bir bilgi soruyor. "
                "Aşağıdaki resmi tarımsal belgelerden SADECE ilgili kısımları kullanarak yanıt ver. "
                "Belgelerde yoksa kesinlikle uydurma."
            )
            prompt = (
                f"Kullanıcı Sorusu: {user_query}\n\n"
                f"Bulunan Resmi Tarımsal Belgeler:\n{context}"
            )
        else:
            system_msg = "Sen dürüst ve yardımsever bir tarım asistanısın."
            prompt = (
                f"Kullanıcı Sorusu: {user_query}\n\n"
                "Sistem Notu: Veritabanımda bu konu hakkında resmi bir kılavuz bulunmuyor. Lütfen kullanıcıya 'Veritabanımda bu konu yok' diyerek durumu bildir ve uydurma yapma."
            )
        rag_mode = "DOGRUDAN"
        
    else:  # VERİ
        smart_queries = build_smart_rag_queries(tarla_verileri)
        
        all_context_parts = set()
        for sq in smart_queries:
            ctx = get_filtered_context(sq, vector_db, distance_threshold=1.1)
            if ctx:
                all_context_parts.add(ctx)
                
        context = "\n\n---\n\n".join(all_context_parts)
        
        if context:
            sources = [
                {"metadata": {"source": "Tarla Sensörleri"}, "method": "Canlı Veri"},
                {"metadata": {"source": "RAG"}, "method": "Kılavuz Çözümleri"}
            ]
        else:
            sources = [{"metadata": {"source": "Tarla Sensörleri"}, "method": "Canlı Veri"}]
            
        system_msg = (
            "Sen veri odaklı, analitik bir tarım uzmanısın. Kullanıcı tarlasının anlık veya genel durumunu soruyor. "
            "1. Tarlanın güncel durumunu çiftçiye kısaca özetle.\n"
            "2. Mevcut risklere göre (düşük nem, hastalık vs.) bağlamdaki resmi belgeleri kullanarak uygulanması gereken aksiyonları söyle.\n"
            "3. Bağlamda bulunmayan hiçbir tedavi yöntemi önerme, uydurma ve rakamları basitçe ifade et."
        )
        prompt = (
            f"Kullanıcı Sorusu: {user_query}\n\n"
            f"Tarlanın Güncel Anlık Verileri:\n{tarla_str}\n"
            f"Bu verilere istinaden bulunan Çözüm Önerileri (RAG):\n{context if context else 'Sisteme kayıtlı çözüm önerisi bulunamadı.'}"
        )
        rag_mode = "AKILLI"

    # LLM Çağrısı (llm_engine'den query_llm ile)
    result = query_llm(prompt, system_prompt=system_msg)
    
    # Dashboard ve arayüz uyumluluğu için JSON döndür
    result["query_type"] = kategori
    result["rag_mode"] = rag_mode
    result["sources"] = sources
    return result
