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

    winget install --id=astral-sh.uv -e
    uv pip compile requirements.txt --resolution lowest --output-file requirements.txt