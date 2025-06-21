# Development Notes

## Version Management
`git tag v0.0.2`  
`git push origin v0.0.2`

## Docker Usage
### CPU Version
docker run -p 8888:8888 sensejworld/melotts

### GPU Version
docker run --gpus all -p 8888:8888 sensejworld/melotts

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


### v0.0.2 (Planned)
- Enable API calls together with UI

