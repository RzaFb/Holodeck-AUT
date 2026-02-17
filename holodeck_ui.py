#!/usr/bin/env python3
import os
import sys
import subprocess
import shlex
import time
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Holodeck one-command UI (model / key / flags & Unity connect)")

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".holodeck.env"

DEFAULT_BASE = "https://models.github.ai/inference"
DEFAULT_MODEL = "openai/gpt-4.1"
ALT_MODEL = "openai/gpt-4o-mini"  # quota-friendly
PYTHON = sys.executable  # use current env

def load_env_file():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

def save_env_file(pairs: dict, include_key: bool = False):
    existing = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
    for k, v in pairs.items():
        if k == "OPENAI_API_KEY" and not include_key:
            continue
        existing[k] = v
    with ENV_FILE.open("w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
    typer.secho(f"Saved defaults to {ENV_FILE}", fg=typer.colors.GREEN)

def bump_nofile_limit(target: int = 8192):
    try:
        import resource  # Linux/Unix only
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        new_soft = min(max(target, soft), hard)
        if new_soft != soft:
            resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft, hard))
            typer.secho(f"Raised RLIMIT_NOFILE: {soft} -> {new_soft}", fg=typer.colors.BLUE)
    except Exception:
        pass  # ignore if not supported

def latest_scene_json() -> Optional[Path]:
    scenes_root = ROOT / "data" / "scenes"
    if not scenes_root.exists():
        return None
    dirs = sorted(scenes_root.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for d in dirs:
        js = sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if js:
            return js[0]
    return None

def run_stream(cmd: list, env: dict):
    # pretty, shell-ready command preview
    try:
        print(shlex.join(cmd))
    except Exception:
        print(" ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, cwd=str(ROOT), text=True, bufsize=1)
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            print(line, end="")
    except KeyboardInterrupt:
        proc.terminate()
    finally:
        proc.wait()
    return proc.returncode

@app.command()
def generate(
    prompt: str = typer.Option(..., "--prompt", "-p", help="Scene description"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", "-m", help="Model id (e.g., openai/gpt-4.1 or openai/gpt-4o-mini)"),
    base_url: str = typer.Option(DEFAULT_BASE, "--base", help="OpenAI-compatible API base"),
    api_key: str = typer.Option("", "--key", help="API key (GitHub token). If omitted, uses env OPENAI_API_KEY or GITHUB_TOKEN"),
    generate_image: bool = typer.Option(False, "--image/--no-image", help="Generate images"),
    generate_video: bool = typer.Option(False, "--video/--no-video", help="Generate video"),
    add_ceiling: bool = typer.Option(True, "--ceiling/--no-ceiling", help="Add ceiling"),
    single_room: bool = typer.Option(True, "--single-room/--multi-room", help="Force single room"),
    fast_mode: bool = typer.Option(True, "--fast/--full", help="Fast mode (fewer unique assets)"),
    remember_defaults: bool = typer.Option(False, "--remember", help="Remember base/model in .holodeck.env (not the key unless you also pass --remember-key)"),
    remember_key: bool = typer.Option(False, "--remember-key", help="Also save your API key in .holodeck.env"),
):
    """
    Generate a Holodeck scene without remembering long commands.
    """
    load_env_file()
    bump_nofile_limit()

    # Resolve API key
    key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("GITHUB_TOKEN")
    if not key:
        typer.secho("No API key provided. Use --key or set OPENAI_API_KEY/GITHUB_TOKEN.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Prepare environment for the child process
    child_env = os.environ.copy()
    # Old OpenAI SDK (0.27.6) + langchain==0.0.171 expect this:
    child_env["OPENAI_API_BASE"] = base_url
    child_env["OPENAI_API_KEY"] = key
    # Our patched code reads these as well:
    child_env["OPENAI_BASE_URL"] = base_url
    child_env["HOLODECK_MODEL"] = model
    if fast_mode:
        child_env["HOLODECK_FAST"] = "1"
    # Safer Torch sharing (if present)
    child_env.setdefault("OMP_NUM_THREADS", "1")

    # Build command to call Holodeck
    cmd = [
        PYTHON, "-m", "ai2holodeck.main",
        "--mode", "generate_single_scene",
        "--query", prompt,
        "--openai_api_key", key,
        "--model", model,
        "--generate_image", str(generate_image),
        "--generate_video", str(generate_video),
        "--add_ceiling", str(add_ceiling),
        "--single_room", str(single_room),
    ]
    typer.secho("\n▶ Generating scene…\n", fg=typer.colors.GREEN)
    rc = run_stream(cmd, child_env)
    if rc != 0:
        typer.secho(f"\nHolodeck exited with code {rc}", fg=typer.colors.RED)
        raise typer.Exit(rc)

    scene = latest_scene_json()
    if scene:
        typer.secho(f"\n✓ Latest scene: {scene}", fg=typer.colors.GREEN)
    else:
        typer.secho("\n(no scene json found yet under data/scenes)", fg=typer.colors.YELLOW)

    # Save defaults if requested
    if remember_defaults or remember_key:
        pairs = {
            "OPENAI_API_BASE": base_url,
            "OPENAI_BASE_URL": base_url,
            "HOLODECK_MODEL": model,
        }
        if remember_key:
            pairs["OPENAI_API_KEY"] = key
        save_env_file(pairs, include_key=remember_key)

@app.command()
def connect(
    scene: Optional[Path] = typer.Option(None, "--scene", "-s", exists=False, help="Path to scene json (defaults to latest)"),
    port: int = typer.Option(8200, "--port", "-p", help="Unity Editor port"),
):
    """
    Connect the (Unity) AI2-THOR Editor to a scene. Open the Editor, press Play on Procedural.unity,
    then run this to attach.
    """
    load_env_file()
    bump_nofile_limit()

    sj = scene or latest_scene_json()
    if not sj or not Path(sj).exists():
        typer.secho("Could not find a scene json. Run `generate` first or pass --scene.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Choose your connector; if you created connect_to_unity.py, use that.
    connector = ROOT / "connect_to_unity.py"
    if not connector.exists():
        typer.secho("connector script connect_to_unity_editor.py not found. Using minimal Controller ping instead.", fg=typer.colors.YELLOW)
        # Minimal ping fallback
        code = f"""
from ai2thor.controller import Controller
c = Controller(host="127.0.0.1", port={port}, launch_build=False, scene="Procedural", width=1024, height=768)
print("Connected to editor. Frame OK:", hasattr(c.step(action="Pass"), "frame"))
"""
        cmd = [PYTHON, "-c", code]
    else:
        cmd = [PYTHON, str(connector), "--scene", str(sj), "--port", str(port)]

    typer.secho(f"\n▶ Connecting Unity Editor on port {port} with scene:\n   {sj}\n", fg=typer.colors.GREEN)
    rc = run_stream(cmd, os.environ.copy())
    if rc != 0:
        typer.secho(f"\nConnector exited with code {rc}", fg=typer.colors.RED)
        raise typer.Exit(rc)

if __name__ == "__main__":
    app()
