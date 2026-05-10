import base64
import gc
import io
import json
import logging
import os
import random
from pathlib import Path

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr
import soundfile as sf
import torch
from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from melo.api import TTS
from melo.split_utils import split_sentence


APP_ROOT = Path(__file__).resolve().parent.parent
ICON_PATH = APP_ROOT / "icon.png"


def _read_non_empty_env(name: str):
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _load_build_metadata():
    metadata_path = _read_non_empty_env("BUILD_METADATA_PATH") or str(APP_ROOT / ".build_meta.json")
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


def get_cuda_devices():
    if not torch.cuda.is_available():
        return []
    return [torch.cuda.get_device_name(idx) for idx in range(torch.cuda.device_count())]


def get_runtime_label():
    cuda_devices = get_cuda_devices()
    if cuda_devices:
        visible = os.getenv("CUDA_VISIBLE_DEVICES", "all")
        device_list = ", ".join(f"{idx}:{name}" for idx, name in enumerate(cuda_devices))
        return f"GPU x{len(cuda_devices)} (visible={visible}) [{device_list}]"
    try:
        mps_backend = getattr(torch.backends, "mps", None)
        if mps_backend is not None and getattr(mps_backend, "is_available", lambda: False)():
            return "Apple MPS"
    except Exception as error:
        logger.warning(f"Could not determine runtime device label: {error}")
    return "CPU"


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

QUOTE_BANK = {
    "EN": [
        "A clear voice can make a simple sentence feel alive.",
        "Every small test teaches the system something useful.",
        "The morning light moved slowly across the quiet room.",
        "Good tools should stay out of the way and help the work flow.",
        "Speech turns written ideas into something people can feel.",
        "A careful listener notices rhythm before individual words.",
        "The fastest path is often the one that stays simple.",
        "Today is a good day to make the interface easier to use.",
        "Strong software grows from many small and practical decisions.",
        "When the sound is natural, the text becomes easier to trust.",
    ],
    "EN_V2": [
        "A clear voice can make a simple sentence feel alive.",
        "Every small test teaches the system something useful.",
        "The morning light moved slowly across the quiet room.",
        "Good tools should stay out of the way and help the work flow.",
        "Speech turns written ideas into something people can feel.",
        "A careful listener notices rhythm before individual words.",
        "The fastest path is often the one that stays simple.",
        "Today is a good day to make the interface easier to use.",
        "Strong software grows from many small and practical decisions.",
        "When the sound is natural, the text becomes easier to trust.",
    ],
    "EN_NEWEST": [
        "A clear voice can make a simple sentence feel alive.",
        "Every small test teaches the system something useful.",
        "The morning light moved slowly across the quiet room.",
        "Good tools should stay out of the way and help the work flow.",
        "Speech turns written ideas into something people can feel.",
        "A careful listener notices rhythm before individual words.",
        "The fastest path is often the one that stays simple.",
        "Today is a good day to make the interface easier to use.",
        "Strong software grows from many small and practical decisions.",
        "When the sound is natural, the text becomes easier to trust.",
    ],
    "ES": [
        "Una voz clara puede dar vida a una frase sencilla.",
        "Cada prueba pequena ensena algo util al sistema.",
        "La luz de la manana avanzo despacio por la habitacion tranquila.",
        "Las buenas herramientas ayudan sin llamar demasiado la atencion.",
        "La voz convierte las ideas escritas en una experiencia cercana.",
        "Quien escucha con atencion percibe primero el ritmo.",
        "El camino mas rapido suele ser el que mantiene todo simple.",
        "Hoy es un buen dia para mejorar la interfaz.",
        "El buen software crece con decisiones pequenas y practicas.",
        "Cuando el sonido es natural, el texto resulta mas confiable.",
    ],
    "FR": [
        "Une voix claire peut donner vie a une phrase simple.",
        "Chaque petit test apprend quelque chose d utile au systeme.",
        "La lumiere du matin avancait lentement dans la piece calme.",
        "Les bons outils aident sans attirer trop d attention.",
        "La parole transforme les idees ecrites en experience proche.",
        "Une personne attentive remarque le rythme avant les mots.",
        "Le chemin le plus rapide reste souvent le plus simple.",
        "Aujourd hui est un bon jour pour rendre l interface plus agreable.",
        "Un bon logiciel grandit grace a de petites decisions pratiques.",
        "Quand le son parait naturel, le texte inspire davantage confiance.",
    ],
    "ZH": [
        "清晰的声音能让简单的句子变得生动。",
        "每一次小测试都会让系统学到有用的东西。",
        "清晨的光慢慢移过安静的房间。",
        "好的工具应该安静地帮助工作顺利进行。",
        "语音把写下的想法变成可以感受的内容。",
        "细心的听众会先注意到节奏。",
        "最快的道路往往是保持简单的道路。",
        "今天很适合让界面变得更好用。",
        "可靠的软件来自许多小而实际的决定。",
        "当声音自然时，文字也更容易被信任。",
    ],
    "JP": [
        "澄んだ声は、短い文にも命を吹き込みます。",
        "小さなテストのたびに、システムは役立つことを学びます。",
        "朝の光が静かな部屋をゆっくり進んでいきました。",
        "よい道具は作業を静かに支えてくれます。",
        "音声は書かれた考えを身近な体験に変えます。",
        "注意深く聞く人は、言葉より先にリズムに気づきます。",
        "いちばん速い道は、たいていシンプルな道です。",
        "今日は画面をもっと使いやすくするのに良い日です。",
        "良いソフトウェアは、小さく実用的な判断から育ちます。",
        "音が自然だと、文章も信頼しやすくなります。",
    ],
    "KR": [
        "맑은 목소리는 짧은 문장에도 생기를 줍니다.",
        "작은 테스트마다 시스템은 유용한 것을 배웁니다.",
        "아침 햇살이 조용한 방 안을 천천히 지나갔습니다.",
        "좋은 도구는 일을 조용히 도와야 합니다.",
        "음성은 글로 쓴 생각을 더 가까운 경험으로 바꿉니다.",
        "주의 깊게 듣는 사람은 단어보다 리듬을 먼저 느낍니다.",
        "가장 빠른 길은 대개 단순함을 지키는 길입니다.",
        "오늘은 인터페이스를 더 쓰기 좋게 만들기에 좋은 날입니다.",
        "좋은 소프트웨어는 작고 실용적인 결정에서 자랍니다.",
        "소리가 자연스러우면 글도 더 신뢰하기 쉬워집니다.",
    ],
}

PARAMETER_PRESETS = {
    "Balanced": {"speed": 1.0, "sdp_ratio": 0.2, "noise_scale": 0.6, "noise_scale_w": 0.8},
    "Clear narration": {"speed": 0.92, "sdp_ratio": 0.18, "noise_scale": 0.45, "noise_scale_w": 0.7},
    "Expressive": {"speed": 1.0, "sdp_ratio": 0.35, "noise_scale": 0.75, "noise_scale_w": 0.9},
    "Fast preview": {"speed": 1.2, "sdp_ratio": 0.2, "noise_scale": 0.55, "noise_scale_w": 0.75},
    "Calm": {"speed": 0.85, "sdp_ratio": 0.15, "noise_scale": 0.4, "noise_scale_w": 0.65},
}


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


def get_model(body: TextModel) -> TTS:
    model = models.get(body.language)
    if not model:
        logger.error(f"Requested model not available: {body.language}")
        raise HTTPException(status_code=404, detail=f"Language '{body.language}' is not loaded")
    return model


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


def make_request_body(text, language, speaker, speed, sdp_ratio, noise_scale, noise_scale_w):
    return TextModel(
        text=text or "",
        language=language,
        speaker_id=speaker,
        speed=speed,
        sdp_ratio=sdp_ratio,
        noise_scale=noise_scale,
        noise_scale_w=noise_scale_w,
    )


def synthesize_for_ui(text, language, speaker, speed, sdp_ratio, noise_scale, noise_scale_w):
    body = make_request_body(text, language, speaker, speed, sdp_ratio, noise_scale, noise_scale_w)
    model = models.get(body.language)
    if not model:
        raise gr.Error(f"Language '{body.language}' is not loaded")
    try:
        bio = synthesize_to_wav_bytes(body, model)
        waveform, sample_rate = sf.read(bio, dtype="float32")
        metrics_payload = get_text_metrics(body.text, body.language)
        duration = len(waveform) / sample_rate if sample_rate else 0
        status_text = (
            f"Generated {duration:.2f}s audio | "
            f"{metrics_payload['characters']} chars | "
            f"{metrics_payload['words']} words | "
            f"{metrics_payload['segments']} segments"
        )
        logger.info(
            f"UI synthesis complete for language={body.language}, speaker={body.speaker_id}, duration={duration:.2f}s"
        )
        return (sample_rate, waveform), status_text
    except HTTPException as error:
        raise gr.Error(str(error.detail)) from error
    except Exception as error:
        logger.exception(f"UI synthesis failed: {error}")
        raise gr.Error(str(error)) from error


def update_language(language, current_text):
    speakers = get_speakers_for_language(language)
    default_text = DEFAULT_TEXTS.get(language, current_text or "")
    return gr.update(choices=speakers, value=speakers[0] if speakers else None), default_text


def apply_preset(preset_name):
    preset = PARAMETER_PRESETS.get(preset_name, PARAMETER_PRESETS["Balanced"])
    return preset["speed"], preset["sdp_ratio"], preset["noise_scale"], preset["noise_scale_w"]


def normalize_text(text):
    return " ".join((text or "").split())


def load_random_quote(language):
    quotes = QUOTE_BANK.get(language) or QUOTE_BANK["EN"]
    quote = random.choice(quotes)
    return quote, metrics_for_ui(quote, language)


def metrics_for_ui(text, language):
    metrics_payload = get_text_metrics(text, language)
    return (
        f"{metrics_payload['characters']} characters | "
        f"{metrics_payload['words']} words | "
        f"{metrics_payload['segments']} segments"
    )


def purge_models_sync(language):
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


def release_unused_models_for_ui(language):
    result = purge_models_sync(language)
    speakers = get_speakers_for_language(language)
    gr.Info(f"Released {len(result['removed'])} model(s). Kept loaded: {language}.")
    return (
        gr.update(choices=list(models.keys()), value=language),
        gr.update(choices=speakers, value=speakers[0] if speakers else None),
    )


def load_icon_data_uri():
    try:
        return "data:image/png;base64," + base64.b64encode(ICON_PATH.read_bytes()).decode("ascii")
    except FileNotFoundError:
        logger.warning(f"UI icon not found at {ICON_PATH}")
    except Exception as error:
        logger.warning(f"Unable to load UI icon from {ICON_PATH}: {error}")
    return ""


BADGE_CSS = """
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
#brand-strip {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}
#brand-strip img {
    width: 34px;
    height: 34px;
    border-radius: 8px;
}
#brand-strip strong {
    font-size: 20px;
}
"""

ICON_DATA_URI = load_icon_data_uri()
HEAD_HTML = f'<link rel="icon" type="image/png" href="{ICON_DATA_URI}">' if ICON_DATA_URI else ""
BRAND_HTML = (
    f'<div id="brand-strip"><img src="{ICON_DATA_URI}" alt="MeloTTS icon"><strong>MeloTTS</strong></div>'
    if ICON_DATA_URI
    else "<div id='brand-strip'><strong>MeloTTS</strong></div>"
)


initial_language = next(iter(models.keys()), LANGUAGES[0] if LANGUAGES else "EN")
initial_speakers = get_speakers_for_language(initial_language)
initial_speaker = initial_speakers[0] if initial_speakers else None

with gr.Blocks(analytics_enabled=False) as generate_tab:
    out_audio = gr.Audio(label="Output Audio", interactive=False, streaming=False, autoplay=True)
    generate_btn = gr.Button("Generate", variant="primary")
    with gr.Accordion("Output Details", open=True):
        status_box = gr.Textbox(
            value="No audio generated yet.",
            interactive=False,
            show_label=False,
            info="Generation details and text metrics.",
        )
        gr.Button("Open API Docs", link="/tts/docs", variant="secondary")

with gr.Blocks(analytics_enabled=False) as voices_tab:
    voices_json = gr.JSON(label="Loaded Voices", value=get_voice_inventory())
    refresh_voices_btn = gr.Button("Refresh", variant="secondary")

with gr.Blocks(title="MeloTTS", analytics_enabled=False, head=HEAD_HTML) as ui:
    gr.HTML(f"<style>{BADGE_CSS}</style>")
    gr.HTML(f"<div id='build-badge'>Version: {VERSION} | Build: {BUILD_ID}<br>{RUNTIME_LABEL}</div>")
    gr.HTML(BRAND_HTML)
    with gr.Row():
        with gr.Column():
            text = gr.Textbox(
                value=DEFAULT_TEXTS.get(initial_language, ""),
                label="Input Text",
                info="Arbitrarily many characters supported",
                lines=5,
            )
            metrics_box = gr.Textbox(
                value=metrics_for_ui(DEFAULT_TEXTS.get(initial_language, ""), initial_language),
                label="Text Metrics",
                interactive=False,
            )
            with gr.Row():
                language = gr.Dropdown(
                    choices=list(models.keys()),
                    value=initial_language,
                    label="Language",
                    info="Loaded MeloTTS model",
                    filterable=False,
                    allow_custom_value=False,
                )
                speaker = gr.Dropdown(
                    choices=initial_speakers,
                    value=initial_speaker,
                    label="Speaker",
                    info="Available speakers for selected language",
                    filterable=False,
                    allow_custom_value=False,
                )
            preset = gr.Dropdown(
                choices=list(PARAMETER_PRESETS.keys()),
                value="Balanced",
                label="Preset",
                info="Quick synthesis parameter set",
                filterable=False,
                allow_custom_value=False,
            )
            speed = gr.Slider(minimum=0.5, maximum=2, value=1, step=0.05, label="Speed")
            with gr.Accordion("Advanced Synthesis", open=False):
                sdp_ratio = gr.Slider(minimum=0, maximum=1, value=0.2, step=0.01, label="SDP Ratio")
                noise_scale = gr.Slider(minimum=0, maximum=1.5, value=0.6, step=0.01, label="Noise Scale")
                noise_scale_w = gr.Slider(
                    minimum=0,
                    maximum=1.5,
                    value=0.8,
                    step=0.01,
                    label="Noise Scale W",
                )
            sample_btn = gr.Button("Random Quote", variant="secondary")
            with gr.Row():
                normalize_btn = gr.Button("Normalize Spacing", variant="secondary")
                purge_btn = gr.Button("Purge Other Models", variant="secondary")
        with gr.Column():
            gr.TabbedInterface([generate_tab, voices_tab], ["Generate", "Voices"])

    language.change(update_language, inputs=[language, text], outputs=[speaker, text])
    language.change(metrics_for_ui, inputs=[text, language], outputs=[metrics_box])
    text.change(metrics_for_ui, inputs=[text, language], outputs=[metrics_box])
    preset.change(apply_preset, inputs=[preset], outputs=[speed, sdp_ratio, noise_scale, noise_scale_w])
    sample_btn.click(load_random_quote, inputs=[language], outputs=[text, metrics_box])
    normalize_btn.click(normalize_text, inputs=[text], outputs=[text])
    normalize_btn.click(metrics_for_ui, inputs=[text, language], outputs=[metrics_box])
    purge_btn.click(release_unused_models_for_ui, inputs=[language], outputs=[language, speaker])
    generate_btn.click(
        synthesize_for_ui,
        inputs=[text, language, speaker, speed, sdp_ratio, noise_scale, noise_scale_w],
        outputs=[out_audio, status_box],
    )
    refresh_voices_btn.click(get_voice_inventory, inputs=[], outputs=[voices_json])

ui.queue(default_concurrency_limit=4, api_open=False)

api = FastAPI(
    title="TTS Service API",
    description="API documentation for the MeloTTS service",
    version=VERSION,
    openapi_url="/tts/openapi.json",
    docs_url="/tts/docs",
    redoc_url="/tts/redoc",
)


@api.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error for path {request.url.path}: {exc}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@api.get("/tts/ping")
async def ping():
    logger.info("/tts/ping request received")
    return {"msg": "pong", "type": "MeloTTS", "version": VERSION, "build_id": BUILD_ID}


@api.get("/tts/status")
async def status():
    logger.info("/tts/status request received")
    return get_status_payload()


@api.get("/tts/defaults")
async def defaults():
    logger.info("/tts/defaults request received")
    return {"texts": DEFAULT_TEXTS, "quotes": QUOTE_BANK, "presets": PARAMETER_PRESETS}


@api.get("/tts/languages")
async def list_languages():
    logger.info("/tts/languages request received")
    return {"languages": LANGUAGES, "loaded_languages": list(models.keys())}


@api.get("/tts/speakers")
async def list_speakers(language: str = Query(..., description="Loaded language code")):
    logger.info(f"/tts/speakers request received for language={language}")
    model = models.get(language)
    if not model:
        logger.warning(f"Requested speakers for unknown language: {language}")
        raise HTTPException(status_code=404, detail="Language not found")
    return {"language": language, "speakers": list(model.hps.data.spk2id.keys())}


@api.get("/tts/voices")
async def voices():
    logger.info("/tts/voices request received")
    return {"voices": get_voice_inventory()}


@api.post("/tts/metrics")
async def metrics(body: MetricsModel = Body(...)):
    logger.info(f"/tts/metrics request received for language={body.language}")
    return {"language": body.language, "metrics": get_text_metrics(body.text, body.language)}


@api.post("/tts/purge")
async def purge_models(language: str = Body(..., embed=True)):
    return purge_models_sync(language)


@api.post("/tts/convert/tts")
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


app = gr.mount_gradio_app(api, ui, path="/")
logger.info("Mounted Gradio UI at / with TTS API routes under /tts")


def main():
    import uvicorn

    logger.info("Starting server on 0.0.0.0:8888")
    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="info")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        logger.exception(f"Application crashed: {error}")
