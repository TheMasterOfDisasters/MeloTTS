# Development Notes

##Tools

    winget install --id=astral-sh.uv -e

## Version Management
`git tag v0.0.2`  
`git push origin v0.0.2`

## Docker Usage
### CPU Version
`docker run -p 8888:8888 sensejworld/melotts`

### GPU Version
`docker run --gpus all -p 8888:8888 sensejworld/melotts`

## Test locally

### Build image  
You need docker to be working. (Example : Docker Desktop)  
`docker build -t melotts:test .`

### Run image  
`docker run -p 8888:8888 --gpus all melotts:test`

### Run image - offline mode
`docker run -p 8888:8888 -it --rm --gpus all --add-host=cdn-lfs.huggingface.co:127.0.0.1 --add-host=hf.co:127.0.0.1 --add-host=huggingface.co:127.0.0.1 --add-host=s3.amazonaws.com:127.0.0.1 --add-host=raw.githubusercontent.com:127.0.0.1 --add-host=git-lfs.github.com:127.0.0.1 --add-host=objects.githubusercontent.com:127.0.0.1 melotts:test`

### Run image - english only
`docker run -p 8888:8888 --gpus all -e TTS_LANGUAGES=EN melotts:test`

### Investigate image without running it (Used to slim the image and see files)
`docker run -it --rm --entrypoint bash sensejworld/melotts:latest`

### Check UI
Open http://localhost:8888

### Rapid local UI/API loop
After building an image once, use the bind-mounted tasks for `melo/app.py` edits:

```bash
task localdev
task localapi
```

These mount `melo/app.py` into the container so most UI/API changes do not require a Docker rebuild.

### Check API - ping
```bash
curl -v http://localhost:8888/tts/ping
```

### Check API - tts
```bash
curl -v -X POST http://localhost:8888/tts/convert/tts ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"Hello world. I wanted to test this and see if this works properly\",\"speed\":1.0,\"language\":\"EN\",\"speaker_id\":\"EN-BR\",\"sdp_ratio\":\"0.21\",\"noise_scale\":\"0.61\",\"noise_scale_w\":\"0.81\"}" ^
  --output hello.wav
```

### Check API - compact output
```bash
curl -v -X POST http://localhost:8888/tts/convert/tts ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"Hello world. I wanted to test MP3 output\",\"language\":\"EN\",\"speaker_id\":\"EN-BR\",\"format\":\"mp3\"}" ^
  --output hello.mp3
```

Available response formats:
```bash
curl -v http://localhost:8888/tts/formats
```

The UI has an Output Format dropdown and defaults to MP3. The API remains WAV-by-default when `format` is omitted.

### Check API - languages
```bash
curl -v http://localhost:8888/tts/languages
```

### Check API - languages
```bash
curl -v "http://localhost:8888/tts/speakers?language=EN"
```

### Clean docker
`docker system prune -a --volumes`

## Common Operations
- Port 8888 is exposed for web interface
- Use `--gpus all` only if NVIDIA drivers and Docker GPU support is installed


## Dependency management

Python dependency files in this repo:

- `requirements.in` is the short human-edited list. It says what this project directly needs.
- `requirements.txt` is the full resolved/pinned list. Docker installs this file so builds are repeatable.
- `uv` is the resolver. It reads `requirements.in`, figures out all transitive dependencies, and writes `requirements.txt`.

Go comparison:

- `requirements.in` is a little like the dependencies you intentionally care about.
- `requirements.txt` is closer to a lock file: exact versions that are known to work.
- `uv pip compile` is the command that refreshes the lock-like file.

Install `uv` on Windows:

```bash
winget install --id=astral-sh.uv -e
```

Refresh Python dependencies:

```bash
uv pip compile requirements.in --upgrade --python-version 3.10 --no-header --no-annotate --output-file requirements.txt
```

After this command, inspect `requirements.txt`. It may change many indirect packages even if `requirements.in` is small.

Add a new direct dependency:

1. Add the package name to `requirements.in`.
2. Run the resolver command above.
3. Build and test Docker.

Remove a dependency:

1. Remove it from `requirements.in`.
2. Run the resolver command above.
3. Check whether it disappeared from `requirements.txt`.
4. Build and test Docker.

Docker remains the expected validation environment for dependency upgrades:

```bash
task imagesmall
task localapi
```

Check dependency consistency inside the running container:

```bash
docker exec melotts_local python -m pip check
```

Print key runtime versions:

```bash
docker exec melotts_local python -c "import gradio, fastapi, starlette, pydantic, torch, torchaudio, transformers, numpy, soundfile; print('gradio', gradio.__version__); print('fastapi', fastapi.__version__); print('starlette', starlette.__version__); print('pydantic', pydantic.__version__); print('torch', torch.__version__); print('torchaudio', torchaudio.__version__); print('transformers', transformers.__version__); print('numpy', numpy.__version__); print('soundfile', soundfile.__version__)"
```

## Release

Root `VERSION` is the release source of truth. A standard patch release can be prepared from a clean working tree with:

    task release

The task requires `VERSION` to be a snapshot such as `v0.0.8-SNAPSHOT`. It commits `VERSION=v0.0.8`, creates tag `v0.0.8`, then commits the next patch snapshot such as `v0.0.9-SNAPSHOT`. Override the release or next version only when needed:

    task release RELEASE_VERSION=v0.0.8 NEXT_VERSION=v0.1.0-SNAPSHOT

Publish the prepared release with:

    task releasepush RELEASE_VERSION=v0.0.8

This pushes the release tag first so GitHub Actions runs the tag build, then pushes `main` with the next `-SNAPSHOT` version.
