from typing import List, Optional

import chromadb
from fastapi import APIRouter, Query

from ..utils.ai import embed_texts, generate_text

router = APIRouter()

_client = None
_collection = None
_seeded = False


def _ensure_collection():
    global _client, _collection
    if _client is None or _collection is None:
        _client = chromadb.Client()
        _collection = _client.get_or_create_collection(name="schemes")


def _seed_if_needed():
    global _seeded
    if _seeded:
        return
    _ensure_collection()
    # Minimal seed examples (public generic info)
    docs = [
        {
            "id": "pmfby",
            "title": "Pradhan Mantri Fasal Bima Yojana",
            "text": "Crop insurance scheme for farmers covering yield losses due to natural calamities. Eligibility: all farmers with insurable interest. Benefits: subsidized premium, claim support. Apply via bank/CSC portals.",
            "category": "Insurance",
            "state": "All India",
            "link": "https://pmfby.gov.in/",
        },
        {
            "id": "pmksy",
            "title": "Pradhan Mantri Krishi Sinchai Yojana",
            "text": "Irrigation scheme promoting 'Har Khet Ko Pani' and micro-irrigation. Eligibility: farmers, SHGs. Benefits: assistance for irrigation infrastructure. Apply via state agriculture department.",
            "category": "Subsidy",
            "state": "All India",
            "link": "https://pmksy.gov.in/",
        },
    ]
    embeddings = embed_texts([d["text"] for d in docs])
    _collection.add(
        ids=[d["id"] for d in docs],
        embeddings=embeddings,
        documents=[d["text"] for d in docs],
        metadatas=[{"title": d["title"], "category": d["category"], "state": d["state"], "link": d["link"]} for d in docs],
    )
    _seeded = True


@router.get("/schemes/search")
async def search_schemes(
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
):
    _ensure_collection()
    _seed_if_needed()
    query = q or "farmer subsidy"
    query_embed = embed_texts([query])[0]
    res = _collection.query(query_embeddings=[query_embed], n_results=5)
    items: List[dict] = []
    for i in range(len(res.get("ids", [[]])[0])):
        meta = res["metadatas"][0][i]
        doc = res["documents"][0][i]
        if category and meta.get("category") and meta.get("category").lower() != category.lower():
            continue
        if state and meta.get("state") and state.lower() not in meta.get("state").lower():
            continue
        # Summarize into structured fields with Gemini
        answer = generate_text(
            f"From this scheme info: {doc}. Provide a concise JSON with keys: title, eligibility, benefits, how_to_apply, link if available."
        )
        item = {"title": meta.get("title"), "link": meta.get("link")}
        try:
            import json
            parsed = json.loads(answer)
            if isinstance(parsed, dict):
                item.update(
                    {
                        "eligibility": parsed.get("eligibility"),
                        "benefits": parsed.get("benefits"),
                        "how_to_apply": parsed.get("how_to_apply"),
                    }
                )
        except Exception:
            pass
        items.append(item)
    return {"items": items}
