from fastapi import APIRouter, File, Form, UploadFile
from ..utils.ai import vision_analyze

router = APIRouter()


@router.post("/disease/analyze")
async def analyze_disease(
    image: UploadFile = File(...),
    crop: str | None = Form(None),
    symptoms: str | None = Form(None),
):
    img_bytes = await image.read()

    prompt = (
        "You are an agronomist. Analyze the crop disease from the image. "
        "Return STRICT JSON ONLY in this exact format:\n"
        "{"
        "\"disease\": \"string\","
        "\"confidence\": number,"
        "\"treatment\": \"string\","
        "\"pesticides\": [\"string\", \"string\"],"
        "\"prevention\": \"string\""
        "}\n"
        f"Crop: {crop or ''}. Symptoms: {symptoms or ''}."
    )


    text = vision_analyze(img_bytes, prompt)

    result = {
        "disease": None,
        "confidence": None,
        "treatment": None,
        "pesticides": [],
        "prevention": None,
    }

    # 1) try full JSON
    try:
        import json
        data = json.loads(text)
        if isinstance(data, dict):
            result.update({k: data.get(k) for k in result.keys()})
            return result
    except:
        pass

    # 2) try to extract "disease" heuristically
    import re
    m = re.search(r'"disease"\s*:\s*"([^"]+)"', text)
    if m:
        result["disease"] = m.group(1)
    else:
        result["disease"] = "Possible disease detected"

    return result
