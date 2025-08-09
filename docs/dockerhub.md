# 🗣️ MeloTTS WebUI & API (Docker)

This is an independently maintained fork of the original [MeloTTS](https://github.com/myshell-ai/MeloTTS), focusing on making it **easy to run, integrate, and test** without deep technical setup.

## ✅ Features
- Multilingual TTS: EN, ES, FR, ZH, JP, KR
- Web interface (Gradio) on `/`
- HTTP API on `/tts/convert/tts`
- Docker-ready for local or cloud use
- GPU acceleration when available
- Optional offline mode with preloaded models

## 🚀 Quick Start
**CPU:**
```bash
docker run -p 8888:8888 sensejworld/melotts
```

**NVIDIA GPU:**
```bash
docker run -p 8888:8888 --gpus all sensejworld/melotts
```

**English only:**
```bash
docker run -p 8888:8888 --gpus all -e TTS_LANGUAGES=EN sensejworld/melotts
```

Visit: [http://localhost:8888](http://localhost:8888) for the UI.  
*(First synthesis may take up to 1 minute — after that, it's very fast.)*

### 📡 API Usage Examples
**Simple:**
```bash
curl -X POST "http://localhost:8888/tts/convert/tts" ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"Hello world. I wanted to test this and see if this works properly\",\"language\":\"EN\",\"speaker_id\":\"EN-BR\"}" ^
  -o hello.wav
```

**Advanced:**
```bash
curl -v -X POST http://localhost:8888/tts/convert/tts ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"Hello world. I wanted to test this and see if this works properly\",\"speed\":1.0,\"language\":\"EN\",\"speaker_id\":\"EN-BR\",\"sdp_ratio\":\"0.21\",\"noise_scale\":\"0.61\",\"noise_scale_w\":\"0.81\"}" ^
  --output hello.wav
```


## 🆘 Support & Issues
If you encounter a bug, have a feature request, or want to contribute:
- 📄 Open a **[GitHub Issue](https://github.com/TheMasterOfDisasters/MeloTTS/issues)** with full details (logs, commands used, reproduction steps)
- 💬 Start a discussion in the **[GitHub Discussions](https://github.com/TheMasterOfDisasters/MeloTTS/discussions)** tab for ideas or questions
- 🛠 Check **[Known Issues](https://github.com/TheMasterOfDisasters/MeloTTS/issues?q=is%3Aissue+is%3Aopen+label%3Abug)** before reporting

I respond fastest on GitHub — Docker Hub comments aren’t monitored regularly.

### 🔗 Common Help Topics
- **[ReadMe](https://github.com/TheMasterOfDisasters/MeloTTS/blob/main/README.md)**
- **[Technical Readme](https://github.com/TheMasterOfDisasters/MeloTTS/blob/main/docs/notes.md)**


## 📦 Docker Hub Tags
View all available builds: [sensejworld/melotts — Tags](https://hub.docker.com/r/sensejworld/melotts/tags)


---

## 📜 Version History

### v0.0.5 (Planned)
- Add V2 models
- Add V3 models
- Create new repo (Melotts-base) with image containing models so build have more space in the future

### v0.0.4 (09.08.2025)
- **Dependency updates** for improved performance and stability.
- **Full offline support** — all required models are now baked into the image.
- **Model overwrite option**: set `MELOTTS_MODELS` to point to your custom model folder.
- **Smaller image size** via optimized multi-stage Docker build.
- Run with:
  ```bash
  docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.4

### v0.0.3 (25.07.2025)
- Optimized docker build to use layer caching so we can build stuff fast after the initial build
- Expanded ping to include version and build
- Expanded UI with sdp_ratio, noise_scale and noise_scale_w
- Expanded API with sdp_ratio, noise_scale and noise_scale_w
- Corrected faulty version dates
- Updated documentation
- Run with:
  ```bash
  docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.3`

### v0.0.2 (22.06.2025)
- Enable API calls together with UI
- run with
  ```bash 
  docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.2`
- run for english only
    ```bash 
    docker run -p 8888:8888 -e TTS_LANGUAGES=EN sensejworld/melotts:v0.0.2`
- run for english and japanese
    ```bash 
    docker run -p 8888:8888 -e TTS_LANGUAGES=EN,JP sensejworld/melotts:v0.0.2`
- run for english with gpu support named melotts_gpu_en
    ```bash 
    docker run -p 8888:8888 --gpus all -e TTS_LANGUAGES=EN --name melotts_gpu_en sensejworld/melotts:v0.0.2`

### v0.0.1 (21.06.2025)
- Initial release
- Basic TTS functionality
- Support for English (Default, US, BR, India, AU)
- Docker support for both CPU and GPU
- Web interface on port 8888 (http://localhost:8888/)
- Run with
  ```bash 
  docker pull sensejworld/melotts:v0.0.1`

---


## 📜 License
This fork is licensed under the MIT License.  
Original work by Wenliang Zhao, Xumin Yu, and Zengyi Qin in [MeloTTS](https://github.com/myshell-ai/MeloTTS).