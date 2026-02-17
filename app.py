#!/usr/bin/env python3
import os, sys, subprocess, time, json, shutil
from pathlib import Path
from typing import Optional, List
import shlex

import streamlit as st

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
ENV_FILE = ROOT / ".holodeck.env"

DEFAULT_BASE = "https://models.github.ai/inference"
DEFAULT_MODEL = "openai/gpt-4.1"
ALT_MODEL = "openai/gpt-4o-mini"  # quota-friendly

def bump_nofile_limit(target: int = 8192):
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        new_soft = min(max(target, soft), hard)
        if new_soft != soft:
            resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft, hard))
            st.info(f"Raised file-descriptor limit: {soft} → {new_soft}")
    except Exception:
        pass

def load_env_file():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

def save_env_file(pairs: dict, include_key: bool = False):
    existing = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
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

def list_scene_jsons(limit: int = 10) -> List[Path]:
    scenes_root = ROOT / "data" / "scenes"
    if not scenes_root.exists():
        return []
    all_jsons: List[Path] = []
    for d in sorted(scenes_root.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
        all_jsons.extend(sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True))
        if len(all_jsons) >= limit:
            break
    return all_jsons[:limit]

def latest_scene_json() -> Optional[Path]:
    js = list_scene_jsons(limit=1)
    return js[0] if js else None

def run_stream(cmd: list, env: dict):
    """Run a command, stream stdout into Streamlit."""
    try:
        preview = shlex.join(cmd)
    except Exception:
        preview = " ".join(cmd)
    st.code(preview, language="bash")
    placeholder = st.empty()
    lines = []
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=str(ROOT), env=env, text=True, bufsize=1)
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line.rstrip("\n"))
            # keep last 500 lines for rendering speed
            view = "\n".join(lines[-500:])
            placeholder.text(view)
        proc.wait()
    except Exception as e:
        lines.append(f"[stream error] {e}")
        placeholder.text("\n".join(lines[-500:]))
    return proc.returncode

# ---------------- UI ----------------
st.set_page_config(page_title="Holodeck Dashboard", layout="wide")
st.title("🎮 Holodeck Dashboard")

load_env_file()
bump_nofile_limit()

with st.sidebar:
    st.header("Connection & Defaults")
    base_url = st.text_input("API Base", value=os.getenv("OPENAI_API_BASE", DEFAULT_BASE))
    model = st.selectbox(
        "Model",
        options=[DEFAULT_MODEL, ALT_MODEL, os.getenv("HOLODECK_MODEL", DEFAULT_MODEL)],
        index=0,
    )
    custom_model = st.text_input("Custom model (optional)", value="")
    if custom_model.strip():
        model = custom_model.strip()

    api_key = st.text_input("API Key (GitHub token)", type="password", value=os.getenv("OPENAI_API_KEY", os.getenv("GITHUB_TOKEN", "")))
    remember = st.checkbox("Remember base/model in .holodeck.env", value=True)
    remember_key = st.checkbox("Remember API key (plain text)", value=False)

    st.divider()
    st.caption("Unity Editor port for Procedural.unity")
    unity_port = st.number_input("Unity Editor Port", min_value=1, max_value=65535, value=8200, step=1)

tab_gen, tab_connect, tab_scout = st.tabs(["🧪 Generate Scene", "🧷 Connect Unity Editor", "🗂 Scenes / Tools"])

with tab_gen:
    st.subheader("Generate a scene")
    prompt = st.text_area("Prompt", height=120, placeholder="e.g., a cozy living room with a sofa and a coffee table")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        single_room = st.checkbox("Single room", value=True)
    with col2:
        add_ceiling = st.checkbox("Add ceiling", value=True)
    with col3:
        gen_image = st.checkbox("Generate image", value=False)
    with col4:
        gen_video = st.checkbox("Generate video", value=False)
    with col5:
        fast_mode = st.checkbox("Fast mode", value=True, help="Reduce unique assets to stabilize runtime")

    if st.button("🚀 Generate", type="primary", use_container_width=True):
        if not prompt.strip():
            st.error("Please enter a prompt.")
        elif not api_key.strip():
            st.error("Please provide your API key (GitHub token).")
        else:
            # prepare child env
            child_env = os.environ.copy()
            child_env["OPENAI_API_BASE"] = base_url           # old OpenAI SDK expects this name
            child_env["OPENAI_BASE_URL"] = base_url           # keep both for completeness
            child_env["OPENAI_API_KEY"] = api_key
            child_env["HOLODECK_MODEL"] = model
            if fast_mode:
                child_env["HOLODECK_FAST"] = "1"
            child_env.setdefault("OMP_NUM_THREADS", "1")

            # command matches your main.py flags (strings for booleans)
            cmd = [
                PYTHON, "-m", "ai2holodeck.main",
                "--mode", "generate_single_scene",
                "--query", prompt,
                "--openai_api_key", api_key,
                "--model", model,
                "--generate_image", str(gen_image),
                "--generate_video", str(gen_video),
                "--add_ceiling", str(add_ceiling),
                "--single_room", str(single_room),
            ]
            st.success("Starting generation… logs will appear below.")
            rc = run_stream(cmd, child_env)

            if rc == 0:
                st.success("Generation finished.")
                js = latest_scene_json()
                if js:
                    st.write("Latest scene:", js)
                    try:
                        data = json.loads(js.read_text())
                        st.json(data)
                    except Exception:
                        st.caption("Scene JSON preview not available.")
            else:
                st.error(f"Holodeck exited with code {rc}")

            if remember or remember_key:
                save_env_file(
                    {
                        "OPENAI_API_BASE": base_url,
                        "OPENAI_BASE_URL": base_url,
                        "HOLODECK_MODEL": model,
                        "OPENAI_API_KEY": api_key,
                    },
                    include_key=remember_key,
                )
                st.info(f"Saved defaults to {ENV_FILE}")

with tab_connect:
    st.subheader("Connect the latest scene to Unity Editor")
    st.caption("Open Unity → load **Procedural.unity** → press **Play**, then click Connect.")
    latest = latest_scene_json()
    st.write("Latest scene:", latest if latest else "(no scenes yet)")

    if st.button("🔌 Connect to Unity Editor", use_container_width=True):
        if not latest or not latest.exists():
            st.error("No scene JSON found under data/scenes. Generate one first.")
        else:
            # Use your connector script if present; otherwise minimal ping
            connector = ROOT / "connect_to_unity.py"
            if connector.exists():
                # detect if --port is supported by your script
                supports_port = False
                try:
                    help_out = subprocess.run(
                        [PYTHON, str(connector), "--help"],
                        capture_output=True, text=True, cwd=str(ROOT)
                    )
                    supports_port = "--port" in (help_out.stdout + help_out.stderr)
                except Exception:
                    supports_port = False

                if supports_port:
                    cmd = [PYTHON, str(connector), "--scene", str(latest), "--port", str(unity_port)]
                else:
                    cmd = [PYTHON, str(connector), "--scene", str(latest)]

            else:
                code = f"""
from ai2thor.controller import Controller
c = Controller(host="127.0.0.1", port={unity_port}, launch_build=False, scene="Procedural", width=1024, height=768)
print("Connected to editor. Frame OK:", hasattr(c.step(action="Pass"), "frame"))
"""
                cmd = [PYTHON, "-c", code]

            env = os.environ.copy()
            st.success("Connecting… watch the console below and Unity's Console.")
            rc = run_stream(cmd, env)
            if rc == 0:
                st.success("Editor connection completed.")
            else:
                st.error(f"Connector exited with code {rc}")

    st.divider()
    if st.button("🛑 Kill stray Unity/ai2thor", use_container_width=True):
        for pat in ("ai2thor", "Unity"):
            try:
                subprocess.run(["pkill", "-f", pat], check=False)
            except Exception:
                pass
        st.info("Tried to kill stray Unity/ai2thor processes.")

with tab_scout:
    st.subheader("Scenes & quick tools")
    scenes = list_scene_jsons(limit=12)
    if not scenes:
        st.caption("No scenes yet. Generate one in the first tab.")
    else:
        for js in scenes:
            cols = st.columns([0.6, 0.2, 0.2])
            with cols[0]:
                st.write(js)
            with cols[1]:
                try:
                    st.download_button("Download", data=js.read_bytes(), file_name=js.name, mime="application/json")
                except Exception:
                    st.caption("Can't read file.")
            with cols[2]:
                if st.button("Preview", key=f"pv-{js}"):
                    try:
                        st.json(json.loads(js.read_text()))
                    except Exception:
                        st.caption("Preview error.")

st.caption("Tip: Use **Fast mode** for first runs to pre-warm caches, then uncheck for richer scenes.")
