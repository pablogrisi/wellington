import secrets
import threading
import json
import logging
import os
import sqlite3
from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib import error as urlerror
from urllib import request as urlrequest
import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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

SESSION_COOKIE_NAME = "wellington_sid"
ADMIN_COOKIE_NAME = "wellington_admin"
UNDO_LIMIT = 60
SESSIONS_LOCK = threading.Lock()
ADMIN_SESSIONS_LOCK = threading.Lock()
PLAYER_NAME_RE = re.compile(r"^[A-Za-z0-9_ .-]{3,24}$")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
ADMIN_LOGS_PASSWORD = os.getenv("ADMIN_LOGS_PASSWORD", "logsjogo")
ACTIVITY_DB_PATH = Path(__file__).resolve().parents[1] / "player_activity.db"
logger = logging.getLogger("wellington")


class SessionState:
    def __init__(self) -> None:
        self.game = WellingtonGame()
        self.game.new_game()
        self.undo_stack: deque[Dict[str, Any]] = deque(maxlen=UNDO_LIMIT)
        self.lock = threading.Lock()
        self.player_name: Optional[str] = None
        self.player_started_at: Optional[str] = None


SESSIONS: Dict[str, SessionState] = {}
ADMIN_TOKENS: set[str] = set()


def _init_activity_db() -> None:
    with sqlite3.connect(ACTIVITY_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS game_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_time TEXT NOT NULL,
                user_agent TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_game_events_player_time
            ON game_events(player_name, event_time)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_game_events_type
            ON game_events(event_type)
            """
        )
        conn.commit()


def record_local_event(
    session_id: str,
    player_name: str,
    event_type: str,
    event_time: Optional[str] = None,
    user_agent: str = "",
) -> None:
    if event_time is None:
        event_time = datetime.now(timezone.utc).isoformat()

    _init_activity_db()
    with sqlite3.connect(ACTIVITY_DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO game_events(session_id, player_name, event_type, event_time, user_agent)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, player_name, event_type, event_time, user_agent[:240]),
        )
        conn.commit()


def is_admin_authenticated(request: Request) -> bool:
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    if not token:
        return False
    with ADMIN_SESSIONS_LOCK:
        return token in ADMIN_TOKENS


def require_admin(request: Request) -> None:
    if not is_admin_authenticated(request):
        raise HTTPException(status_code=401, detail="Acesso negado.")


def get_or_create_session(session_id: Optional[str]) -> tuple[str, SessionState, bool]:
    with SESSIONS_LOCK:
        if session_id and session_id in SESSIONS:
            return session_id, SESSIONS[session_id], False

        new_session_id = secrets.token_urlsafe(24)
        session_state = SessionState()
        SESSIONS[new_session_id] = session_state
        return new_session_id, session_state, True


@app.middleware("http")
async def ensure_session(request: Request, call_next):
    incoming_session_id = request.cookies.get(SESSION_COOKIE_NAME)
    session_id, session_state, is_new = get_or_create_session(incoming_session_id)

    request.state.session_id = session_id
    request.state.session_state = session_state

    response = await call_next(request)
    if is_new or incoming_session_id != session_id:
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 30,
        )
    return response


def current_session(request: Request) -> SessionState:
    return request.state.session_state


def build_public_state(session: SessionState) -> Dict[str, Any]:
    payload = session.game.public_state()
    payload["can_undo"] = len(session.undo_stack) > 0
    payload["player_name"] = session.player_name
    payload["player_ready"] = session.player_name is not None
    if session.player_name is None:
        payload["can_bot_step"] = False
        payload["actions"] = {
            "can_draw": False,
            "can_discard_drawn": False,
            "replace_slots": [],
            "can_call_wellington": False,
            "can_cut": False,
            "can_send_cut_other_card": False,
            "send_cut_other_slots": [],
        }
    return payload


def safe_action(
    session: SessionState,
    fn: Callable[[], Any],
    allow_when_paused: bool = False,
    record_undo: bool = True,
):
    with session.lock:
        try:
            if session.player_name is None:
                raise ValueError("Informe seu nome para iniciar a partida.")
            if session.game.paused and not allow_when_paused:
                raise ValueError("A partida esta pausada. Clique em Retomar para continuar.")
            before_state = deepcopy(session.game.to_state_dict()) if record_undo else None
            fn()
            if record_undo and before_state is not None:
                session.undo_stack.append(before_state)
            return build_public_state(session)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception(f"Erro interno no servidor: {exc}")
            raise HTTPException(status_code=500, detail=f"Erro interno no servidor: {exc}") from exc


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


class PlayerStartPayload(BaseModel):
    name: str


class AdminLoginPayload(BaseModel):
    password: str


def normalize_player_name(raw_name: str) -> str:
    name = " ".join(raw_name.strip().split())
    if not PLAYER_NAME_RE.fullmatch(name):
        raise ValueError("Nome invalido. Use 3-24 chars (letras, numeros, espaco, _, -, .).")
    return name


def persist_player_start_event(
    session_id: str,
    player_name: str,
    started_at: str,
    user_agent: str,
) -> None:
    record_local_event(
        session_id=session_id,
        player_name=player_name,
        event_type="player_start",
        event_time=started_at,
        user_agent=user_agent,
    )

    logger.info(
        "event=player_start session_id=%s player_name=%s started_at=%s",
        session_id,
        player_name,
        started_at,
    )
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return

    payload = {
        "session_id": session_id,
        "player_name": player_name,
        "started_at": started_at,
        "user_agent": user_agent[:240],
    }
    req = urlrequest.Request(
        f"{SUPABASE_URL}/rest/v1/player_sessions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=4):
            pass
    except (urlerror.URLError, TimeoutError) as exc:
        logger.warning("event=player_start_persist_failed reason=%s", exc)


@app.get("/api/state")
def get_state(request: Request):
    session = current_session(request)
    return build_public_state(session)


@app.post("/api/player/start")
def player_start(payload: PlayerStartPayload, request: Request):
    session = current_session(request)
    session_id = request.state.session_id
    with session.lock:
        if session.player_name is not None:
            raise HTTPException(status_code=400, detail="Nome do jogador ja foi definido nesta sessao.")
        normalized_name = normalize_player_name(payload.name)
        session.game.new_game()
        session.player_name = normalized_name
        session.player_started_at = datetime.now(timezone.utc).isoformat()
        session.game.players[0].name = normalized_name
        session.undo_stack.clear()
        persist_player_start_event(
            session_id=session_id,
            player_name=normalized_name,
            started_at=session.player_started_at,
            user_agent=request.headers.get("user-agent", ""),
        )
        record_local_event(
            session_id=session_id,
            player_name=normalized_name,
            event_type="new_game",
            user_agent=request.headers.get("user-agent", ""),
        )
        return build_public_state(session)


@app.post("/api/new-game")
def new_game(request: Request):
    session = current_session(request)
    with session.lock:
        session.undo_stack.clear()
        session.game.new_game()
        if session.player_name:
            session.game.players[0].name = session.player_name
            logger.info(
                "event=new_game session_id=%s player_name=%s",
                request.state.session_id,
                session.player_name,
            )
            record_local_event(
                session_id=request.state.session_id,
                player_name=session.player_name,
                event_type="new_game",
                user_agent=request.headers.get("user-agent", ""),
            )
        return build_public_state(session)


@app.post("/api/bot-step")
def bot_step(request: Request):
    session = current_session(request)
    return safe_action(session, session.game.bot_step)


@app.post("/api/pause")
def pause_game(request: Request):
    session = current_session(request)
    return safe_action(session, session.game.action_pause, allow_when_paused=True)


@app.post("/api/resume")
def resume_game(request: Request):
    session = current_session(request)
    return safe_action(session, session.game.action_resume, allow_when_paused=True)


@app.post("/api/action/draw")
def action_draw(request: Request):
    session = current_session(request)
    return safe_action(session, session.game.action_draw)


@app.post("/api/action/discard-drawn")
def action_discard_drawn(request: Request):
    session = current_session(request)
    return safe_action(session, session.game.action_discard_drawn)


@app.post("/api/action/replace")
def action_replace(payload: ReplacePayload, request: Request):
    session = current_session(request)
    return safe_action(session, lambda: session.game.action_replace(payload.slot))


@app.post("/api/action/call-wellington")
def action_call_wellington(request: Request):
    session = current_session(request)
    return safe_action(session, session.game.action_call_wellington)


# Backward-compatible alias (legacy typo route)
@app.post("/api/action/call-welligton")
def action_call_welligton_legacy(request: Request):
    session = current_session(request)
    return safe_action(session, session.game.action_call_wellington)


@app.post("/api/action/pass-wellington-window")
def action_pass_wellington_window(request: Request):
    session = current_session(request)
    return safe_action(session, session.game.action_pass_human_wellington_window)


# Backward-compatible alias (legacy typo route)
@app.post("/api/action/pass-welligton-window")
def action_pass_welligton_window_legacy(request: Request):
    session = current_session(request)
    return safe_action(session, session.game.action_pass_human_wellington_window)


@app.post("/api/action/ability")
def action_ability(payload: AbilityPayload, request: Request):
    session = current_session(request)
    return safe_action(session, lambda: session.game.action_use_ability(payload.data))


@app.post("/api/action/cut-self")
def action_cut_self(payload: CutSelfPayload, request: Request):
    session = current_session(request)
    return safe_action(session, lambda: session.game.action_cut_self(payload.slot))


@app.post("/api/action/cut-other")
def action_cut_other(payload: CutOtherPayload, request: Request):
    session = current_session(request)
    return safe_action(
        session,
        lambda: session.game.action_cut_other(
            target_player=payload.target_player,
            target_slot=payload.target_slot,
            give_slot=payload.give_slot,
        ),
    )


@app.post("/api/action/skip-cut")
def action_skip_cut(request: Request):
    session = current_session(request)
    return safe_action(session, session.game.action_skip_cut)


@app.post("/api/action/undo")
def action_undo(request: Request):
    session = current_session(request)
    with session.lock:
        if not session.undo_stack:
            raise HTTPException(status_code=400, detail="Nao ha acao para desfazer.")
        snapshot = session.undo_stack.pop()
        session.game.load_state_dict(snapshot)
        return build_public_state(session)


@app.post("/api/admin/login")
def admin_login(payload: AdminLoginPayload):
    if payload.password != ADMIN_LOGS_PASSWORD:
        raise HTTPException(status_code=401, detail="Senha incorreta.")

    token = secrets.token_urlsafe(24)
    with ADMIN_SESSIONS_LOCK:
        ADMIN_TOKENS.add(token)

    response = JSONResponse(content={"ok": True})
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
    )
    return response


@app.post("/api/admin/logout")
def admin_logout(request: Request):
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    if token:
        with ADMIN_SESSIONS_LOCK:
            ADMIN_TOKENS.discard(token)
    response = JSONResponse(content={"ok": True})
    response.delete_cookie(ADMIN_COOKIE_NAME)
    return response


@app.get("/api/admin/logs")
def admin_logs_api(request: Request):
    require_admin(request)
    _init_activity_db()
    with sqlite3.connect(ACTIVITY_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        summary_rows = conn.execute(
            """
            SELECT
                player_name,
                MIN(event_time) AS first_played_at,
                MAX(event_time) AS last_activity_at,
                SUM(CASE WHEN event_type = 'new_game' THEN 1 ELSE 0 END) AS matches_played,
                COUNT(DISTINCT session_id) AS sessions
            FROM game_events
            GROUP BY player_name
            ORDER BY last_activity_at DESC
            """
        ).fetchall()
        recent_rows = conn.execute(
            """
            SELECT session_id, player_name, event_type, event_time
            FROM game_events
            ORDER BY event_time DESC
            LIMIT 100
            """
        ).fetchall()

    return {
        "players": [dict(row) for row in summary_rows],
        "recent_events": [dict(row) for row in recent_rows],
    }


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets"), html=False), name="assets")


@app.get("/admin")
def admin_root():
    return FileResponse(FRONTEND_DIR / "admin-login.html")


@app.get("/admin/logs")
def admin_logs_page(request: Request):
    require_admin(request)
    return FileResponse(FRONTEND_DIR / "admin-logs.html")


@app.get("/assets/cards/{filename}")
async def get_card_image(filename: str):
    """Serve card images from assets/cards directory."""
    card_path = FRONTEND_DIR / "assets" / "cards" / filename
    if card_path.exists():
        return FileResponse(card_path)
    return {"error": "File not found"}


@app.get("/")
def root():
    return FileResponse(FRONTEND_DIR / "index.html")
