import argparse
import hashlib
import importlib.util
import json
import os
import random
import re
import sys
from datetime import datetime
import logging
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

CHARACTER_STORE = "characters.json"
_REAL_PIPE = None

# configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def _sanitize_filename(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s or "")
    return s.strip("_")[:120] or "image"


def _cache_filename_for(prompt: str, character_name: str | None, character_style: str) -> str:
    key = f"{(prompt or '').strip()}|{(character_name or '').strip()}|{character_style or 'anime'}"
    h = hashlib.md5(key.encode('utf-8')).hexdigest()[:12]
    safe = _sanitize_filename(prompt)[:40].lower()
    return f"{h}_{safe}.png"


def sanitize_prompt(prompt: str) -> str:
    prompt = re.sub(r"\s+", " ", prompt).strip()
    return prompt[:120] if len(prompt) > 120 else prompt


def load_character_profile(character_name: str | None, character_style: str = "anime"):
    name = (character_name or "").strip()
    if not name:
        return None

    if os.path.exists(CHARACTER_STORE):
        try:
            with open(CHARACTER_STORE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            data = {}
    else:
        data = {}

    profile = data.get(name.lower())
    if profile:
        return profile

    seed = int(hashlib.md5(name.lower().encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)
    palette = [
        f"#{rng.randrange(64, 220):02x}{rng.randrange(64, 220):02x}{rng.randrange(64, 220):02x}",
        f"#{rng.randrange(64, 220):02x}{rng.randrange(64, 220):02x}{rng.randrange(64, 220):02x}",
        f"#{rng.randrange(64, 220):02x}{rng.randrange(64, 220):02x}{rng.randrange(64, 220):02x}",
        f"#{rng.randrange(64, 220):02x}{rng.randrange(64, 220):02x}{rng.randrange(64, 220):02x}",
    ]

    profile = {
        "name": name,
        "style": character_style,
        "palette": palette,
        "body_color": palette[0],
        "accent_color": palette[2],
        "head_size": rng.randint(70, 120),
        "body_size": rng.randint(130, 220),
        "eye_gap": rng.randint(12, 24),
        "seed": seed,
    }
    data[name.lower()] = profile
    with open(CHARACTER_STORE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    return profile


def pick_palette(prompt: str, character_profile=None):
    if character_profile and character_profile.get("palette"):
        return character_profile["palette"]

    lowered = prompt.lower()
    palettes = {
        "anime": ["#ff7eb3", "#ffb703", "#7bdff2", "#bde0fe"],
        "cyberpunk": ["#00f5d4", "#ff006e", "#8338ec", "#3a86ff"],
        "sunset": ["#ff7b00", "#ffb703", "#f72585", "#7209b7"],
        "forest": ["#2d6a4f", "#74c69d", "#a8dadc", "#f4f1de"],
        "ocean": ["#023e8a", "#0077b6", "#48cae4", "#caf0f8"],
        "neon": ["#ff00d4", "#00f5d4", "#ffe66d", "#7b2cbf"],
        "default": ["#7c3aed", "#00b4d8", "#f72585", "#ffc857"],
    }

    for key, colors in palettes.items():
        if key in lowered:
            return colors
    return palettes["default"]


def make_gradient(background, colors):
    width, height = background.size
    for y in range(height):
        ratio = y / max(1, height - 1)
        r1, g1, b1 = ImageColorToRGB(colors[0])
        r2, g2, b2 = ImageColorToRGB(colors[1])
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        for x in range(width):
            background.putpixel((x, y), (r, g, b))
    return background


def ImageColorToRGB(hex_color: str):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(ch * 2 for ch in hex_color)
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def blend_color(color, amount):
    r, g, b = ImageColorToRGB(color)
    return tuple(max(0, min(255, int(channel + (255 - channel) * amount))) for channel in (r, g, b))


def create_background(prompt: str, width=1200, height=900, character_profile=None, rng=None):
    # Add optional deterministic RNG support via `rng` parameter.
    # If `rng` is not provided, fall back to the global `random` module.
    rng = rng or random
    palette = pick_palette(prompt, character_profile)
    img = Image.new("RGB", (width, height), "white")
    img = make_gradient(img, palette)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    for i in range(18):
        x = rng.randint(0, width)
        y = rng.randint(0, height)
        radius = rng.randint(80, 220)
        color = palette[rng.randrange(0, len(palette))]
        overlay_draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*ImageColorToRGB(color), 30))

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return img


def draw_prompt_scene(image, prompt: str, character_profile=None, rng=None):
    rng = rng or random
    draw = ImageDraw.Draw(image)
    width, height = image.size
    palette = pick_palette(prompt, character_profile)

    # central composition
    center_x, center_y = width // 2, height // 2
    body = character_profile.get("body_size", rng.randint(130, 220)) if character_profile else rng.randint(130, 220)
    head = character_profile.get("head_size", rng.randint(70, 130)) if character_profile else rng.randint(70, 130)

    # stylized character silhouette
    body_color = ImageColorToRGB(character_profile.get("body_color", palette[0]) if character_profile else palette[0])
    accent_color = ImageColorToRGB(character_profile.get("accent_color", palette[2]) if character_profile else palette[2])

    # body
    draw.ellipse((center_x - body // 2, center_y - body // 2, center_x + body // 2, center_y + body // 2), fill=body_color)
    # head
    draw.ellipse((center_x - head // 2, center_y - body - 30, center_x + head // 2, center_y - body + 100), fill=accent_color)

    # eyes and face features
    eye_y = center_y - body - 20
    eye_gap = character_profile.get("eye_gap", 18) if character_profile else 18
    draw.ellipse((center_x - 30 - eye_gap, eye_y, center_x - 10 - eye_gap, eye_y + 10), fill=(30, 30, 30))
    draw.ellipse((center_x + 10 + eye_gap, eye_y, center_x + 30 + eye_gap, eye_y + 10), fill=(30, 30, 30))
    draw.arc((center_x - 30, center_y - body + 15, center_x + 30, center_y - body + 55), 200, 340, fill=(30, 30, 30), width=4)

    # add decorative shapes (deterministic when rng provided)
    for i in range(10):
        x = rng.randint(40, width - 40)
        y = rng.randint(40, height - 40)
        size = rng.randint(20, 55)
        color = palette[rng.randrange(0, len(palette))]
        draw.rounded_rectangle((x, y, x + size, y + size), radius=10, fill=(*ImageColorToRGB(color), 110))

    # add panels / shapes
    draw.rounded_rectangle((80, 90, width - 80, height - 90), outline=(255, 255, 255, 200), width=4, radius=26)


def add_text_and_title(image, prompt: str):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    safe_prompt = sanitize_prompt(prompt)

    # Title text at bottom
    title = safe_prompt[:40] + ("..." if len(safe_prompt) > 40 else "")
    font_size = 28
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    # find wrap
    wrapped = []
    line = ""
    for word in safe_prompt.split():
        candidate = f"{line} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] > width - 200:
            wrapped.append(line)
            line = word
        else:
            line = candidate
    if line:
        wrapped.append(line)

    border = 40
    total_text_height = len(wrapped) * (font_size + 8)
    y = height - total_text_height - 60
    for part in wrapped:
        bbox = draw.textbbox((0, 0), part, font=font)
        text_x = (width - (bbox[2] - bbox[0])) / 2
        draw.text((text_x, y), part, font=font, fill=(255, 255, 255))
        y += font_size + 10


def get_real_image_pipe():
    global _REAL_PIPE
    # Allow disabling the heavy diffusers/torch pipeline via environment variable
    if os.environ.get('DISABLE_REAL_PIPE', '').lower() in ('1', 'true', 'yes'):
        logging.info('DISABLE_REAL_PIPE is set; skipping real image pipeline')
        return None
    if _REAL_PIPE is not None:
        return _REAL_PIPE

    if importlib.util.find_spec("diffusers") is None or importlib.util.find_spec("torch") is None:
        return None

    try:
        import torch
        from diffusers import AutoPipelineForText2Image
    except Exception:
        return None

    model_id = "stabilityai/sdxl-turbo"
    pipe = AutoPipelineForText2Image.from_pretrained(
        model_id,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )
    pipe.to("cuda" if torch.cuda.is_available() else "cpu")
    _REAL_PIPE = pipe
    return pipe


def generate_real_image(prompt: str, output_dir: str = "output", character_name: str | None = None, character_style: str = "anime", rng=None):
    pipe = get_real_image_pipe()
    if pipe is None:
        raise RuntimeError("Real diffusers backend is not available yet")

    import torch
    safe_prompt = sanitize_prompt(prompt) or "creative concept"
    enhanced_prompt = f"{safe_prompt}, {character_style} anime style, consistent character {character_name or 'hero'}, cinematic lighting, detailed"
    image = pipe(
        prompt=enhanced_prompt,
        num_inference_steps=4,
        guidance_scale=0.0,
        height=1024,
        width=1024,
    ).images[0]

    os.makedirs(output_dir, exist_ok=True)
    # deterministic cache filename for same prompt/character/style
    filename = _cache_filename_for(enhanced_prompt, character_name, character_style)
    save_path = os.path.join(output_dir, filename)
    if os.path.exists(save_path):
        logging.info("Reusing cached real image: %s", save_path)
        return save_path

    image.save(save_path)
    logging.info("Saved real image: %s", save_path)
    return save_path


def generate_image(prompt: str, output_dir: str = "output", character_name: str | None = None, character_style: str = "anime", rng=None):
    try:
        return generate_real_image(prompt, output_dir, character_name, character_style, rng=rng)
    except Exception as e:
        logging.debug("Real image generation unavailable or failed: %s", e)

    os.makedirs(output_dir, exist_ok=True)
    safe_prompt = sanitize_prompt(prompt) or "creative concept"
    character_profile = load_character_profile(character_name, character_style)
    # caching: use deterministic filename so repeated calls reuse existing images
    cache_name = _cache_filename_for(safe_prompt + f"|{character_profile.get('seed') if character_profile else ''}", character_name, character_style)
    save_path = os.path.join(output_dir, cache_name)
    if os.path.exists(save_path):
        logging.info("Reusing cached generated image: %s", save_path)
        return save_path

    image = create_background(safe_prompt, character_profile=character_profile, rng=rng)
    try:
        draw_prompt_scene(image, safe_prompt, character_profile, rng=rng)
    except Exception:
        logging.exception("draw_prompt_scene failed; continuing")
    add_text_and_title(image, safe_prompt)

    image = image.filter(ImageFilter.GaussianBlur(radius=0.3))
    image.save(save_path)
    logging.info("Saved generated image: %s", save_path)
    return save_path


def generate_storyboard(character_name: str | None, scenes: list[str], pose: str = "front", output_dir: str = "output", character_style: str = "anime", variation_strength: float = 0.5):
    if not scenes:
        return []
    results = []

    profile = load_character_profile(character_name, character_style)
    if profile and profile.get("seed"):
        base_seed = int(profile.get("seed"))
    else:
        key = (character_name or "") + "|" + "||".join(scenes)
        base_seed = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16)

    for index, scene in enumerate(scenes, start=1):
        cleaned = sanitize_prompt(scene)
        if not cleaned:
            continue

        frame_seed = base_seed + index
        frame_rng = random.Random(frame_seed)

        base_prompt = f"{cleaned}, {pose} pose, anime character {character_name or 'hero'}, consistent face, detailed expression, cinematic lighting"
        result = generate_image(base_prompt, output_dir, character_name, character_style, rng=frame_rng)
        results.append({
            "scene": index,
            "prompt": cleaned,
            "image_path": result,
            "pose": pose,
        })
    return results


def list_characters():
    if not os.path.exists(CHARACTER_STORE):
        return []
    try:
        with open(CHARACTER_STORE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return []
    names = []
    for key, profile in data.items():
        if isinstance(profile, dict) and profile.get("name"):
            names.append(profile["name"])
    return sorted(set(names))


def create_animation_from_frames(frame_paths: list[str], output_dir: str = "output", fps: int = 2):
    return _create_animation_with_format(frame_paths, output_dir, fps, output_format='gif')


def _create_animation_with_format(frame_paths: list[str], output_dir: str = "output", fps: int = 2, output_format: str = 'gif'):
    if not frame_paths:
        return None

    images = []
    for frame_path in frame_paths:
        if os.path.exists(frame_path):
            images.append(Image.open(frame_path).convert("RGB"))

    if not images:
        return None

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    gif_path = os.path.join(output_dir, f"{timestamp}_storyboard_animation.gif")
    images[0].save(
        gif_path,
        save_all=True,
        append_images=images[1:],
        duration=int(1000 / max(1, fps)),
        loop=0,
    )

    if output_format.lower() == 'gif':
        return gif_path

    # for mp4 conversion, require ffmpeg on PATH
    if output_format.lower() in ('mp4', 'video', 'h264'):
        mp4_path = os.path.splitext(gif_path)[0] + '.mp4'
        ffmpeg_path = shutil.which('ffmpeg')
        if not ffmpeg_path:
            logging.warning('ffmpeg not found on PATH; cannot convert GIF to MP4')
            return gif_path

        try:
            # convert gif to mp4 with reasonable defaults
            cmd = [ffmpeg_path, '-y', '-i', gif_path, '-movflags', 'faststart', '-pix_fmt', 'yuv420p', mp4_path]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info('Converted GIF to MP4: %s', mp4_path)
            return mp4_path
        except subprocess.CalledProcessError as exc:
            logging.exception('ffmpeg conversion failed: %s', exc)
            return gif_path

    return gif_path


def main():
    parser = argparse.ArgumentParser(description="Simple prompt-to-image starter generator.")
    parser.add_argument("--prompt", type=str, default="anime girl in neon city at sunset", help="Prompt text for the image")
    parser.add_argument("--output-dir", type=str, default="output", help="Directory where images are saved")
    parser.add_argument("--character-name", type=str, default="", help="Name of the character to keep consistent across generations")
    parser.add_argument("--character-style", type=str, default="anime", help="Character style")
    args = parser.parse_args()

    prompt = args.prompt.strip() or "anime girl in neon city at sunset"
    result = generate_image(prompt, args.output_dir, args.character_name, args.character_style)
    print(f"Image created: {result}")


if __name__ == "__main__":
    main()
