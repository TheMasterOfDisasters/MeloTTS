import gradio as gr
from fastapi import FastAPI, Body, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os, io, tempfile, logging
from melo.api import TTS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

logger.info("build 11")  # or whatever version you want to call it
logger.info("Make sure you've downloaded unidic (python -m unidic download) for this WebUI to work.")

device = 'auto'
models = {
    'EN': TTS(language='EN', device=device),
    'ES': TTS(language='ES', device=device),
    'FR': TTS(language='FR', device=device),
    'ZH': TTS(language='ZH', device=device),
    'JP': TTS(language='JP', device=device),
    'KR': TTS(language='KR', device=device),
}
speaker_ids = models['EN'].hps.data.spk2id

default_text_dict = {
    'EN': 'The field of text-to-speech has seen rapid development recently.',
    'ES': 'El campo de la conversión de texto a voz ha experimentado un rápido desarrollo recientemente.',
    'FR': 'Le domaine de la synthèse vocale a connu un développement rapide récemment',
    'ZH': 'text-to-speech 领域近年来发展迅速',
    'JP': 'テキスト読み上げの分野は最近急速な発展を遂げています',
    'KR': '최근 텍스트 음성 변환 분야가 급속도로 발전하고 있습니다.',
}

def synthesize(speaker, text, speed, language, progress=gr.Progress()):
    bio = io.BytesIO()
    models[language].tts_to_file(
        text,
        models[language].hps.data.spk2id[speaker],
        bio,
        speed=speed,
        pbar=progress.tqdm,
        format='wav'
    )
    return bio.getvalue()

def load_speakers(language, text):
    if text in list(default_text_dict.values()):
        newtext = default_text_dict[language]
    else:
        newtext = text
    return gr.update(
        value=list(models[language].hps.data.spk2id.keys())[0],
        choices=list(models[language].hps.data.spk2id.keys())
    ), newtext

with gr.Blocks() as demo:
    gr.Markdown('# MeloTTS WebUI\n\nA WebUI for MeloTTS.')
    with gr.Group():
        speaker = gr.Dropdown(speaker_ids.keys(), interactive=True, value='EN-US', label='Speaker')
        language = gr.Radio(['EN', 'ES', 'FR', 'ZH', 'JP', 'KR'], label='Language', value='EN')
        speed = gr.Slider(label='Speed', minimum=0.1, maximum=10.0, value=1.0, interactive=True, step=0.1)
        text = gr.Textbox(label="Text to speak", value=default_text_dict['EN'])
        language.input(load_speakers, inputs=[language, text], outputs=[speaker, text])
    btn = gr.Button('Synthesize', variant='primary')
    aud = gr.Audio(interactive=False)
    btn.click(synthesize, inputs=[speaker, text, speed, language], outputs=[aud])
    gr.Markdown('WebUI by [mrfakename](https://twitter.com/realmrfakename).')

# ---- API AS SUB-APP ----
api_app = FastAPI()

class TextModel(BaseModel):
    text: str
    speed: float = 1.0
    language: str = 'EN'
    speaker_id: str = 'EN-US'

def get_tts_model(body: TextModel):
    return models[body.language]

@api_app.post("/convert/tts")
async def create_upload_file(
        body: TextModel = Body(...), model: TTS = Depends(get_tts_model)
):
    speaker_ids = model.hps.data.spk2id
    if body.speaker_id not in speaker_ids:
        logger.error(f"[API] Invalid speaker_id '{body.speaker_id}'. Available: {list(speaker_ids.keys())}")
        raise ValueError(f"Invalid speaker_id: {body.speaker_id}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        output_path = tmp.name
        model.tts_to_file(
            body.text, speaker_ids[body.speaker_id], output_path, speed=body.speed
        )
        response = FileResponse(
            output_path, media_type="audio/wav", filename=os.path.basename(output_path)
        )
    logger.info(f"[API] Served TTS for speaker {body.speaker_id}, language {body.language}")
    return response

@api_app.get("/ping")
async def ping():
    return {"msg": "pong"}

# ---- Mount API under /api ----


def main():
    logger.info("demo.queue")
    queued = demo.queue(default_concurrency_limit=4, api_open=False)
    logger.info("queued app mount")
    queued.app.mount("/tts", api_app)
    logger.info("for route")
    for route in queued.app.routes:
        logger.info(f"Route: {route.path} -> methods {route.methods}")
    logger.info("Launch")
    queued.launch(
        show_api=False,
        server_name="0.0.0.0",
        server_port=8888,
    )

if __name__ == "__main__":
    main()
