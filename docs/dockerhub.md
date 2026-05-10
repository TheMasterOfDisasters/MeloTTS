# 🗣️ MeloTTS WebUI & API (Docker)

This is an [independently maintained fork](https://github.com/TheMasterOfDisasters/MeloTTS) of the original [MeloTTS](https://github.com/myshell-ai/MeloTTS), focusing on making it **easy to run, integrate, and test** without deep technical setup.

## ✅ Features
- Multilingual TTS: EN, ES, FR, ZH, JP, KR
- Web interface on `/`
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
docker run -p 8888:8888 --gpus all sensejworld/melotts:latest
```

**EN-focused image (smaller target image):**
```bash
docker run -p 8888:8888 --gpus all sensejworld/melotts:latest_en
```

**Specific GPU (example: GPU index `1`):**
```bash
docker run -p 8888:8888 --gpus "device=1" sensejworld/melotts
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

Main tag strategy:
- EN-focused image: `latest_en`, `<version>_en`
- Full multilingual image: `latest`, `<version>_full`


---

## 📜 Version History

### v0.0.8 (planned)
- Scope: runtime-focused cleanup for the Docker UI/API fork.
- Removed unused upstream training surfaces, including training scripts/modules, training example data, legacy script-style package tests, and original upstream docs that no longer matched this fork.
- Trimmed runtime helper code by reducing `melo/utils.py` to inference text preparation, config loading, and `HParams`.
- Removed stale phonemizer generation artifacts and notebook files that were not read by runtime synthesis.
- Cleaned stale imports, unused locals, and unreachable flow-layer code found by lint checks.
- Improved Taskfile API readiness checks by retrying transient startup errors such as `Empty reply from server`.
- Replaced the Gradio-hosted UI with a FastAPI-served `MeloTTS Studio` static frontend using local Tailwind-style CSS assets.
- Added text metrics, voice inventory, synthesis presets, advanced controls, runtime metadata, and richer in-app API documentation.
- Added `/tts/status`, `/tts/defaults`, `/tts/voices`, `/tts/metrics`, and `/tts/purge` endpoints for the new UI and companion integrations.
- Expanded rapid local iteration tasks so `task localrun`, `task localdev`, and `task localapi` bind-mount both `melo/app.py` and `melo/web`.
- Added `todo/FEATURE_IDEAS.md` with practical UI/API/runtime improvements that fit the current codebase.
- Documentation: corrected API examples to use `/tts/convert/tts` JSON payloads and documented the current runtime-only scope.

### v0.0.7 (29.03.2026)
- Upgraded Docker runtime/build baseline to Python 3.10 (`python:3.10-slim`) and aligned packaging with `python_requires>=3.10`.
- Reworked app versioning/build metadata:
  - Root `VERSION` file is now the single version source of truth.
  - Build metadata is generated at image build time (no hardcoded `BUILD_ID`) and exposed in UI/API.
- Upgraded web stack to newer compatible releases: `gradio==4.44.1`, `gradio-client==1.3.0`, `fastapi==0.115.12`, `starlette==0.46.2`, `typer==0.12.5`.
- Applied large dependency/security refresh with pinned versions for reproducible builds, including network/security-sensitive packages such as `requests==2.32.4`, `urllib3==2.3.0`, `certifi==2025.6.15`, plus broad runtime library updates.
- Added/kept compatibility guardrails for stability:
  - `markupsafe` remains on 2.x for Gradio compatibility.
  - `huggingface-hub==0.21.4` and `filelock==3.13.1` remain constrained by `cached-path==1.6.2`.
- Improved offline reliability and startup resilience:
  - Build-time preload profiles (`EN_ONLY` / `FULL`) with retry + strict/non-strict controls.
  - NLTK resources required for EN synthesis (including `averaged_perceptron_tagger_eng` and `cmudict`) are preloaded during image build for offline-ready runs.
- Fixed Gradio 4.x UI regressions after upgrades (language/speaker loading + synth output compatibility) while keeping API behavior stable.
- Split Docker release flow into EN and FULL image tracks/workflows (`<version>_en`, `<version>_full`) to improve build/release flexibility.
- Run with:
  ```bash
  docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.7_en
  docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.7_full
  docker run -p 8888:8888 --gpus "device=1" sensejworld/melotts:v0.0.7_en
  ```

### v0.0.6 (27.03.2026)
- Model loading is now much faster (from ~30 seconds down to only a few seconds in testing).
- Added working RTX 50-series (`sm_120`) support in the Docker setup.
- Added GPU selection support for Docker runs, so you can choose which GPU to use.
- Improved build resilience for model preloading during Docker image creation.
- Run with:
  ```bash
  docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.6
  ```

### v0.0.5 (27.03.2026)
- Added more English model options (including V2 and V3 variants).
- Added UI tabs for `UI Playground` and `API Docs`.
- Added build/version badge in UI (top-right) via `APP_VERSION` and `BUILD_ID`.
- Added memory management in UI (`Purge others`) to release non-selected language models.
- Improved API documentation visibility directly inside the app (`/` -> API Docs tab + `/tts/docs`).
- Updated release planning: V2/V3 scope completed; deferred separate base-repo split plan.
- Run with:
  ```bash
  docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.5
  ```

### v0.0.4 (09.08.2025)
- **Dependency updates** for improved performance and stability.
- **Full offline support** — all required models are now baked into the image.
- **Model overwrite option**: set `MELOTTTS_MODELS` to point to your custom model folder.
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
