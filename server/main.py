import os
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

# Optional: OpenAI client
try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), 'workflows')
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), 'outputs')

PREFERENCES_PATH = os.path.join(DATA_DIR, 'preferences.json')
HISTORY_PATH = os.path.join(DATA_DIR, 'history.json')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(WORKFLOWS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


@app.get('/preferences')
def get_preferences():
    return _read_json(PREFERENCES_PATH, {})


@app.post('/preferences')
def set_preferences(preferences: dict):
    _write_json(PREFERENCES_PATH, preferences)
    return {"ok": True}


@app.get('/history')
def get_history():
    return _read_json(HISTORY_PATH, [])


def _append_history(item: dict) -> None:
    history = _read_json(HISTORY_PATH, [])
    history.insert(0, item)
    _write_json(HISTORY_PATH, history)


def _call_llm_to_generate_workflow(prompt: str, api_key: Optional[str]) -> str:
    # For MVP: return a simple instruction string; integrate OpenAI if key provided
    if api_key and OpenAI is not None:
        try:
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You output ComfyUI workflow JSON or high-level steps."},
                    {"role": "user", "content": f"Create a workflow for: {prompt}"},
                ],
                temperature=0.2,
            )
            return resp.choices[0].message.content or ""
        except Exception:
            pass
    return f"Generate an image based on: {prompt}"


def _execute_comfyui_placeholder(instructions: str, workflow: str) -> str:
    # Placeholder: write a text file as a stand-in for image/video output
    out_name = f"{uuid.uuid4().hex}.txt"
    out_path = os.path.join(OUTPUTS_DIR, out_name)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"Workflow: {workflow}\n")
        f.write(f"Instructions: {instructions}\n")
    return out_path


@app.post('/run_workflow')
def run_workflow(body: dict):
    prompt: str = body.get('prompt', '')
    workflow: str = body.get('workflow', 'image_generation')
    prefs = _read_json(PREFERENCES_PATH, {})
    api_key = prefs.get('openaiApiKey')

    instructions = _call_llm_to_generate_workflow(prompt, api_key)
    result_path = _execute_comfyui_placeholder(instructions, workflow)

    item = {
        'id': uuid.uuid4().hex,
        'prompt': prompt,
        'resultPath': result_path,
        'createdAt': datetime.utcnow().isoformat() + 'Z',
    }
    _append_history(item)
    return {'resultPath': result_path, 'instructions': instructions}


@app.get('/file')
def get_file(path: str = Query(..., description="Absolute or server-relative path to serve")):
    # Security: restrict to OUTPUTS_DIR
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(os.path.abspath(OUTPUTS_DIR)):
        return {"error": "Access denied"}
    return FileResponse(abs_path)


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000)


