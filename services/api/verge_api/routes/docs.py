"""Document intelligence API — ingest, list, entities, grounded ask."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from verge_docintel import DocIntelStore, process_bytes
from verge_docintel.pipeline import chunk_text
from verge_llm import Message, provider_from_env

router = APIRouter(tags=["knowledge"])
DOC_FILE = File(...)
TITLE_FORM = Form(None)
PLANT_PACK_FORM = Form(None)


def _store(request: Request) -> DocIntelStore:
    store = getattr(request.app.state, "docintel", None)
    if store is None:
        store = DocIntelStore()
        request.app.state.docintel = store
    return store


@router.get("/docs")
def list_docs(request: Request) -> dict:
    store = _store(request)
    docs = [d.model_dump(by_alias=True, mode="json") for d in store.list_documents()]
    return {"documents": docs, "count": len(docs)}


@router.get("/docs/{document_id}")
def get_doc(document_id: str, request: Request) -> dict:
    store = _store(request)
    doc = store.get(document_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    chunks = [c.model_dump(by_alias=True, mode="json") for c in store.chunks.get(document_id, [])]
    entities = [
        e.model_dump(by_alias=True, mode="json") for e in store.entities.get(document_id, [])
    ]
    return {
        "document": doc.model_dump(by_alias=True, mode="json"),
        "chunks": chunks,
        "entities": entities,
    }


@router.post("/docs/ingest")
async def ingest_doc(
    request: Request,
    file: UploadFile = DOC_FILE,
    title: str | None = TITLE_FORM,
    plantPack: str | None = PLANT_PACK_FORM,
) -> dict:
    store = _store(request)
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty upload")
    asset = process_bytes(
        store,
        data,
        filename=file.filename or "upload.bin",
        mime_type=file.content_type or "application/octet-stream",
        title=title,
        plant_pack=plantPack,
    )
    return {
        "document": asset.model_dump(by_alias=True, mode="json"),
        "entityCount": len(store.entities.get(asset.document_id, [])),
        "chunkCount": len(store.chunks.get(asset.document_id, [])),
    }


class AskBody(BaseModel):
    query: str = Field(min_length=2)
    limit: int = Field(default=6, ge=1, le=20)


def _retrieve(store: DocIntelStore, query: str, *, limit: int) -> list[dict]:
    q = query.lower().split()
    scored: list[tuple[int, dict]] = []
    for doc_id, chunks in store.chunks.items():
        doc = store.documents.get(doc_id)
        for ch in chunks:
            text = ch.text.lower()
            score = sum(1 for tok in q if tok in text)
            if score:
                scored.append(
                    (
                        score,
                        {
                            "documentId": doc_id,
                            "title": doc.title if doc else doc_id,
                            "chunkId": ch.chunk_id,
                            "page": ch.page,
                            "excerpt": ch.text[:500],
                            "score": score,
                        },
                    )
                )
    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored[:limit]]


@router.post("/knowledge/ask")
def knowledge_ask(body: AskBody, request: Request) -> dict:
    """Grounded answer over ingested documents — refuse when corpus is empty."""
    store = _store(request)
    citations = _retrieve(store, body.query, limit=body.limit)
    if not citations:
        return {
            "answer": "",
            "citations": [],
            "degraded": True,
            "reason": "no-matching-chunks" if store.documents else "empty-corpus",
        }

    facts = "\n\n".join(
        f"[{i + 1}] ({c['title']}) {c['excerpt']}" for i, c in enumerate(citations)
    )
    llm = getattr(request.app.state, "llm", None) or provider_from_env()
    prompt = (
        "Answer ONLY from the numbered facts. If insufficient, say you cannot answer "
        "from the corpus. Cite fact numbers like [1].\n\n"
        f"Question: {body.query}\n\nFacts:\n{facts}"
    )
    completion = llm.complete([Message(role="user", content=prompt)])
    if completion.degraded or not (completion.text or "").strip():
        # Deterministic fallback: stitch top excerpts — never invent.
        answer = "Based on retrieved documents:\n" + "\n".join(
            f"- [{i + 1}] {c['excerpt'][:240]}" for i, c in enumerate(citations[:3])
        )
        return {
            "answer": answer,
            "citations": citations,
            "degraded": True,
            "reason": "llm-degraded",
        }
    return {
        "answer": completion.text.strip(),
        "citations": citations,
        "degraded": False,
        "reason": "",
    }


# Keep chunk_text imported for potential future reprocess route.
_ = chunk_text
