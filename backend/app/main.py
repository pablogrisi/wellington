import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.game_engine import WellingtonGame


app = FastAPI(title="Wellington API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GAME = WellingtonGame()
STATE_FILE = Path(__file__).resolve().parents[1] / "game_state.json"
STATE_LOCK = threading.Lock()


def save_game_state() -> None:
    payload = json.dumps(GAME.to_state_dict(), ensure_ascii=False, indent=2)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with STATE_LOCK:
        fd, temp_path = tempfile.mkstemp(
            prefix="game_state_",
            suffix=".tmp",
            dir=str(STATE_FILE.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp:
                tmp.write(payload)
                tmp.flush()
                os.fsync(tmp.fileno())

            for attempt in range(5):
                try:
                    os.replace(temp_path, STATE_FILE)
                    temp_path = ""
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.05 * (attempt + 1))
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass


def load_game_state_or_new() -> None:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            GAME.load_state_dict(data)
            return
        except Exception:
            pass

    GAME.new_game()
    save_game_state()


load_game_state_or_new()


class ReplacePayload(BaseModel):
    slot: int


class AbilityPayload(BaseModel):
    data: Dict[str, Any]


class CutSelfPayload(BaseModel):
    slot: int


class CutOtherPayload(BaseModel):
    target_player: int
    target_slot: int
    give_slot: Optional[int] = None


def safe_action(fn, allow_when_paused: bool = False):
    try:
        if GAME.paused and not allow_when_paused:
            raise ValueError("A partida esta pausada. Clique em Retomar para continuar.")
        fn()
        save_game_state()
        return GAME.public_state()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro interno no servidor: {exc}") from exc


@app.get("/api/state")
def get_state():
    return GAME.public_state()


@app.post("/api/new-game")
def new_game():
    GAME.new_game()
    save_game_state()
    return GAME.public_state()


@app.post("/api/bot-step")
def bot_step():
    return safe_action(GAME.bot_step)


@app.post("/api/pause")
def pause_game():
    return safe_action(GAME.action_pause, allow_when_paused=True)


@app.post("/api/resume")
def resume_game():
    return safe_action(GAME.action_resume, allow_when_paused=True)


@app.post("/api/action/draw")
def action_draw():
    return safe_action(GAME.action_draw)


@app.post("/api/action/discard-drawn")
def action_discard_drawn():
    return safe_action(GAME.action_discard_drawn)


@app.post("/api/action/replace")
def action_replace(payload: ReplacePayload):
    return safe_action(lambda: GAME.action_replace(payload.slot))


@app.post("/api/action/call-wellington")
def action_call_wellington():
    return safe_action(GAME.action_call_wellington)


# Backward-compatible alias (legacy typo route)
@app.post("/api/action/call-welligton")
def action_call_welligton_legacy():
    return safe_action(GAME.action_call_wellington)


@app.post("/api/action/pass-wellington-window")
def action_pass_wellington_window():
    return safe_action(GAME.action_pass_human_wellington_window)


# Backward-compatible alias (legacy typo route)
@app.post("/api/action/pass-welligton-window")
def action_pass_welligton_window_legacy():
    return safe_action(GAME.action_pass_human_wellington_window)


@app.post("/api/action/ability")
def action_ability(payload: AbilityPayload):
    return safe_action(lambda: GAME.action_use_ability(payload.data))


@app.post("/api/action/cut-self")
def action_cut_self(payload: CutSelfPayload):
    return safe_action(lambda: GAME.action_cut_self(payload.slot))


@app.post("/api/action/cut-other")
def action_cut_other(payload: CutOtherPayload):
    return safe_action(
        lambda: GAME.action_cut_other(
            target_player=payload.target_player,
            target_slot=payload.target_slot,
            give_slot=payload.give_slot,
        )
    )


@app.post("/api/action/skip-cut")
def action_skip_cut():
    return safe_action(GAME.action_skip_cut)


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR)), name="assets")


@app.get("/")
def root():
    return FileResponse(FRONTEND_DIR / "index.html")
