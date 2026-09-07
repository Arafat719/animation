import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from app import create_animation_from_frames, generate_image, generate_storyboard

HOST = "0.0.0.0"
PORT = 8000
OUTPUT_DIR = "output"

HTML_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Animora Studio Starter</title>
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --panel-2: #1f2937;
      --accent: #8b5cf6;
      --accent-2: #22d3ee;
      --text: #e5e7eb;
      --muted: #94a3b8;
      --border: rgba(148, 163, 184, 0.22);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, sans-serif;
      background: linear-gradient(135deg, #0f172a, #111827 40%, #1e1b4b);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 24px;
    }
    .app {
      width: min(980px, 100%);
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 22px 50px rgba(15, 23, 42, 0.7);
      padding: 24px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 22px;
      gap: 12px;
    }
    .brand {
      font-size: 2rem;
      font-weight: 700;
      letter-spacing: 0.05em;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .status {
      font-size: 0.82rem;
      color: var(--muted);
      border: 1px solid var(--border);
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(148, 163, 184, 0.05);
    }
    .download-btn {
      padding: 10px 14px;
      background: rgba(34, 211, 238, 0.12);
      border: 1px solid rgba(34, 211, 238, 0.35);
      color: var(--text);
      border-radius: 12px;
      cursor: pointer;
      font-weight: 600;
    }
    .grid {
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 22px;
    }
    .panel {
      background: rgba(17, 24, 39, 0.95);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 18px;
    }
    .storyboard {
      margin-top: 20px;
    }
    .field-row {
      display: grid;
      grid-template-columns: 1fr 180px;
      gap: 12px;
      margin-bottom: 12px;
    }
    label {
      display: block;
      font-size: 0.9rem;
      margin-bottom: 8px;
      color: var(--muted);
    }
    input, select, textarea {
      width: 100%;
      border-radius: 12px;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 12px 14px;
      font-size: 1rem;
    }
    textarea {
      width: 100%;
      min-height: 140px;
      border-radius: 12px;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 12px 14px;
      font-size: 1rem;
      resize: vertical;
    }
    .actions {
      margin-top: 16px;
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
    button {
      border: none;
      border-radius: 12px;
      padding: 12px 18px;
      font-size: 1rem;
      font-weight: 700;
      cursor: pointer;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
      color: #fff;
      box-shadow: 0 10px 25px rgba(139, 92, 246, 0.35);
    }
    button.secondary {
      background: transparent;
      border: 1px solid var(--border);
      box-shadow: none;
      color: var(--text);
    }
    .preview {
      min-height: 420px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 14px;
      background: linear-gradient(135deg, #111827, #1f2937);
      border: 1px solid var(--border);
      overflow: hidden;
      position: relative;
    }
    .preview img {
      width: 100%;
      height: 100%;
      max-height: 430px;
      object-fit: cover;
      display: none;
    }
    .video-panel {
      margin-top: 20px;
      background: rgba(17, 24, 39, 0.95);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 18px;
    }
    .video-panel video, .video-panel img {
      width: 100%;
      max-height: 380px;
      border-radius: 12px;
      display: none;
    }
    .compact-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 12px;
    }
    .chip {
      background: rgba(139, 92, 246, 0.14);
      border: 1px solid rgba(139, 92, 246, 0.35);
      color: var(--text);
      border-radius: 999px;
      padding: 7px 11px;
      cursor: pointer;
      font-size: 0.8rem;
    }
    .gallery {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }
    .thumb {
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
    }
    .thumb img {
      width: 100%;
      height: 180px;
      object-fit: cover;
      display: block;
    }
    .thumb-label {
      padding: 8px 10px;
      font-size: 0.75rem;
      color: var(--muted);
    }
    .placeholder {
      color: var(--muted);
      text-align: center;
      padding: 30px;
      line-height: 1.7;
    }
    .meta {
      margin-top: 16px;
      color: var(--muted);
      font-size: 0.82rem;
    }
    @media (max-width: 760px) {
      .grid { grid-template-columns: 1fr; }
      .header { flex-direction: column; align-items: flex-start; }
    }
  </style>
</head>
<body>
  <div class="app">
    <div class="header">
      <div class="brand">Animora Studio</div>
      <div class="status">AI anime studio prototype</div>
    </div>

    <div class="grid">
      <div class="panel">
        <div class="field-row">
          <div>
            <label for="characterName">Character name</label>
            <input id="characterName" value="Airi" placeholder="Airi" />
          </div>
          <div>
            <label for="style">Style</label>
            <select id="style">
              <option value="anime" selected>Anime</option>
              <option value="cyberpunk">Cyberpunk</option>
              <option value="sunset">Sunset</option>
              <option value="ocean">Ocean</option>
              <option value="forest">Forest</option>
            </select>
          </div>
        </div>

        <label for="prompt">Prompt</label>
        <textarea id="prompt" placeholder="Example: anime girl in neon city at sunset, cinematic lighting, detailed face, high quality">anime girl in neon city at sunset</textarea>

        <div class="field-row" style="margin-top: 16px;">
          <div>
            <label for="pose">Pose</label>
            <select id="pose">
              <option value="front" selected>Front</option>
              <option value="side">Side</option>
              <option value="running">Running</option>
              <option value="smile">Smile</option>
              <option value="angry">Angry</option>
            </select>
          </div>
          <div>
            <label for="sceneCount">Scenes</label>
            <select id="sceneCount">
              <option value="3" selected>3</option>
              <option value="4">4</option>
              <option value="5">5</option>
            </select>
          </div>
        </div>

        <label for="scenePrompts">Storyboard scenes</label>
        <textarea id="scenePrompts" rows="6" placeholder="One scene per line">neon street at night
coffee shop interior
rooftop sunset
emotional close-up</textarea>

        <div class="actions">
          <button id="generateBtn">Generate</button>
          <button id="storyboardBtn" class="secondary">Generate storyboard</button>
          <button id="animateBtn" class="secondary">Create animation</button>
          <button class="secondary" id="sampleBtn" type="button">Use example</button>
        </div>
        <div class="actions" style="margin-top: 12px;">
          <button class="download-btn" id="downloadImageBtn" type="button">Download image</button>
          <button class="download-btn" id="downloadAnimationBtn" type="button">Download animation</button>
        </div>
        <div class="meta">This version focuses on one character across multiple scene prompts, pose variations, and short animation export.</div>
      </div>

      <div class="panel preview" id="previewPanel">
        <div class="placeholder" id="placeholder">
          Your generated image will appear here.<br />
          Start with a prompt and click Generate.
        </div>
        <img id="resultImage" alt="Generated artwork" />
      </div>
    </div>

    <div class="panel storyboard">
      <h3 style="margin-top:0;">Storyboard output</h3>
      <div id="timelineList" class="compact-row"></div>
      <div class="gallery" id="storyboardGallery"></div>
    </div>

    <div class="panel">
      <h3 style="margin-top:0;">Saved characters</h3>
      <div id="savedCharacters" class="compact-row"></div>
    </div>

    <div class="video-panel">
      <h3 style="margin-top:0;">Animation preview</h3>
      <img id="animationPreview" alt="Animation preview" />
    </div>
  </div>

  <script>
    const promptInput = document.getElementById('prompt');
    const characterNameInput = document.getElementById('characterName');
    const styleInput = document.getElementById('style');
    const poseInput = document.getElementById('pose');
    const sceneCountInput = document.getElementById('sceneCount');
    const scenePromptsInput = document.getElementById('scenePrompts');
    const generateBtn = document.getElementById('generateBtn');
    const storyboardBtn = document.getElementById('storyboardBtn');
    const animateBtn = document.getElementById('animateBtn');
    const sampleBtn = document.getElementById('sampleBtn');
    const downloadImageBtn = document.getElementById('downloadImageBtn');
    const downloadAnimationBtn = document.getElementById('downloadAnimationBtn');
    const resultImage = document.getElementById('resultImage');
    const animationPreview = document.getElementById('animationPreview');
    const placeholder = document.getElementById('placeholder');
    const storyboardGallery = document.getElementById('storyboardGallery');
    const savedCharacters = document.getElementById('savedCharacters');
    const timelineList = document.getElementById('timelineList');

    function setLoading(isLoading) {
      generateBtn.disabled = isLoading;
      generateBtn.textContent = isLoading ? 'Generating...' : 'Generate';
    }

    sampleBtn.addEventListener('click', () => {
      promptInput.value = 'cyberpunk anime hero standing under neon rain';
      scenePromptsInput.value = 'neon street at night\ncoffee shop interior\nrooftop sunset\nclose-up emotional moment';
    });

    function renderStoryboard(items) {
      storyboardGallery.innerHTML = '';
      timelineList.innerHTML = '';

      items.forEach((item) => {
        const card = document.createElement('div');
        card.className = 'thumb';
        card.innerHTML = `
          <img src="${item.image_url}" alt="${item.prompt}" />
          <div class="thumb-label">Scene ${item.scene}: ${item.pose}</div>
        `;
        storyboardGallery.appendChild(card);

        const chip = document.createElement('button');
        chip.className = 'chip';
        chip.type = 'button';
        chip.textContent = `Scene ${item.scene}`;
        chip.onclick = () => {
          scenePromptsInput.value = items.map((entry) => entry.prompt).join('\n');
          promptInput.value = items[0].prompt;
        };
        timelineList.appendChild(chip);
      });
    }

    function downloadAsset(url, filename) {
      if (!url) return;
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
    }

    function renderCharacters(characterNames) {
      savedCharacters.innerHTML = '';
      if (!characterNames.length) {
        savedCharacters.innerHTML = '<span class="thumb-label">No saved characters yet</span>';
        return;
      }
      characterNames.forEach((name) => {
        const chip = document.createElement('button');
        chip.className = 'chip';
        chip.type = 'button';
        chip.textContent = name;
        chip.onclick = () => {
          characterNameInput.value = name;
          promptInput.value = `${name} in a dramatic anime scene`;
        };
        savedCharacters.appendChild(chip);
      });
    }

    async function refreshCharacters() {
      try {
        const response = await fetch('/characters');
        const data = await response.json();
        renderCharacters(Array.isArray(data.characters) ? data.characters : []);
      } catch (error) {
        renderCharacters([]);
      }
    }

    async function generateSingleImage() {
      const prompt = promptInput.value.trim();
      if (!prompt) {
        promptInput.focus();
        return;
      }

      setLoading(true);
      placeholder.style.display = 'block';
      resultImage.style.display = 'none';

      try {
        const response = await fetch('/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({
            prompt,
            character_name: characterNameInput.value.trim(),
            character_style: styleInput.value
          })
        });

        const data = await response.json();
        if (!response.ok || !data.image_url) {
          throw new Error(data.error || 'Generation failed');
        }

        resultImage.src = data.image_url + '?t=' + Date.now();
        resultImage.style.display = 'block';
        placeholder.style.display = 'none';
        await refreshCharacters();
      } catch (error) {
        placeholder.innerHTML = 'Generation failed.<br />' + error.message;
        placeholder.style.display = 'block';
      } finally {
        setLoading(false);
      }
    }

    generateBtn.addEventListener('click', generateSingleImage);

    async function generateStoryboardData() {
      const characterName = characterNameInput.value.trim();
      const scenes = scenePromptsInput.value
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .slice(0, Number(sceneCountInput.value || 3));

      if (!scenes.length) {
        placeholder.innerHTML = 'Add at least one scene prompt.';
        placeholder.style.display = 'block';
        return null;
      }

      setLoading(true);
      placeholder.style.display = 'block';
      resultImage.style.display = 'none';

      try {
        const response = await fetch('/storyboard', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({
            character_name: characterName,
            character_style: styleInput.value,
            pose: poseInput.value,
            scenes: JSON.stringify(scenes)
          })
        });

        const data = await response.json();
        if (!response.ok || !Array.isArray(data.frames)) {
          throw new Error(data.error || 'Storyboard generation failed');
        }

        renderStoryboard(data.frames);
        placeholder.style.display = 'none';
        if (data.frames[0]) {
          resultImage.src = data.frames[0].image_url + '?t=' + Date.now();
          resultImage.style.display = 'block';
        }
        return data.frames;
      } catch (error) {
        placeholder.innerHTML = 'Storyboard failed.<br />' + error.message;
        placeholder.style.display = 'block';
        return null;
      } finally {
        setLoading(false);
      }
    }

    downloadImageBtn.addEventListener('click', () => {
      if (resultImage.src && resultImage.style.display !== 'none') {
        downloadAsset(resultImage.src, 'generated-image.png');
      }
    });

    downloadAnimationBtn.addEventListener('click', () => {
      if (animationPreview.src && animationPreview.style.display !== 'none') {
        downloadAsset(animationPreview.src, 'generated-animation.gif');
      }
    });

    storyboardBtn.addEventListener('click', async () => {
      await generateStoryboardData();
      await refreshCharacters();
    });

    animateBtn.addEventListener('click', async () => {
      const frames = await generateStoryboardData();
      if (!frames || !frames.length) return;

      try {
        const response = await fetch('/animate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({
            character_name: characterNameInput.value.trim(),
            character_style: styleInput.value,
            pose: poseInput.value,
            scenes: JSON.stringify(frames.map((frame) => frame.prompt))
          })
        });

        const data = await response.json();
        if (!response.ok || !data.animation_url) {
          throw new Error(data.error || 'Animation generation failed');
        }

        animationPreview.src = data.animation_url + '?t=' + Date.now();
        animationPreview.style.display = 'block';
      } catch (error) {
        placeholder.innerHTML = 'Animation failed.<br />' + error.message;
        placeholder.style.display = 'block';
      }
    });
    refreshCharacters();
  </script>
</body>
</html>
"""


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
            return

        if path == '/characters':
            from app import list_characters
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'characters': list_characters()}).encode('utf-8'))
            return

        if path == '/api/v1/characters':
            from app import list_characters
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'characters': list_characters()}).encode('utf-8'))
            return

        if path == '/health' or path == '/api/v1/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
            return

        if path.startswith('/output/') or path.startswith('/images/'):
            file_path = path.lstrip('/')
            if file_path.startswith('images/'):
                file_path = file_path.replace('images/', '', 1)
            local_path = os.path.normpath(os.path.join(os.getcwd(), file_path))
            if os.path.exists(local_path) and local_path.startswith(os.path.abspath(os.getcwd())):
                self.send_response(200)
                if local_path.endswith('.gif'):
                    self.send_header('Content-Type', 'image/gif')
                else:
                    self.send_header('Content-Type', 'image/png')
                self.end_headers()
                with open(local_path, 'rb') as f:
                    self.wfile.write(f.read())
                return

        self.send_error(404, 'Not found')

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length) if length > 0 else b''
        content_type = self.headers.get('Content-Type', '')

        # parse body as JSON if JSON, otherwise as form data
        if 'application/json' in content_type:
            try:
                data_json = json.loads(raw.decode('utf-8') or '{}')
            except Exception:
                data_json = {}
            data = None
        else:
            data_json = None
            try:
                data = parse_qs(raw.decode('utf-8') or '')
            except Exception:
                data = {}

        # /generate
        if parsed.path == '/generate':
            if data_json is not None:
                prompt = (data_json.get('prompt') or '').strip()
                character_name = (data_json.get('character_name') or '').strip()
                character_style = (data_json.get('character_style') or 'anime').strip() or 'anime'
            else:
                prompt = (data.get('prompt', [''])[0] or '').strip()
                character_name = (data.get('character_name', [''])[0] or '').strip()
                character_style = (data.get('character_style', ['anime'])[0] or 'anime').strip() or 'anime'

            if not prompt:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Prompt is required'}).encode('utf-8'))
                return

            try:
                file_path = generate_image(prompt, OUTPUT_DIR, character_name, character_style)
                image_url = '/' + file_path.replace(os.sep, '/')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'image_url': image_url, 'filename': os.path.basename(file_path)}).encode('utf-8'))
            except Exception as exc:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Generation failed: {str(exc)}'}).encode('utf-8'))
            return

        # /storyboard
        if parsed.path == '/storyboard':
            try:
                if data_json is not None:
                    character_name = (data_json.get('character_name') or '').strip()
                    character_style = (data_json.get('character_style') or 'anime').strip() or 'anime'
                    pose = (data_json.get('pose') or 'front').strip() or 'front'
                    scene_list = data_json.get('scenes') or []
                else:
                    character_name = (data.get('character_name', [''])[0] or '').strip()
                    character_style = (data.get('character_style', ['anime'])[0] or 'anime').strip() or 'anime'
                    pose = (data.get('pose', ['front'])[0] or 'front').strip() or 'front'
                    scene_list = json.loads(data.get('scenes', ['[]'])[0] or '[]')

                if not isinstance(scene_list, list) or not scene_list:
                    raise ValueError('At least one scene is required')

                storyboard = []
                for index, scene in enumerate(scene_list, start=1):
                    prompt = f"{scene}, {pose} pose, anime character {character_name or 'hero'}, detailed expression, cinematic composition"
                    file_path = generate_image(prompt, OUTPUT_DIR, character_name, character_style)
                    storyboard.append({
                        'scene': index,
                        'pose': pose,
                        'prompt': scene,
                        'image_url': '/' + file_path.replace(os.sep, '/'),
                    })

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'frames': storyboard}).encode('utf-8'))
            except Exception as exc:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Storyboard generation failed: {str(exc)}'}).encode('utf-8'))
            return

        # /animate
        if parsed.path == '/animate':
            try:
                if data_json is not None:
                    character_name = (data_json.get('character_name') or '').strip()
                    character_style = (data_json.get('character_style') or 'anime').strip() or 'anime'
                    pose = (data_json.get('pose') or 'front').strip() or 'front'
                    scene_list = data_json.get('scenes') or []
                else:
                    character_name = (data.get('character_name', [''])[0] or '').strip()
                    character_style = (data.get('character_style', ['anime'])[0] or 'anime').strip() or 'anime'
                    pose = (data.get('pose', ['front'])[0] or 'front').strip() or 'front'
                    scene_list = json.loads(data.get('scenes', ['[]'])[0] or '[]')

                if not isinstance(scene_list, list) or not scene_list:
                    raise ValueError('At least one scene is required')

                frames = generate_storyboard(character_name, scene_list, pose, OUTPUT_DIR, character_style)
                frame_paths = [item['image_path'] for item in frames if item.get('image_path')]
                animation_path = create_animation_from_frames(frame_paths, OUTPUT_DIR, fps=2)
                if not animation_path:
                    raise ValueError('Animation creation failed')

                animation_url = '/' + animation_path.replace(os.sep, '/')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'animation_url': animation_url}).encode('utf-8'))
            except Exception as exc:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Animation failed: {str(exc)}'}).encode('utf-8'))
            return

        self.send_error(404, 'Not found')

    def log_message(self, format, *args):
        return


def run_server():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Server running at http://localhost:{PORT}")
    server.serve_forever()


if __name__ == '__main__':
    run_server()
