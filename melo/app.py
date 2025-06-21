from fastapi import FastAPI, Form
from fastapi.responses import FileResponse
from fastapi.middleware.wsgi import WSGIMiddleware
import gradio as gr
import os, torch, io, uuid, tempfile, click
from melo.api import TTS

print("Make sure you've downloaded unidic (python -m unidic download) for this WebUI to work.")

speed = 1.0

device = 'auto'
models = {
    'EN': TTS(language='EN', device=device),
    'ES': TTS(language='ES', device=device),
    'FR': TTS(language='FR', device=device),
    'ZH': TTS(language='ZH', device=device),
    'JP': TTS(language='JP', device=device),
    'KR': TTS(language='KR', device=device),
}
speaker_ids = dict(models['EN'].hps.data.spk2id)  # Convert to regular dictionary

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
    models[language].tts_to_file(text, models[language].hps.data.spk2id[speaker], bio, speed=speed, pbar=progress.tqdm, format='wav')
    return bio.getvalue()

def load_speakers(language, text):
    if text in list(default_text_dict.values()):
        newtext = default_text_dict[language]
    else:
        newtext = text
    
    # Get the speaker IDs dictionary for the selected language
    speakers = dict(models[language].hps.data.spk2id)
    speaker_list = list(speakers.keys())
    
    if not speaker_list:
        raise ValueError(f"No speakers found for language {language}")
    
    return gr.update(value=speaker_list[0], choices=speaker_list), newtext

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

# FastAPI for API access
fastapi_app = FastAPI()

@fastapi_app.post("/api/tts")
async def generate_tts(text: str = Form(...), speaker: str = Form(...), language: str = Form('EN'), speed: float = Form(1.0)):
    if language not in models:
        return {"error": f"Language {language} not supported"}
    
    speakers = dict(models[language].hps.data.spk2id)
    if speaker not in speakers:
        return {"error": f"Speaker {speaker} not found for language {language}"}
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        output_path = tmp.name
        models[language].tts_to_file(text, speakers[speaker], output_path, speed=speed)
        return FileResponse(output_path, media_type='audio/wav', filename='output.wav')

# Mount Gradio app on FastAPI
fastapi_app.mount("/", WSGIMiddleware(demo))

@click.command()
@click.option('--share', '-s', is_flag=True, show_default=True, default=False, help="Expose a publicly-accessible shared Gradio link usable by anyone with the link. Only share the link with people you trust.")
@click.option('--host', '-h', default="0.0.0.0")
@click.option('--port', '-p', type=int, default=8888)
def main(share, host, port):
    import uvicorn
    uvicorn.run(fastapi_app, host=host, port=port)

if __name__ == "__main__":
    main()