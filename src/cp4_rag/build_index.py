"""
TRAK-AI KDS — FAISS Vektör İndeks Oluşturucu
==============================================
Bu modül şunları yapar:
1. pdf_loader'dan gelen chunk'ları alır
2. Her chunk'ı embedding modeli ile sayısal vektöre çevirir
3. Vektörleri FAISS indeksine yazar (diske kaydeder)
4. Metadata'yı JSON olarak saklar (BM25 sparse arama için)

İlk seferde çalıştır, sonra tekrar çalıştırmana gerek yok.
Yeni PDF eklediysen tekrar çalıştır — indeks sıfırdan oluşur.
"""
import json
import time
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

from config import EMBEDDING_MODEL, FAISS_DIR
from pdf_loader import load_all_pdfs, chunk_documents


def build_faiss_index():
    """
    PDF'leri oku → chunk'la → embed et → FAISS'e yaz.
    
    Bu fonksiyon iki dosya üretir:
    - faiss_index/index.faiss  → vektör veritabanı
    - faiss_index/index.pkl    → metadata
    - faiss_index/chunks_meta.json → BM25 için ham chunk verileri
    """
    
    # Adım 1: PDF'leri oku
    print("\n" + "=" * 50)
    print("  Adım 1/3: PDF'ler okunuyor...")
    print("=" * 50)
    documents = load_all_pdfs()
    
    if not documents:
        print("\nHiç belge bulunamadı! Önce docs/ klasörüne PDF koy.")
        return None
    
    # Adım 2: Chunk'la
    print("\n" + "=" * 50)
    print("  Adım 2/3: Chunk'lara bölünüyor...")
    print("=" * 50)
    chunks = chunk_documents(documents)
    
    # Adım 3: Embedding ve FAISS
    print("\n" + "=" * 50)
    print("  Adım 3/3: Vektörlere dönüştürülüyor...")
    print("=" * 50)
    print(f"  Model: {EMBEDDING_MODEL}")
    print(f"  (İlk seferde model indirilecek, ~500MB, 2-5 dk bekle)")
    
    # Embedding modelini yükle
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    
    # Chunk'ları LangChain Document formatına çevir
    lc_docs = [
        Document(
            page_content=c["text"],
            metadata=c["metadata"]
        )
        for c in chunks
    ]
    
    # FAISS indeksini oluştur (embedding + indexing)
    print(f"\n  {len(lc_docs)} chunk embed ediliyor...")
    t0 = time.time()
    
    vectorstore = FAISS.from_documents(lc_docs, embeddings)
    
    elapsed = time.time() - t0
    print(f"  Tamamlandı! ({elapsed:.1f} saniye)")
    
    # Diske kaydet
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(FAISS_DIR))
    print(f"\n  FAISS indeksi kaydedildi: {FAISS_DIR}")
    
    # BM25 sparse arama için chunk metadata'sını da kaydet
    meta_path = FAISS_DIR / "chunks_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"  Chunk metadata kaydedildi: {meta_path}")
    
    # Özet
    print(f"\n{'=' * 50}")
    print(f"  BİLGİ TABANI HAZIR!")
    print(f"  Toplam belge: {len(documents)}")
    print(f"  Toplam chunk: {len(chunks)}")
    print(f"  Vektör sayısı: {vectorstore.index.ntotal}")
    print(f"{'=' * 50}")
    
    return vectorstore


def load_faiss_index():
    """
    Mevcut FAISS indeksini diskten yükle.
    build_faiss_index() çalıştırdıktan sonra bunu kullan.
    
    Returns:
        (vectorstore, chunks) → FAISS nesnesi ve ham chunk listesi
    """
    index_path = FAISS_DIR / "index.faiss"
    meta_path = FAISS_DIR / "chunks_meta.json"
    
    if not index_path.exists():
        print("[HATA] FAISS indeksi bulunamadı!")
        print("Önce build_index.py'yi çalıştır.")
        return None, None
    
    # Embedding modelini yükle (aynı model olmalı!)
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    
    # FAISS'i diskten oku
    vectorstore = FAISS.load_local(
        str(FAISS_DIR),
        embeddings,
        allow_dangerous_deserialization=True,  # kendi oluşturduğumuz dosya, güvenli
    )
    
    # BM25 için chunk metadata'sını oku
    chunks = []
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    
    print(f"FAISS indeksi yüklendi: {vectorstore.index.ntotal} vektör, {len(chunks)} chunk")
    
    return vectorstore, chunks


# ============================================================
# Doğrudan çalıştırılırsa indeksi oluştur
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("  TRAK-AI KDS — Bilgi Tabanı Oluşturucu")
    print("=" * 50)
    
    build_faiss_index()