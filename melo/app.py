# WebUI by mrfakename <X @realmrfakename / HF @mrfakename>
# Demo also available on HF Spaces: https://huggingface.co/spaces/mrfakename/MeloTTS

import gradio as gr
import os, torch, io
from melo.api import TTS
import tempfile
import click
import logging

# ===== Logging Setup =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

logger.info("build 1")
logger.info("Make sure you've downloaded unidic (python -m unidic download) for this WebUI to work.")


# ===== Gradio UI Setup =====
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
    """Gradio UI synthesis handler. Uses in-memory BytesIO."""
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
    """Update available speakers and default text based on selected language."""
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

# ===== FastAPI Setup =====
from fastapi import FastAPI, Body, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

fastapi_app = FastAPI()

class TextModel(BaseModel):
    text: str
    speed: float = 1.0
    language: str = 'EN'
    speaker_id: str = 'EN-US'

def get_tts_model(body: TextModel):
    # Reuse models already loaded in memory!
    return models[body.language]

@fastapi_app.get("/ping")
async def ping():
    return {"msg": "pong"}

@fastapi_app.post("/convert/tts")
async def create_upload_file(
        body: TextModel = Body(...),
        model: TTS = Depends(get_tts_model)
):
    """
    API endpoint for TTS. Accepts JSON body, validates, synthesizes audio,
    saves to disk, and returns as a downloadable wav file.
    """
    speaker_ids = model.hps.data.spk2id

    # Validate speaker_id
    if body.speaker_id not in speaker_ids:
        logger.error(f"[API] Invalid speaker_id '{body.speaker_id}'. Available: {list(speaker_ids.keys())}")
        raise ValueError(f"Invalid speaker_id: {body.speaker_id}")

    # Synthesize to memory first (safer; matches UI)
    bio = io.BytesIO()
    logger.info(f"[API] Synthesizing to memory for speaker {body.speaker_id}, language {body.language}")
    model.tts_to_file(
        body.text,
        speaker_ids[body.speaker_id],
        bio,
        speed=body.speed,
        format='wav'
    )
    bio.seek(0)

    # Write memory buffer to disk for FileResponse
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(bio.read())
        tmp.flush()
        os.fsync(tmp.fileno())
        output_path = tmp.name
        logger.info(f"[API] Wrote buffer to disk at {output_path}, size={os.path.getsize(output_path)}")

    # Confirm file is not empty
    if os.path.getsize(output_path) == 0:
        logger.error("[API] Output wav file is empty after TTS!")
    else:
        logger.info("[API] Output wav file generated successfully.")

    return FileResponse(
        output_path,
        media_type="audio/mpeg",
        filename=os.path.basename(output_path)
    )

# ===== Main Entrypoint =====
@click.command()
@click.option('--share', '-s', is_flag=True, show_default=True, default=False, help="Expose a publicly-accessible shared Gradio link usable by anyone with the link. Only share the link with people you trust.")
@click.option('--host', '-h', default=None)
@click.option('--port', '-p', type=int, default=None)
def main(share, host, port):
    demo.queue(api_open=False)
    demo.app.mount("/api", fastapi_app)
    demo.launch(show_api=False, share=share, server_name=host, server_port=port)

if __name__ == "__main__":
    main()

