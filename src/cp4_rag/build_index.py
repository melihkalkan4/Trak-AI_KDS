"""
TRAK-AI KDS — FAISS Vektör İndeks Oluşturucu
==============================================
Chunk'ları vektöre çevirip FAISS'e yazar.
"""
import json
import time
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from config import EMBEDDING_MODEL, FAISS_DIR
from pdf_loader import load_all_pdfs, chunk_documents


def build_faiss_index():
    """PDF'leri oku → chunk'la → embed et → FAISS'e yaz."""

    print("\n" + "=" * 50)
    print("  Adım 1/3: PDF'ler okunuyor...")
    print("=" * 50)
    documents = load_all_pdfs()

    if not documents:
        print("\nHiç belge bulunamadı! Önce docs/ klasörüne PDF koy.")
        return None

    print("\n" + "=" * 50)
    print("  Adım 2/3: Chunk'lara bölünüyor...")
    print("=" * 50)
    chunks = chunk_documents(documents)

    print("\n" + "=" * 50)
    print("  Adım 3/3: Vektörlere dönüştürülüyor...")
    print("=" * 50)
    print(f"  Model: {EMBEDDING_MODEL}")
    print(f"  (İlk seferde model indirilecek, ~500MB, 2-5 dk bekle)")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    lc_docs = [
        Document(page_content=c["text"], metadata=c["metadata"])
        for c in chunks
    ]

    print(f"\n  {len(lc_docs)} chunk embed ediliyor...")
    t0 = time.time()

    vectorstore = FAISS.from_documents(lc_docs, embeddings)

    elapsed = time.time() - t0
    print(f"  Tamamlandı! ({elapsed:.1f} saniye)")

    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(FAISS_DIR))
    print(f"\n  FAISS indeksi kaydedildi: {FAISS_DIR}")

    meta_path = FAISS_DIR / "chunks_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"  Chunk metadata kaydedildi: {meta_path}")

    print(f"\n{'=' * 50}")
    print(f"  BİLGİ TABANI HAZIR!")
    print(f"  Toplam belge: {len(documents)}")
    print(f"  Toplam chunk: {len(chunks)}")
    print(f"  Vektör sayısı: {vectorstore.index.ntotal}")
    print(f"{'=' * 50}")

    return vectorstore


def load_faiss_index():
    """Mevcut FAISS indeksini diskten yükle."""
    index_path = FAISS_DIR / "index.faiss"
    meta_path = FAISS_DIR / "chunks_meta.json"

    if not index_path.exists():
        print("[HATA] FAISS indeksi bulunamadı! Önce build çalıştır.")
        return None, None

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = FAISS.load_local(
        str(FAISS_DIR), embeddings,
        allow_dangerous_deserialization=True,
    )

    chunks = []
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)

    print(f"FAISS indeksi yüklendi: {vectorstore.index.ntotal} vektör, {len(chunks)} chunk")
    return vectorstore, chunks


if __name__ == "__main__":
    build_faiss_index()