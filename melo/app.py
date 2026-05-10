import gc
import io
import json
import logging
import os
from pathlib import Path

import soundfile as sf
import torch
from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from melo.api import TTS
from melo.split_utils import split_sentence


APP_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = Path(__file__).resolve().parent / "web"


def _read_non_empty_env(name: str):
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _load_build_metadata():
    metadata_path = _read_non_empty_env("BUILD_METADATA_PATH") or str(
        APP_ROOT / ".build_meta.json"
    )
    try:
        with open(metadata_path, "r", encoding="utf-8") as metadata_file:
            data = json.load(metadata_file)
            if isinstance(data, dict):
                return data
    except FileNotFoundError:
        pass
    except Exception as error:
        logging.getLogger("TTSApp").warning(
            f"Unable to read build metadata from {metadata_path}: {error}"
        )
    return {}


def _load_version_from_file():
    version_file_path = _read_non_empty_env("VERSION_FILE_PATH") or str(APP_ROOT / "VERSION")
    try:
        with open(version_file_path, "r", encoding="utf-8") as version_file:
            version = version_file.read().strip()
            return version or None
    except FileNotFoundError:
        pass
    except Exception as error:
        logging.getLogger("TTSApp").warning(
            f"Unable to read version file at {version_file_path}: {error}"
        )
    return None


def _resolve_runtime_version_and_build():
    metadata = _load_build_metadata()
    version = _load_version_from_file() or metadata.get("app_version") or "0.0.0-SNAPSHOT"
    build_id = metadata.get("build_id") or _read_non_empty_env("BUILD_ID") or "local-dev"
    return version, build_id


VERSION, BUILD_ID = _resolve_runtime_version_and_build()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("TTSApp")
logger.info(f"Starting TTS UI+API App - Version: {VERSION}, Build: {BUILD_ID}")


def validate_nltk_resources(required_languages):
    if not any(lang.startswith("EN") for lang in required_languages):
        return

    try:
        import nltk
    except Exception as error:
        raise RuntimeError(f"Failed to import nltk for EN startup validation: {error}") from error

    required = [
        ("taggers/averaged_perceptron_tagger_eng", "averaged_perceptron_tagger_eng"),
        ("corpora/cmudict", "cmudict"),
    ]
    missing = []
    for resource_path, resource_name in required:
        try:
            nltk.data.find(resource_path)
        except LookupError:
            missing.append(resource_name)

    if missing:
        raise RuntimeError(
            "Missing required NLTK data for EN synthesis: "
            + ", ".join(missing)
            + ". Run `python melo/init_downloads.py` or `python -m nltk.downloader "
            + "averaged_perceptron_tagger_eng cmudict` in the runtime image."
        )


def get_runtime_label():
    try:
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            major, minor = torch.cuda.get_device_capability(0)
            sm_code = major * 10 + minor
            visible = os.getenv("CUDA_VISIBLE_DEVICES", "all")
            return f"GPU: {gpu_name} (sm_{sm_code}, visible={visible})"
        mps_backend = getattr(torch.backends, "mps", None)
        if mps_backend is not None and getattr(mps_backend, "is_available", lambda: False)():
            return "Device: Apple MPS"
    except Exception as error:
        logger.warning(f"Could not determine runtime device label: {error}")
    return "Device: CPU"


DEVICE = os.getenv("TTS_DEVICE", "auto")
logger.info(
    f"Runtime device setting: {DEVICE}; CUDA_VISIBLE_DEVICES={os.getenv('CUDA_VISIBLE_DEVICES', 'not-set')}"
)
RUNTIME_LABEL = get_runtime_label()
logger.info(f"Runtime label: {RUNTIME_LABEL}")
LANGUAGES = [
    lang.strip()
    for lang in os.getenv("TTS_LANGUAGES", "EN,EN_V2,EN_NEWEST,ES,FR,ZH,JP,KR").split(",")
    if lang.strip()
]
validate_nltk_resources(LANGUAGES)
logger.info(f"Loading models for languages: {LANGUAGES}")
models = {}
for lang in LANGUAGES:
    try:
        models[lang] = TTS(language=lang, device=DEVICE)
        logger.info(f"Loaded TTS model for {lang}")
    except Exception as error:
        logger.error(f"Failed to load model for {lang}: {error}")


DEFAULT_TEXTS = {
    "EN": "The field of text-to-speech has seen rapid development recently.",
    "EN_V2": "The field of text-to-speech has seen rapid development recently.",
    "EN_NEWEST": "The field of text-to-speech has seen rapid development recently.",
    "ES": "El campo de sintesis de voz ha experimentado un rapido desarrollo recientemente.",
    "FR": "Le domaine de la synthese vocale a connu un developpement rapide recemment.",
    "ZH": "最近，文本到语音领域发展迅速。",
    "JP": "テキストから音声への分野は最近急速に発展しています。",
    "KR": "텍스트-음성 변환 분야는 최근 급격한 발전을 이루었습니다。",
}

PARAMETER_PRESETS = {
    "Balanced": {"speed": 1.0, "sdp_ratio": 0.2, "noise_scale": 0.6, "noise_scale_w": 0.8},
    "Clear narration": {"speed": 0.92, "sdp_ratio": 0.18, "noise_scale": 0.45, "noise_scale_w": 0.7},
    "Expressive": {"speed": 1.0, "sdp_ratio": 0.35, "noise_scale": 0.75, "noise_scale_w": 0.9},
    "Fast preview": {"speed": 1.2, "sdp_ratio": 0.2, "noise_scale": 0.55, "noise_scale_w": 0.75},
    "Calm": {"speed": 0.85, "sdp_ratio": 0.15, "noise_scale": 0.4, "noise_scale_w": 0.65},
}


def get_speakers_for_language(language):
    model = models.get(language)
    if not model:
        return []
    return list(model.hps.data.spk2id.keys())


def get_text_metrics(text, language):
    text = text or ""
    words = len(text.split())
    characters = len(text)
    try:
        segments = split_sentence(text, language_str=language) if text.strip() else []
    except Exception as error:
        logger.warning(f"Could not split text for metrics: {error}")
        segments = []
    return {"characters": characters, "words": words, "segments": len(segments)}


def get_voice_inventory():
    return [
        {
            "language": language,
            "status": "loaded" if language in models else "unavailable",
            "speakers": get_speakers_for_language(language),
        }
        for language in LANGUAGES
    ]


def get_status_payload():
    return {
        "msg": "pong",
        "type": "MeloTTS",
        "version": VERSION,
        "build_id": BUILD_ID,
        "device": DEVICE,
        "runtime": RUNTIME_LABEL,
        "configured_languages": LANGUAGES,
        "loaded_languages": list(models.keys()),
        "presets": PARAMETER_PRESETS,
    }


def synthesize_to_wav_bytes(body, model):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")
    try:
        spk_id = model.hps.data.spk2id[body.speaker_id]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid speaker_id '{body.speaker_id}'")

    bio = io.BytesIO()
    model.tts_to_file(
        body.text,
        spk_id,
        bio,
        speed=body.speed,
        sdp_ratio=body.sdp_ratio,
        noise_scale=body.noise_scale,
        noise_scale_w=body.noise_scale_w,
        format="wav",
    )
    bio.seek(0)
    return bio


app = FastAPI(
    title="MeloTTS",
    description="MeloTTS static web UI and mounted TTS API",
    version=VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

tts_app = FastAPI(
    title="TTS Service API",
    description="API documentation for the MeloTTS service",
    version=VERSION,
    openapi_url="/tts/openapi.json",
    docs_url="/tts/docs",
    redoc_url="/tts/redoc",
)


@tts_app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error for path {request.url.path}: {exc}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


class TextModel(BaseModel):
    text: str = Field(..., description="Text to synthesize.")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speech speed multiplier.")
    language: str = Field("EN", description="Loaded language/model code.")
    speaker_id: str = Field(..., description="Speaker ID from /tts/speakers.")
    sdp_ratio: float = Field(0.2, ge=0.0, le=1.0, description="Stochastic duration predictor ratio.")
    noise_scale: float = Field(0.6, ge=0.0, le=1.5, description="Acoustic sampling noise.")
    noise_scale_w: float = Field(0.8, ge=0.0, le=1.5, description="Duration sampling noise.")


class MetricsModel(BaseModel):
    text: str = Field("", description="Text to inspect.")
    language: str = Field("EN", description="Language/model code used for sentence splitting.")


def get_model(body: TextModel) -> TTS:
    model = models.get(body.language)
    if not model:
        logger.error(f"Requested model not available: {body.language}")
        raise HTTPException(status_code=404, detail=f"Language '{body.language}' is not loaded")
    return model


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(WEB_ROOT / "index.html")


@tts_app.get("/ping")
async def ping():
    logger.info("/tts/ping request received")
    return {
        "msg": "pong",
        "type": "MeloTTS",
        "version": VERSION,
        "build_id": BUILD_ID,
    }


@tts_app.get("/status")
async def status():
    logger.info("/tts/status request received")
    return get_status_payload()


@tts_app.get("/defaults")
async def defaults():
    logger.info("/tts/defaults request received")
    return {"texts": DEFAULT_TEXTS, "presets": PARAMETER_PRESETS}


@tts_app.get("/languages")
async def list_languages():
    logger.info("/tts/languages request received")
    return {"languages": LANGUAGES, "loaded_languages": list(models.keys())}


@tts_app.get("/speakers")
async def list_speakers(language: str = Query(..., description="Loaded language code")):
    logger.info(f"/tts/speakers request received for language={language}")
    model = models.get(language)
    if not model:
        logger.warning(f"Requested speakers for unknown language: {language}")
        raise HTTPException(status_code=404, detail="Language not found")
    return {"language": language, "speakers": list(model.hps.data.spk2id.keys())}


@tts_app.get("/voices")
async def voices():
    logger.info("/tts/voices request received")
    return {"voices": get_voice_inventory()}


@tts_app.post("/metrics")
async def metrics(body: MetricsModel = Body(...)):
    logger.info(f"/tts/metrics request received for language={body.language}")
    return {"language": body.language, "metrics": get_text_metrics(body.text, body.language)}


@tts_app.post("/purge")
async def purge_models(language: str = Body(..., embed=True)):
    global models
    keep_model = models.get(language)
    if not keep_model:
        raise HTTPException(status_code=404, detail=f"Language '{language}' is not loaded")
    removed = [lang for lang in list(models.keys()) if lang != language]
    models = {language: keep_model}
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info(f"Released models from memory: {removed}. Kept: {language}")
    return {"kept": language, "removed": removed, "loaded_languages": list(models.keys())}


@tts_app.post("/convert/tts")
async def convert_tts(body: TextModel = Body(...), model: TTS = Depends(get_model)):
    logger.info(f"/tts/convert/tts request: {body}")
    try:
        bio = synthesize_to_wav_bytes(body, model)
        audio, sample_rate = sf.read(bio, dtype="float32")
        duration = len(audio) / sample_rate if sample_rate else 0
        bio.seek(0)
        logger.info(
            f"Streamed TTS audio for language={body.language}, speaker={body.speaker_id}, duration={duration:.2f}s"
        )
        return StreamingResponse(
            bio,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=tts_{body.language}.wav",
                "X-MeloTTS-Language": body.language,
                "X-MeloTTS-Speaker": body.speaker_id,
                "X-MeloTTS-Sample-Rate": str(sample_rate),
                "X-MeloTTS-Duration": f"{duration:.3f}",
            },
        )
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error during TTS generation: {error}")
        return JSONResponse(status_code=500, content={"error": str(error)})


app.mount("/assets", StaticFiles(directory=str(WEB_ROOT)), name="assets")
app.mount("/tts", tts_app)
logger.info("Mounted static UI at / and TTS API at /tts")


def main():
    import uvicorn

    logger.info("Starting server on 0.0.0.0:8888")
    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="info")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        logger.exception(f"Application crashed: {error}")
