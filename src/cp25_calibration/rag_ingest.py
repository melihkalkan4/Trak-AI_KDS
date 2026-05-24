"""ÇP-2.5 — TÜİK verim chunk'larını FAISS index'ine ekler.

Idempotent: aynı ``chunk_id`` zaten chunks_meta.json'da varsa atlar.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger("trakai.cp25.rag")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAG_DIR  = PROJECT_ROOT / "src" / "cp4_rag"
SRC_PATH = str(RAG_DIR)
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# Late import — relies on cp4_rag config
from langchain_huggingface import HuggingFaceEmbeddings           # noqa: E402
from langchain_community.vectorstores import FAISS                # noqa: E402
from langchain_core.documents import Document                     # noqa: E402
from config import EMBEDDING_MODEL, FAISS_DIR                     # noqa: E402


CHUNKS_PATH = PROJECT_ROOT / "data" / "external" / "tuik" / "rag_chunks_yield.json"


def _load_tuik_chunks() -> list[dict]:
    with CHUNKS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _existing_chunk_ids(meta_path: Path) -> set[str]:
    if not meta_path.exists():
        return set()
    try:
        existing = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:                                              # noqa: BLE001
        return set()
    ids = set()
    for c in existing:
        meta = c.get("metadata", {}) or {}
        if meta.get("chunk_id_external"):
            ids.add(str(meta["chunk_id_external"]))
    return ids


def main() -> None:
    chunks = _load_tuik_chunks()
    logger.info("loaded %d TÜİK chunks from %s", len(chunks), CHUNKS_PATH.name)

    meta_path = FAISS_DIR / "chunks_meta.json"
    already = _existing_chunk_ids(meta_path)
    logger.info("existing TÜİK chunk_ids in FAISS meta: %d", len(already))

    new_docs: list[Document] = []
    new_meta: list[dict] = []
    for c in chunks:
        cid = c.get("chunk_id", "")
        if cid in already:
            logger.info("skip (already present): %s", cid)
            continue
        meta = {
            "source": f"TUIK_{c.get('il','?')}_{c.get('urun','?')}",
            "category": "yield_statistics",
            "language": "tr",
            "chunk_id_external": cid,
            "il": c.get("il"),
            "urun": c.get("urun"),
            "kaynak": c.get("kaynak", "TÜİK"),
            "metric_type": c.get("metric_type", ""),
        }
        new_docs.append(Document(page_content=c["text"], metadata=meta))
        new_meta.append({"text": c["text"], "metadata": meta})

    if not new_docs:
        logger.info("nothing to ingest; all %d TÜİK chunks already present", len(chunks))
        return

    logger.info("embedding model = %s", EMBEDDING_MODEL)
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )

    if (FAISS_DIR / "index.faiss").exists():
        logger.info("loading existing FAISS index from %s", FAISS_DIR)
        vs = FAISS.load_local(str(FAISS_DIR), embeddings,
                              allow_dangerous_deserialization=True)
        n_before = vs.index.ntotal
        vs.add_documents(new_docs)
        logger.info("FAISS vectors %d → %d (+%d)", n_before, vs.index.ntotal, len(new_docs))
    else:
        logger.info("no existing index; building fresh with %d chunks only", len(new_docs))
        vs = FAISS.from_documents(new_docs, embeddings)

    vs.save_local(str(FAISS_DIR))
    logger.info("saved FAISS → %s", FAISS_DIR)

    # Append to chunks_meta.json (preserve existing)
    if meta_path.exists():
        existing = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        existing = []
    existing.extend(new_meta)
    meta_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    logger.info("appended %d entries to %s", len(new_meta), meta_path.name)


if __name__ == "__main__":
    main()
