# Prompt Image Generator Starter

This project creates a stylized image from a text prompt using Python and Pillow.

## Run

```bash
python3 app.py --prompt "anime girl in neon city at sunset"
```

The generated image will be saved inside the `output/` folder.

## What this is

This is a working starter for an image-generation workflow. It is intentionally lightweight so it runs immediately in a standard Python environment. It can be upgraded later into a real AI image/video animation pipeline.

## Next upgrades

- Real diffusion model integration
- Character consistency
- Pose/expression controls
- Short video generation
- Storyboard / animation timeline
- LoRA-based character training

## HTTP API (local)

The project includes a tiny HTTP server (`web_app.py`) exposing a few helpful endpoints for programmatic use. Start the server and call the endpoints locally:

Start server:

```bash
python3 web_app.py
# Opens at http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/health
```

List saved characters:

```bash
curl http://localhost:8000/characters
curl http://localhost:8000/api/v1/characters
```

Generate a single image (form-encoded):

```bash
curl -X POST http://localhost:8000/generate \
	-H "Content-Type: application/x-www-form-urlencoded" \
	-d "prompt=anime+girl+in+neon+city&character_name=Airi&character_style=anime"
```

Generate a storyboard (JSON):

```bash
curl -X POST http://localhost:8000/storyboard \
	-H "Content-Type: application/json" \
	-d '{"character_name":"Airi","character_style":"anime","pose":"front","scenes":["neon street","rooftop"]}'
```

Create an animation (GIF) from scenes (JSON):

```bash
curl -X POST http://localhost:8000/animate \
	-H "Content-Type: application/json" \
	-d '{"character_name":"Airi","character_style":"anime","pose":"front","scenes":["neon street","rooftop","close-up"]}'
```

Notes:
- Generated images and GIFs are saved under the `output/` folder and returned as paths (e.g. `/output/2026...png`).
- MP4 export is not enabled by default; to convert GIF→MP4 install `ffmpeg` and run locally:

```bash
ffmpeg -y -i output/<name>.gif -movflags +faststart -pix_fmt yuv420p output/<name>.mp4
```

Dependencies:

```bash
python3 -m pip install -r requirements.txt
```

