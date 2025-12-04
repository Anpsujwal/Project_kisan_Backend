from io import BytesIO
from typing import Optional

import subprocess
import numpy as np
import soundfile as sf
import speech_recognition as sr


def _to_wav_bytes(audio_bytes: bytes, mime_type: Optional[str]) -> bytes:
    """Return 16kHz mono WAV bytes from arbitrary input using soundfile or ffmpeg fallback."""
    # If already wav, try to resample/channel adjust via soundfile
    if mime_type and mime_type.endswith("wav"):
        try:
            data_io = BytesIO(audio_bytes)
            audio, sr_in = sf.read(data_io, dtype="float32", always_2d=True)
            # Convert to mono by averaging channels
            mono = audio.mean(axis=1)
            out = BytesIO()
            sf.write(out, mono, 16000, format="WAV", subtype="PCM_16")
            return out.getvalue()
        except Exception:
            # If soundfile can't parse, fall through to ffmpeg
            pass

    # First attempt: decode using soundfile directly (works for wav/flac/ogg, etc.)
    try:
        data_io = BytesIO(audio_bytes)
        audio, sr_in = sf.read(data_io, dtype="float32", always_2d=True)
        mono = audio.mean(axis=1)
        # Resample if needed using numpy (simple linear interpolation)
        if sr_in != 16000:
            # Compute resample ratio
            ratio = 16000 / float(sr_in)
            x_old = np.arange(len(mono))
            x_new = np.linspace(0, len(mono) - 1, int(len(mono) * ratio))
            mono = np.interp(x_new, x_old, mono).astype(np.float32)
        out = BytesIO()
        sf.write(out, mono, 16000, format="WAV", subtype="PCM_16")
        return out.getvalue()
    except Exception:
        # Fallback: use ffmpeg (must be installed on system PATH)
        try:
            proc = subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    "pipe:0",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-f",
                    "wav",
                    "pipe:1",
                ],
                input=audio_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            return proc.stdout
        except Exception:
            # Last resort: return original bytes
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
