"""
TRAK-AI KDS — Tri-RAG Retriever
=================================
Bu modül sorguya en uygun belge parçalarını üç farklı yöntemle bulur:

1. Dense (FAISS)  → Anlam benzerliği: "sulama zamanı" ile "su verme periyodu" eşleşir
2. Sparse (BM25)  → Kelime eşleşmesi: "mildiyö" kelimesini birebir bulur
3. Re-rank        → İkisinin sonuçlarını birleştirir, tekrarları atar, en iyileri seçer

Neden tek yöntem yetmiyor?
- Sadece Dense: "Mildiyö" gibi özel terimleri kaçırabilir
- Sadece Sparse: "bitki su ihtiyacı" ile "sulama" arasındaki anlam bağını kuramaz
- İkisini birleştirince her iki dünyanın da en iyisini alıyoruz
"""
import numpy as np
from rank_bm25 import BM25Okapi

from config import FAISS_TOP_K, BM25_TOP_K, FINAL_TOP_K


def tri_rag_retrieve(query: str, vectorstore, chunks: list) -> list:
    """
    Tri-RAG: Dense + Sparse + Re-rank birleştirme.
    
    Args:
        query: Kullanıcının sorusu veya anomali açıklaması
        vectorstore: FAISS vektör veritabanı
        chunks: BM25 için ham chunk listesi (chunks_meta.json'dan)
    
    Returns:
        list: En iyi chunk'lar, her biri {"text", "metadata", "score", "method"} dict'i
    """
    
    # ─── A. Dense Retrieval (FAISS — semantik arama) ───
    # Soruyu vektöre çevir, FAISS'te en yakın komşuları bul
    dense_results = vectorstore.similarity_search_with_score(query, k=FAISS_TOP_K)
    
    dense_docs = []
    for doc, score in dense_results:
        dense_docs.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score),
            "method": "dense",
        })
    
    # ─── B. Sparse Retrieval (BM25 — anahtar kelime arama) ───
    # Klasik bilgi erişimi: kelimelerin frekansına dayalı eşleştirme
    corpus = [c["text"] for c in chunks]
    tokenized_corpus = [doc.lower().split() for doc in corpus]
    
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)
    
    # En yüksek skorlu chunk'ları al
    top_indices = np.argsort(bm25_scores)[-BM25_TOP_K:][::-1]
    
    sparse_docs = []
    for i in top_indices:
        if bm25_scores[i] > 0:  # skor 0 olanları alma
            sparse_docs.append({
                "text": chunks[i]["text"],
                "metadata": chunks[i]["metadata"],
                "score": float(bm25_scores[i]),
                "method": "sparse",
            })
    
    # ─── C. Re-rank: Birleştir + Tekrarları At + Sırala ───
    seen = set()
    merged = []
    
    for doc in dense_docs + sparse_docs:
        # İlk 100 karakter ile tekrar kontrolü
        key = doc["text"][:100]
        if key not in seen:
            seen.add(key)
            merged.append(doc)
    
    # Her iki yöntemde de bulunan chunk'lara bonus ver
    dense_keys = {d["text"][:100] for d in dense_docs}
    sparse_keys = {d["text"][:100] for d in sparse_docs}
    both_keys = dense_keys & sparse_keys  # kesişim
    
    for doc in merged:
        doc["boosted"] = doc["text"][:100] in both_keys
    
    # Sıralama: boosted olanlar önce, sonra skora göre
    merged.sort(key=lambda x: (x["boosted"], -x["score"]), reverse=True)
    
    # En iyi FINAL_TOP_K chunk'ı döndür
    final = merged[:FINAL_TOP_K]
    
    # Sonuç özeti
    boosted_count = sum(1 for d in final if d["boosted"])
    print(f"  Tri-RAG sonucu: Dense={len(dense_docs)}, Sparse={len(sparse_docs)}, "
          f"Birleşik={len(merged)}, Final={len(final)} (boosted: {boosted_count})")
    
    return final


def format_context(retrieved_docs: list) -> str:
    """
    Bulunan chunk'ları LLM'e gönderilecek bağlam metnine dönüştür.
    
    Her chunk'ın kaynağını gösterir, böylece LLM "bu bilgi FAO Paper 56'dan"
    gibi referans verebilir.
    """
    if not retrieved_docs:
        return "Bilgi tabanında bu konuyla ilgili belge bulunamadı."
    
    parts = []
    for i, doc in enumerate(retrieved_docs, 1):
        source = doc["metadata"].get("source", "bilinmiyor")
        method = doc["method"]
        boost = " ★" if doc.get("boosted") else ""
        
        parts.append(
            f"[Kaynak {i}: {source} ({method}{boost})]\n"
            f"{doc['text']}"
        )
    
    return "\n\n---\n\n".join(parts)


# ============================================================
# Doğrudan çalıştırılırsa test et
# ============================================================
if __name__ == "__main__":
    from build_index import load_faiss_index
    
    print("=" * 50)
    print("  TRAK-AI KDS — Tri-RAG Arama Testi")
    print("=" * 50)
    
    vectorstore, chunks = load_faiss_index()
    
    if vectorstore is None:
        print("Önce build_index.py çalıştır!")
    else:
        # Test sorguları
        test_queries = [
            "Buğdayda sapa kalkma döneminde sulama nasıl yapılır?",
            "Ayçiçeğinde mildiyö hastalığı belirtileri nelerdir?",
            "BBCH 60 evresinde nem stresi",
        ]
        
        for q in test_queries:
            print(f"\nSORGU: {q}")
            print("-" * 40)
            results = tri_rag_retrieve(q, vectorstore, chunks)
            context = format_context(results)
            print(f"BAĞLAM (ilk 300 kar.):\n{context[:300]}...")