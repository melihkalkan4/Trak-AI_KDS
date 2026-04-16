"""
TRAK-AI KDS — PDF Yükleyici ve Chunk'lama Modülü
==================================================
Bu modül şunları yapar:
1. docs/ klasöründeki tüm PDF'leri okur
2. Her PDF'den metni çıkarır (PyMuPDF ile)
3. Metni küçük parçalara (chunk) böler
4. Her chunk'a kaynak bilgisi (metadata) ekler
"""
import fitz  # PyMuPDF — PDF okuma kütüphanesi
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter

from config import DOCS_DIR, CHUNK_SIZE, CHUNK_OVERLAP


def load_all_pdfs() -> list:
    """
    docs/ klasöründeki TÜM PDF'leri oku ve metin çıkar.
    
    Returns:
        list: Her eleman bir dict: {"text": "...", "source": "dosya.pdf", "category": "fao"}
    """
    documents = []
    
    # docs/ altındaki tüm .pdf dosyalarını bul (alt klasörler dahil)
    pdf_files = list(DOCS_DIR.rglob("*.pdf"))
    
    if not pdf_files:
        print(f"\n[UYARI] Hiç PDF bulunamadı!")
        print(f"PDF'leri şu klasörlere koy:")
        print(f"  {DOCS_DIR / 'bbch/'}")
        print(f"  {DOCS_DIR / 'tr_bakanlik/'}")
        print(f"  {DOCS_DIR / 'fao/'}")
        print(f"  {DOCS_DIR / 'abd/'}")
        print(f"  {DOCS_DIR / 'hastalik/'}")
        return documents
    
    print(f"\n{len(pdf_files)} PDF bulundu, okunuyor...")
    
    for pdf_path in pdf_files:
        try:
            # PDF'i aç ve tüm sayfaların metnini birleştir
            doc = fitz.open(str(pdf_path))
            text = ""
            for page in doc:
                text += page.get_text()
            page_count = len(doc)
            doc.close()
            
            # Çok kısa dosyaları atla (muhtemelen sadece resim)
            if len(text.strip()) < 100:
                print(f"  [ATLANDI] {pdf_path.name} (metin çok kısa, muhtemelen taranmış görüntü)")
                continue
            
            # Kategoriyi klasör adından al (fao, bbch, tr_bakanlik vb.)
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
    """
    Belgeleri küçük parçalara (chunk) böl.
    
    Neden chunk'lıyoruz?
    - LLM'in context window'u sınırlı (4096 token)
    - Küçük parçalar daha isabetli arama sonucu verir
    - Her chunk kendi kaynak bilgisini taşır
    
    Args:
        documents: load_all_pdfs()'den gelen belge listesi
        
    Returns:
        list: Her eleman {"text": "chunk metni", "metadata": {source, category, chunk_id}}
    """
    # LangChain'in akıllı metin bölücüsü
    # Önce paragraf sonlarından, sonra cümle sonlarından, sonra boşluklardan böler
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    
    all_chunks = []
    
    for doc in documents:
        # Bu belgeyi chunk'lara böl
        chunks = splitter.split_text(doc["text"])
        
        # Her chunk'a metadata ekle (sonra "bu bilgi nereden geldi?" diyebilmek için)
        for i, chunk_text in enumerate(chunks):
            all_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": doc["source"],       # hangi PDF'den geldi
                    "category": doc["category"],   # hangi kategori (fao, bbch vb.)
                    "chunk_id": i,                 # bu PDF'deki kaçıncı parça
                    "total_chunks": len(chunks),   # bu PDF toplam kaç parçaya bölündü
                },
            })
    
    print(f"\n{len(documents)} belgeden toplam {len(all_chunks)} chunk oluşturuldu.")
    
    # Kategori bazında özet göster
    categories = {}
    for c in all_chunks:
        cat = c["metadata"]["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    print("Kategori dağılımı:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} chunk")
    
    return all_chunks


# ============================================================
# Doğrudan çalıştırılırsa test et
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("  TRAK-AI KDS — PDF Yükleme Testi")
    print("=" * 50)
    
    docs = load_all_pdfs()
    
    if docs:
        chunks = chunk_documents(docs)
        
        # İlk chunk'ı göster (kontrol amaçlı)
        print(f"\nÖrnek chunk (ilk 200 karakter):")
        print(f"  Kaynak: {chunks[0]['metadata']['source']}")
        print(f"  Metin: {chunks[0]['text'][:200]}...")