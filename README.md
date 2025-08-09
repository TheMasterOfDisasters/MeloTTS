# MeloTTS — Maintained & Easy-to-Use Fork 🛠️

This project is an independently maintained fork of the original [MeloTTS](https://github.com/myshell-ai/MeloTTS) by [Wenliang Zhao](https://github.com/wl-zhao), [Xumin Yu](https://github.com/yuxumin), and [Zengyi Qin](https://github.com/Zengyi-Qin).  
The original work is licensed under the MIT License, and we thank the authors for their excellent research and contributions.

While the original MeloTTS is an impressive research project, this fork focuses on **making it simple to run and integrate** — with a working Docker image, included UI, and API support.

It’s designed so that you can:
- Pull the Docker image
- Run it instantly
- Start synthesizing speech via UI or API without hunting down dependencies

⚠️ **Note:**  This project is maintained for usability and convenience by a single developer (with a different primary tech stack).  
It is **not** a production-hardened system and may require additional work for deployment in critical environments.

✅ **Offline Mode:** Supported — provided that models are baked into the Docker image or mounted via a volume.  
If running in a fully offline environment, ensure all required model files are available locally before starting the container.

🤝 **Contributions Welcome:** If you find bugs, have ideas, or want to improve things, feel free to submit issues or pull requests. Every bit of help makes this project better for everyone.

---

## 🆘 Support & Issues
If you encounter bugs, have feature requests, or need help using MeloTTS:
- Please open a new [GitHub Issue](https://github.com/TheMasterOfDisasters/MeloTTS/issues) with as much detail as possible
- Include error messages, logs, and reproduction steps if applicable
- For general questions or ideas, you can also use the [Discussions](https://github.com/TheMasterOfDisasters/MeloTTS/discussions) tab

---

## 🚀 Quick Start

```bash
docker run -p 8888:8888 --gpus all sensejworld/melotts:latest
```

Then open: **[http://localhost:8888](http://localhost:8888)**

---

## 🌐 API Usage Example

```bash
curl -X POST "http://localhost:8888/api/tts"   -F "text=Hello world!"   -F "language=EN"   -o output.wav
```

---

## 📦 Docker Features
- Pinned dependencies for reproducible builds
- Preloaded models for instant offline use (optional)
- GPU acceleration when available
- HTTP API + web UI in one container

---

## 🐳 Docker Hub
You can explore all available MeloTTS container images on [Docker Hub](https://hub.docker.com/r/sensejworld/melotts/tags).

This is useful if you want to:
- Select a specific version of MeloTTS for compatibility
- Check the latest available builds before pulling
- Verify image tags for deployment

---

## 📜 Version History

### v0.0.5 (Planned)
- Add V2 models
- Add V3 models

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
- run with `docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.3`

### v0.0.2 (22.06.2025)
- Enable API calls together with UI
- run with `docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.2`
- run for english only `docker run -p 8888:8888 -e TTS_LANGUAGES=EN sensejworld/melotts:v0.0.2`
- run for english and japanese `docker run -p 8888:8888 -e TTS_LANGUAGES=EN,JP sensejworld/melotts:v0.0.2`
- run for english with gpu support named melotts_gpu_en `docker run -p 8888:8888 --gpus all -e TTS_LANGUAGES=EN --name melotts_gpu_en sensejworld/melotts:v0.0.2`

### v0.0.1 (21.06.2025)
`docker pull sensejworld/melotts:v0.0.1`
- Initial release
- Basic TTS functionality
- Support for English (Default, US, BR, India, AU)
- Docker support for both CPU and GPU
- Web interface on port 8888 (http://localhost:8888/)

---

## 🛠 Developer Notes
If you’re interested in building MeloTTS locally, testing changes, or working directly on the codebase, I have included additional technical details and tips in [`notes.md`](./docs/notes.md).

This file contains guidance for:
- Local environment setup
- Dependency management
- Testing workflows
- Build & Docker optimization notes

---

## 📜 License

This fork is licensed under the [MIT License](LICENSE).  
Original work by Wenliang Zhao, Xumin Yu, and Zengyi Qin in [MeloTTS](https://github.com/myshell-ai/MeloTTS).
