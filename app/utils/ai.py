import os
from typing import List, Optional
import google.generativeai as genai

_configured = False

def _ensure_config():
    global _configured
    if _configured:
        return
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY env var not set")
    genai.configure(api_key=api_key)
    _configured = True


def generate_text(prompt: str, system: Optional[str] = None) -> str:
    _ensure_config()
    model = genai.GenerativeModel("gemini-2.5-flash")

    parts = []
    if system:
        parts.append({"text": system})
    parts.append({"text": prompt})

    resp = model.generate_content(
        [{"role": "user", "parts": parts}]
    )
    return resp.text or ""


def generate_json(prompt: str) -> str:
    _ensure_config()
    model = genai.GenerativeModel("gemini-2.5-flash")
    resp = model.generate_content([{"role": "user", "parts": [{"text": prompt}]}])
    return resp.text or ""


def vision_analyze(image_bytes: bytes, prompt: str) -> str:
    _ensure_config()
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )

    resp = model.generate_content([
        {
            "role": "user",
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_bytes
                    }
                }
            ]
        }
    ])

    return resp.text or ""



def embed_texts(texts: List[str]) -> List[List[float]]:
    _ensure_config()
    vectors = []
    for t in texts:
        resp = genai.embed_content(model="text-embedding-004", content=t)
        if isinstance(resp, dict) and "embedding" in resp:
            vectors.append(resp["embedding"])
        else:
            vectors.append(getattr(resp, "embedding", []))
    return vectors
