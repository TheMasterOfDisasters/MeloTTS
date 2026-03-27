import io
import os
import logging
import gc

import gradio as gr
import torch
from fastapi import FastAPI, Body, Depends
from pydantic import BaseModel

from melo.api import TTS

# ─── Configuration & Version Info ─────────────────────────────────────────────
VERSION = os.getenv("APP_VERSION", "v0.0.6-SNAPSHOT")
BUILD_ID = os.getenv("BUILD_ID", "28")

# ─── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("TTSApp")
logger.info(f"Starting TTS UI+API App - Version: {VERSION}, Build: {BUILD_ID}")

# ─── Load Your TTS Models ───────────────────────────────────────────────────────
DEVICE = "auto"
LANGUAGES = [
    lang.strip()
    for lang in os.getenv("TTS_LANGUAGES", "EN,EN_V2,EN_NEWEST,ES,FR,ZH,JP,KR").split(",")
    if lang.strip()
]
logger.info(f"Loading models for languages: {LANGUAGES}")
models = {}
for lang in LANGUAGES:
    try:
        models[lang] = TTS(language=lang, device=DEVICE)
        logger.info(f"Loaded TTS model for {lang}")
    except Exception as e:
        logger.error(f"Failed to load model for {lang}: {e}")

# ─── Gradio UI Callbacks ────────────────────────────────────────────────────────
def synthesize(speaker: str, text: str, speed: float, language: str,  sdp_ratio: float = 0.2, noise_scale: float = 0.6, noise_scale_w: float = 0.8, progress=gr.Progress()):
    """
    Perform TTS synthesis, return WAV bytes.
    """
    try:
        bio = io.BytesIO()
        model = models.get(language)
        if not model:
            logger.error(f"Model not found for language: {language}")
            return None
        # Lookup speaker ID via dict-like access; HParams supports __getitem__
        try:
            spk_id = model.hps.data.spk2id[speaker]
        except KeyError:
            logger.error(f"Invalid speaker: {speaker} for language {language}")
            return None
        model.tts_to_file(
            text,
            spk_id,
            bio,
            speed=speed,
            sdp_ratio=sdp_ratio,
            noise_scale=noise_scale,
            noise_scale_w=noise_scale_w,
            pbar=progress.tqdm,
            format="wav"
        )
        logger.info(f"Synthesized audio for language={language}, speaker={speaker}")
        return bio.getvalue()
    except Exception as e:
        logger.exception(f"Error in synthesize callback: {e}")
        return None


def load_speakers(language: str, text: str):
    """
    Update speakers dropdown and default text when language changes.
    """
    model = models.get(language)
    if not model:
        logger.error(f"No model loaded for language: {language}")
        return gr.update(choices=[], value=None), text
    # HParams.data.spk2id is an HParams mapping, use keys()
    speakers = list(model.hps.data.spk2id.keys())
    defaults = {
        "EN": "The field of text-to-speech has seen rapid development recently.",
        "EN_V2": "The field of text-to-speech has seen rapid development recently.",
        "EN_NEWEST": "The field of text-to-speech has seen rapid development recently.",
        "ES": "El campo de síntesis de voz ha experimentado un rápido desarrollo recientemente.",
        "FR": "Le domaine de la synthèse vocale a connu un développement rapide récemment.",
        "ZH": "最近，文本到语音领域发展迅速。",
        "JP": "テキストから音声への分野は最近急速に発展しています。",
        "KR": "텍스트-음성 변환 분야는 최근 급격한 발전을 이루었습니다。",
    }
    logger.info(f"Updated speakers for language={language}: {speakers}")
    return gr.update(choices=speakers, value=speakers[0]), defaults.get(language, text)


def release_unused_models(language: str):
    """
    Keep only the selected language model in memory and release the rest.
    """
    global models
    keep_model = models.get(language)
    if not keep_model:
        logger.warning(f"Cannot release models; selected language not loaded: {language}")
        gr.Warning("No changes: selected language is not currently loaded.")
        return (
            gr.update(choices=list(models.keys()), value=None),
            gr.update(choices=[], value=None),
        )

    removed = [lang for lang in list(models.keys()) if lang != language]
    models = {language: keep_model}

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    speakers = list(keep_model.hps.data.spk2id.keys())
    logger.info(f"Released models from memory: {removed}. Kept: {language}")
    status = f"Released {len(removed)} model(s). Kept loaded: {language}."
    gr.Info(status)
    return (
        gr.update(choices=list(models.keys()), value=language),
        gr.update(choices=speakers, value=speakers[0] if speakers else None),
    )

# ─── Build Gradio Blocks ────────────────────────────────────────────────────────
with gr.Blocks(css="""
#build-badge {
    position: fixed;
    top: 12px;
    right: 12px;
    z-index: 9999;
    background: rgba(0, 0, 0, 0.45);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
    font-family: Arial, sans-serif;
    backdrop-filter: blur(2px);
}
""") as demo:
    gr.HTML(f"<div id='build-badge'>Version: {VERSION} | Build: {BUILD_ID}</div>")
    with gr.Tabs():
        with gr.Tab("UI Playground"):
            gr.Markdown("## Multilingual TTS Playground")
            with gr.Row():
                language = gr.Dropdown(LANGUAGES, label="Language", value=LANGUAGES[0])
                purge_btn = gr.Button("Purge others", size="sm", variant="secondary", min_width=120)
                speaker = gr.Dropdown([], label="Speaker")
            text = gr.Textbox(lines=3, label="Text")
            speed = gr.Slider(0.5, 2.0, value=1.0, label="Speed")
            sdp_ratio = gr.Slider(0.0, 1.0, value=0.2, label="SDP Ratio")
            noise_scale = gr.Slider(0.0, 1.5, value=0.6, label="Noise Scale")
            noise_scale_w = gr.Slider(0.0, 1.5, value=0.8, label="Noise Scale W")
            btn = gr.Button("Synthesize")
            audio_out = gr.Audio(label="Output Audio")

        with gr.Tab("API Docs"):
            gr.Markdown(
                """
## API Docs

Base path for custom endpoints: `/tts`

### `GET /tts/ping`
- Health/info endpoint
- Response example:
```json
{
  "msg": "pong",
  "type": "MeloTTS",
  "version": "v0.0.5",
  "build_id": "17"
}
```

### `POST /tts/convert/tts`
- Convert text to WAV stream
- JSON body:
```json
{
  "text": "Hello world",
  "speed": 1.0,
  "language": "EN",
  "speaker_id": "EN-BR",
  "sdp_ratio": 0.2,
  "noise_scale": 0.6,
  "noise_scale_w": 0.8
}
```

### `GET /tts/languages`
- Returns currently loaded language codes

### `GET /tts/speakers?language=EN`
- Returns available speakers for a language

You can also open interactive OpenAPI docs at `/tts/docs`.
                """
            )

    # Dynamic speaker loading
    language.change(load_speakers, inputs=[language, text], outputs=[speaker, text])
    # Synthesis button
    btn.click(
        fn=synthesize,
        inputs=[speaker, text, speed, language, sdp_ratio, noise_scale, noise_scale_w],
        outputs=[audio_out]
    )
    # Release all models except selected language
    purge_btn.click(
        fn=release_unused_models,
        inputs=[language],
        outputs=[language, speaker],
    )
    # Initialize speakers and default text on page load
    demo.load(load_speakers, inputs=[language, text], outputs=[speaker, text])

# ─── Enable Gradio Queue ───────────────────────────────────────────────────────
logger.info("Enabling Gradio queue: default_concurrency_limit=4, api_open=False")
demo.queue(default_concurrency_limit=4, api_open=False)
gr_app = demo.app
logger.info("Gradio app with queue initialized")

# ─── Build Your TTS FastAPI ────────────────────────────────────────────────────
tts_app = FastAPI(
    title="TTS Service API",
    description="API documentation for the TTS service",
    version=VERSION,
    openapi_url="/tts/openapi.json",
    docs_url="/tts/docs",
    redoc_url="/tts/redoc"
)
logger.info("TTS OpenAPI docs available at /tts/docs and OpenAPI spec at /tts/openapi.json")

# Handle Pydantic validation errors to return detailed messages
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

@tts_app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error for path {request.url.path}: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

class TextModel(BaseModel):
    text: str
    speed: float = 1.0
    language: str = "EN"
    speaker_id: str
    sdp_ratio: float = 0.2
    noise_scale: float = 0.6
    noise_scale_w: float = 0.8

def get_model(body: TextModel) -> TTS:
    model = models.get(body.language)
    if not model:
        logger.error(f"Requested model not available: {body.language}")
    return model

@tts_app.get("/ping")
async def ping():
    logger.info("/tts/ping request received")
    return {
        "msg": "pong",
        "type": "MeloTTS",
        "version": VERSION,
        "build_id": BUILD_ID
    }

@tts_app.post("/convert/tts")
async def convert_tts(
        body: TextModel = Body(...),
        model: TTS = Depends(get_model)
):
    """
    Convert text to speech and stream WAV bytes directly, without writing to disk.
    """
    logger.info(f"/tts/convert/tts request: {body}")
    # Validate and retrieve speaker ID
    try:
        spk_id = model.hps.data.spk2id[body.speaker_id]
    except KeyError:
        logger.warning(f"Invalid speaker_id: {body.speaker_id}")
        return JSONResponse(status_code=400, content={"error": f"Invalid speaker_id '{body.speaker_id}'"})

    # Use in-memory buffer
    bio = io.BytesIO()
    try:
        model.tts_to_file(
            body.text,
            spk_id,
            bio,
            speed=body.speed,
            sdp_ratio=body.sdp_ratio,
            noise_scale=body.noise_scale,
            noise_scale_w=body.noise_scale_w,
            format="wav"
        )
        bio.seek(0)
        logger.info(f"Streamed TTS audio for language={body.language}, speaker={body.speaker_id}")
        return StreamingResponse(
            bio,
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename=tts_{body.language}.wav"}
        )
    except Exception as e:
        logger.error(f"Error during TTS generation: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ─── Additional TTS API Endpoints ─────────────────────────────────────────────
@tts_app.get("/languages")
async def list_languages():
    """Return available languages."""
    logger.info("/tts/languages request received")
    return {"languages": LANGUAGES}

@tts_app.get("/speakers")
async def list_speakers(language: str):
    """Return available speakers for a given language query parameter."""
    logger.info(f"/tts/speakers request received for language={language}")
    model = models.get(language)
    if not model:
        logger.warning(f"Requested speakers for unknown language: {language}")
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Language not found")
    return {"speakers": list(model.hps.data.spk2id.keys())}

# ─── Mount TTS API on Gradio App ─────────────────────────────────────────────────
gr_app.mount("/tts", tts_app)
logger.info("Mounted TTS API at /tts on Gradio app")

# ─── Entrypoint ────────────────────────────────────────────────────────────────
def main():
    import uvicorn
    logger.info("Starting server on 0.0.0.0:8888")
    uvicorn.run(gr_app, host="0.0.0.0", port=8888, log_level="info")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Application crashed: {e}")
