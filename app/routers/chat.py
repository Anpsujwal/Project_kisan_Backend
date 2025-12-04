import base64
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from ..db.database import chats_col, memories_col
from ..utils import stt
from ..utils.ai import generate_text

router = APIRouter()


def _tts_data_url(text: str) -> str:
    try:
        from gtts import gTTS
        buf = bytearray()
        tts = gTTS(text=text, lang="en")
        import io
        bio = io.BytesIO()
        tts.write_to_fp(bio)
        audio_bytes = bio.getvalue()
        b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return f"data:audio/mpeg;base64,{b64}"
    except Exception:
        return ""


def _get_user_preamble(user_id: Optional[str]) -> str:
    if not user_id:
        return ""
    mem = memories_col().find_one({"userId": user_id}) or {}
    profile = mem.get("profile", {})
    crops = ", ".join(profile.get("crops", []) or [])
    soil = profile.get("soilType") or ""
    lang = profile.get("preferredLanguage") or "en"
    return (
        "You are Project Kisan assistant. Personalize responses.\n"
        f"Preferred language: {lang}.\n"
        f"Crops: {crops}. Soil: {soil}.\n"
    )


@router.post("/chat/send")
async def send_message(
    text: Optional[str] = Form(default=None),
    user_id: Optional[str] = Form(default=None),
    audio: Optional[UploadFile] = File(default=None),
):
    query_text = text or ""
    if audio is not None:
        data = await audio.read()
        query_text = stt.transcribe_audio(data, audio.content_type) or query_text

    preamble = _get_user_preamble(user_id)
    prompt = f"{preamble}\nUser: {query_text}\nAssistant:"
    reply = generate_text(prompt)

    # Save chat
    chats_col().insert_one({
        "userId": user_id,
        "query": query_text,
        "response": reply,
        "ts": datetime.utcnow(),
    })

    # very simple memory update: store last chat summary
    if user_id:
        memories_col().update_one(
            {"userId": user_id},
            {"$set": {"lastSummary": reply[:500]}},
            upsert=True,
        )

    audio_url = _tts_data_url(reply)
    return {"text": reply, "audioUrl": audio_url}


@router.get("/chat/history")
async def chat_history(user_id: Optional[str] = None):
    q = {}
    if user_id:
        q["userId"] = user_id
    items = list(chats_col().find(q).sort("ts", -1).limit(50))
    for it in items:
        it["_id"] = str(it["_id"])  # make JSON safe
    return {"items": items}
