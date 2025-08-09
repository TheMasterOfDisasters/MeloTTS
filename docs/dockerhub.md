## 🗣️ MeloTTS WebUI & API (Docker)
This image provides a ready-to-run container for the [MeloTTS](https://github.com/TheMasterOfDisasters/MeloTTS) project, exposing both a Web UI and an HTTP API.

Image will be expanded with integration towards local models in mind.

If you have any issues or suggestions for improvement, please create issue in GitHub.

### ✅ Features
- Multilingual TTS: EN, ES, FR, ZH, JP, KR
- Web interface (Gradio) on `/`
- HTTP API on `/api/tts`
- Docker-ready for local or cloud use

### 🚀 Quick Start
CPU :
```docker run -p 8888:8888 sensejworld/melotts ```

NVIDIA :
```docker run -p 8888:8888 --gpus all sensejworld/melotts ```

Visit: http://localhost:8888 for the UI  (Remember first synthesize might take up to 1 minute, after that its very fast)

### 📡 API Usage
```bash curl -X POST http://localhost:8888/api/tts \ -F "text=Hello from Docker" \ -F "speaker=EN-US" \ -F "language=EN" \ -F "speed=1.0" --output output.wav ```

### 📘 Full Walkthrough & Notes
For a complete walkthrough, including setup tips and explanations for non-developers, check out the full guide in [`docs/notes.md`](https://github.com/TheMasterOfDisasters/MeloTTS/blob/main/docs/notes.md). 💬

**Note from the creator**: I'm not a Python expert, and I wrote this mostly to help myself and others who might struggle with technical docs or coding. So, if anything seems over-explained, that's on purpose! 😊 My goal is to make this project accessible and functional for everyone.

## Version History

## 📜 Version History

### v0.0.5 (Planned)
- Add V2 models
- Add V3 models

### v0.0.4 (Upcoming)
- **Dependency updates** for improved performance and stability.
- **Full offline support** — all required models are now baked into the image.
- **Model overwrite option**: set `MELOTTS_MODELS` to point to your custom model folder.
- **Smaller image size** via optimized multi-stage Docker build.
- Run with:
  ```bash
  docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.4

### v0.0.3 (2025-07-25)
- Optimized docker build to use layer caching so we can build stuff fast after the initial build
- Expanded ping to include version and build
- Expanded UI with sdp_ratio, noise_scale and noise_scale_w
- Expanded API with sdp_ratio, noise_scale and noise_scale_w
- Corrected faulty version dates
- Updated documentation
- run with `docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.3`

### v0.0.2 (2025-06-22)
- Enable API calls together with UI
- run with `docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.2`
- run for english only `docker run -p 8888:8888 -e TTS_LANGUAGES=EN sensejworld/melotts:v0.0.2`
- run for english and japanese `docker run -p 8888:8888 -e TTS_LANGUAGES=EN,JP sensejworld/melotts:v0.0.2`
- run for english with gpu support named melotts_gpu_en `docker run -p 8888:8888 --gpus all -e TTS_LANGUAGES=EN --name melotts_gpu_en sensejworld/melotts:v0.0.2`

### v0.0.1 (2025-06-21)
`docker pull sensejworld/melotts:v0.0.1`
- Initial release
- Basic TTS functionality
- Support for English (Default, US, BR, India, AU)
- Docker support for both CPU and GPU
- Web interface on port 8888 (http://localhost:8888/)

---


