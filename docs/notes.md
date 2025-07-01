# Development Notes

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
`docker build -t melotts:test .`

### Run image  
`docker run -p 8888:8888 --gpus all melotts:test`

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
  -d "{\"text\":\"Hello world. I wanted to test this and see if this works properly\",\"speed\":1.0,\"language\":\"EN\",\"speaker_id\":\"EN-BR\"}" ^
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

## Version History
### v0.0.1 (2024-06-21)
`docker pull sensejworld/melotts:v0.0.1`
- Initial release
- Basic TTS functionality
- Support for English (Default, US, BR, India, AU)
- Docker support for both CPU and GPU
- Web interface on port 8888 (http://localhost:8888/)


### v0.0.2 (2024-06-22)
- Enable API calls together with UI
- run with `docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.2`
- run for english only `docker run -p 8888:8888 -e TTS_LANGUAGES=EN sensejworld/melotts:v0.0.2`
- run for english and japanese `docker run -p 8888:8888 -e TTS_LANGUAGES=EN,JP sensejworld/melotts:v0.0.2`
- run for english with gpu support named melotts_gpu_en `docker run -p 8888:8888 --gpus all -e TTS_LANGUAGES=EN --name melotts_gpu_en sensejworld/melotts:v0.0.2`

### v0.0.3 (Planned)
- Expose internal settings to api sdp_ratio, noise_scale, noise_scale_w
- run with `docker run -p 8888:8888 --gpus all sensejworld/melotts:v0.0.2`