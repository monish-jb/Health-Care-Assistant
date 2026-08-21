"""
Automatic Seed Script for Healthcare Knowledge Navigator KB.
Populates preprocessed medical guidelines and laboratory reference documents into SQLite DB and rebuilds TF-IDF index.
"""

import os
import sys
from sqlalchemy.orm import Session

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models import KBDocument, KBChunk, User
from app.rag import extract_text_from_file, chunk_text, rag_engine

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def seed_medical_knowledge_base():
    db: Session = SessionLocal()
    try:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "medical_kb")
        if not os.path.exists(data_dir):
            print(f"Directory {data_dir} does not exist. Skipping seeding.")
            return

        admin_user = db.query(User).filter(User.role == "admin").first()
        admin_id = admin_user.id if admin_user else None

        files = sorted(os.listdir(data_dir))
        added_count = 0

        for fname in files:
            if not fname.endswith(".md") and not fname.endswith(".txt"):
                continue

            # Check if document already present
            existing = db.query(KBDocument).filter(KBDocument.filename == fname).first()
            if existing:
                print(f"[SKIP] Document '{fname}' already present in Knowledge Base (ID: {existing.id})")
                continue

            fpath = os.path.join(data_dir, fname)
            with open(fpath, "rb") as f:
                content_bytes = f.read()

            raw_text = extract_text_from_file(fname, content_bytes)
            if not raw_text.strip():
                continue

            chunks = chunk_text(raw_text)
            if not chunks:
                continue

            source_type = "Clinical Guideline"
            if "laboratory" in fname.lower() or "reference" in fname.lower():
                source_type = "Health Authority"
            elif "pharmacology" in fname.lower():
                source_type = "Clinical Reference"

            doc = KBDocument(
                filename=fname,
                file_type=fname.split(".")[-1],
                chunk_count=len(chunks),
                source_type=source_type,
                uploaded_by_id=admin_id
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            for idx, c in enumerate(chunks):
                chunk_obj = KBChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    section_name=c.get("section", "General Overview"),
                    content=c["content"]
                )
                db.add(chunk_obj)

            db.commit()
            added_count += 1
            print(f"[SUCCESS] Ingested '{fname}' ({len(chunks)} chunks, Source Type: {source_type})")

        # Rebuild RAG index
        rag_engine.is_dirty = True
        rag_engine.rebuild_index(db)
        print(f"\n==================================================")
        print(f"HEALTHCARE KNOWLEDGE BASE INGESTION COMPLETE!")
        print(f"Ingested {added_count} new medical document(s).")
        print(f"Total Chunks in RAG Vector Space: {len(rag_engine.chunk_ids)}")
        print(f"==================================================")

    except Exception as e:
        print(f"Error seeding medical KB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_medical_knowledge_base()
