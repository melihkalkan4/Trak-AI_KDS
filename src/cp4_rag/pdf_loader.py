"""
TRAK-AI KDS — PDF Yükleyici ve Chunk'lama Modülü
==================================================
docs/ klasöründeki PDF'leri okur, metin çıkarır, chunk'lara böler.
"""
import fitz
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import DOCS_DIR, CHUNK_SIZE, CHUNK_OVERLAP


def load_all_pdfs() -> list:
    """docs/ altındaki tüm PDF'leri oku ve metin çıkar."""
    documents = []
    pdf_files = list(DOCS_DIR.rglob("*.pdf"))

    if not pdf_files:
        print(f"\n[UYARI] Hiç PDF bulunamadı!")
        print(f"PDF'leri şu klasörlere koy:")
        print(f"  {DOCS_DIR / 'bbch'}")
        print(f"  {DOCS_DIR / 'tr_bakanlik'}")
        print(f"  {DOCS_DIR / 'fao'}")
        print(f"  {DOCS_DIR / 'abd'}")
        print(f"  {DOCS_DIR / 'hastalik'}")
        return documents

    print(f"\n{len(pdf_files)} PDF bulundu, okunuyor...")

    for pdf_path in pdf_files:
        try:
            doc = fitz.open(str(pdf_path))
            text = ""
            for page in doc:
                text += page.get_text()
            page_count = len(doc)
            doc.close()

            if len(text.strip()) < 100:
                print(f"  [ATLANDI] {pdf_path.name} (metin çok kısa)")
                continue

            category = pdf_path.parent.name

            documents.append({
                "text": text,
                "source": pdf_path.name,
                "category": category,
                "pages": page_count,
            })

            print(f"  [OK] {pdf_path.name} — {page_count} sayfa, {len(text):,} karakter")

        except Exception as e:
            print(f"  [HATA] {pdf_path.name}: {e}")

    print(f"\nToplam {len(documents)} belge başarıyla yüklendi.")
    return documents


def chunk_documents(documents: list) -> list:
    """Belgeleri küçük parçalara (chunk) böl."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    all_chunks = []

    for doc in documents:
        chunks = splitter.split_text(doc["text"])

        for i, chunk_text in enumerate(chunks):
            all_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": doc["source"],
                    "category": doc["category"],
                    "chunk_id": i,
                    "total_chunks": len(chunks),
                },
            })

    print(f"\n{len(documents)} belgeden toplam {len(all_chunks)} chunk oluşturuldu.")

    categories = {}
    for c in all_chunks:
        cat = c["metadata"]["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print("Kategori dağılımı:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} chunk")

    return all_chunks


if __name__ == "__main__":
    docs = load_all_pdfs()
    if docs:
        chunks = chunk_documents(docs)
        print(f"\nÖrnek chunk: {chunks[0]['text'][:200]}...")