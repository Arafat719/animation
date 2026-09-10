import os

import pytest

import app


def test_sanitize_prompt_basic():
    assert app.sanitize_prompt("  a   b  c ") == "a b c"


def test_sanitize_prompt_length():
    long = "x" * 200
    s = app.sanitize_prompt(long)
    assert isinstance(s, str)
    assert len(s) <= 120


def test_load_character_profile_creates_and_reads(tmp_path):
    # isolate CHARACTER_STORE to temp file
    store = tmp_path / "characters.json"
    app.CHARACTER_STORE = str(store)

    profile = app.load_character_profile("UnitTester", "anime")
    assert profile is not None
    assert profile.get("name") == "UnitTester"
    assert isinstance(profile.get("seed"), int)

    # calling again returns same profile
    profile2 = app.load_character_profile("UnitTester", "anime")
    assert profile2.get("seed") == profile.get("seed")


def test_generate_image_writes_file(tmp_path):
    outdir = tmp_path / "out"
    outdir_str = str(outdir)
    os.makedirs(outdir_str, exist_ok=True)

    path = app.generate_image("test tiny prompt", output_dir=outdir_str, character_name="Tmp", character_style="anime")
    assert path is not None
    assert os.path.exists(path)
    assert str(outdir) in path


def test_main_disable_real_pipe_flag_sets_env(monkeypatch, tmp_path):
    monkeypatch.delenv("DISABLE_REAL_PIPE", raising=False)

    captured = {}

    def fake_generate_image(*args, **kwargs):
        captured["called"] = True
        return str(tmp_path / "fake.png")

    monkeypatch.setattr(app, "generate_image", fake_generate_image)

    result = app.main([
        "--disable-real-pipe",
        "--prompt",
        "anime girl in pastel city",
        "--output-dir",
        str(tmp_path),
        "--character-name",
        "Airi",
    ])

    assert result == str(tmp_path / "fake.png")
    assert captured["called"] is True
    assert os.environ.get("DISABLE_REAL_PIPE") == "1"
