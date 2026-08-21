from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, KBDocument, KBChunk
from app.schemas import KBDocumentResponse
from app.auth import get_current_user, get_admin_user
from app.rag import extract_text_from_file, chunk_text, rag_engine

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])

@router.post("/upload", response_model=KBDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    source_type: str = "Clinical Guideline",
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    filename = file.filename
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ["txt", "md", "pdf"]:
        raise HTTPException(status_code=400, detail="Only .txt, .md, and .pdf files are supported")

    content_bytes = await file.read()
    raw_text = extract_text_from_file(filename, content_bytes)
    
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Document appears to be empty or unreadable")

    chunks = chunk_text(raw_text)
    if not chunks:
        raise HTTPException(status_code=400, detail="Could not extract meaningful text chunks from file")

    doc = KBDocument(
        filename=filename,
        file_type=ext,
        chunk_count=len(chunks),
        source_type=source_type,
        uploaded_by_id=admin_user.id
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

    # Immediately rebuild RAG vectorizer index
    rag_engine.is_dirty = True
    rag_engine.rebuild_index(db)

    return KBDocumentResponse.model_validate(doc)

@router.get("/documents", response_model=List[KBDocumentResponse])
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = db.query(KBDocument).order_by(KBDocument.created_at.desc()).all()
    return docs

@router.delete("/documents/{id}")
def delete_document(
    id: int,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    doc = db.query(KBDocument).filter(KBDocument.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(doc)
    db.commit()

    # Rebuild RAG index after document removal
    rag_engine.is_dirty = True
    rag_engine.rebuild_index(db)

    return {"message": "Document deleted and index updated successfully"}
