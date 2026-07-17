from verge_docintel import extract_entities, process_bytes
from verge_docintel.pipeline import DocIntelStore
from verge_schema.documents import DocumentStatus, EntityKind


def test_extract_equipment_and_zone() -> None:
    text = "Isolate PUMP-3 in zone B-04 before hot work. See OISD-STD-105 and PW-2025-0142."
    ents = extract_entities(text, document_id="DOC-1")
    kinds = {e.kind for e in ents}
    assert EntityKind.EQUIPMENT in kinds
    assert EntityKind.ZONE in kinds
    assert EntityKind.CLAUSE in kinds
    assert EntityKind.PERMIT in kinds


def test_process_text_document() -> None:
    store = DocIntelStore()
    body = b"""Hot Work SOP

Before welding near LEL-04 in B-04, confirm permit PW-0142 and isolate P-3.
Reference OISD-STD-105 section 4.2.
"""
    asset = process_bytes(store, body, filename="hot-work-sop.md", mime_type="text/markdown")
    assert asset.status == DocumentStatus.READY
    assert asset.kind.value == "sop"
    assert store.chunks[asset.document_id]
    assert store.entities[asset.document_id]
