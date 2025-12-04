from io import BytesIO
from typing import Optional

from pydub import AudioSegment
import speech_recognition as sr


def _to_wav_bytes(audio_bytes: bytes, mime_type: Optional[str]) -> bytes:
    # Try to convert whatever is provided to wav (16k mono)
    data = BytesIO(audio_bytes)
    if mime_type and mime_type.endswith("wav"):
        return audio_bytes
    try:
        seg = AudioSegment.from_file(data)
        seg = seg.set_channels(1).set_frame_rate(16000)
        out = BytesIO()
        seg.export(out, format="wav")
        return out.getvalue()
    except Exception:
        # Fallback: return original
        return audio_bytes


def transcribe_audio(audio_bytes: bytes, mime_type: Optional[str] = None) -> str:
    wav = _to_wav_bytes(audio_bytes, mime_type)
    recognizer = sr.Recognizer()
    with sr.AudioFile(BytesIO(wav)) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio)
    except Exception:
        return ""
