import os
import io
import requests
import chess
import chess.pgn
import chess.engine
import subprocess
import json
import re

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# =========================
# Environment variables
# =========================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
#APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY")  # optional
MAX_GAMES = int(os.environ.get("MAX_GAMES_ANALYZED", 10))
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")

# Stockfish binary (downloaded by setup script)
STOCKFISH_PATH = os.path.join(os.getcwd(), "stockfish")

def curl_get(url, timeout=10):
    """GET request via curl, returns raw text"""
    result = subprocess.run(
        [
            "curl",
            "-s",
            "--fail",
            "--max-time", str(timeout),
            "-H", "Accept: application/json",
            url,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout

# =========================
# FastAPI app
# =========================

app = FastAPI(title="Chess Analyzer")

templates = Jinja2Templates(directory="templates")

# =========================
# Utility: simple API key protection
# =========================

#def check_api_key(request: Request):
#    if APP_SECRET_KEY:
#        if request.headers.get("X-API-Key") != APP_SECRET_KEY:
#            raise HTTPException(status_code=401, detail="Unauthorized")

# =========================
# Frontend
# =========================

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# =========================
# Chess.com API
# =========================

@app.get("/api/games/{username}")
def get_last_games(username: str, request: Request):
    #check_api_key(request)

    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"

    
    # try:
    #     archives_resp = requests.get(archives_url, timeout=10, verify="/etc/ssl/certs/ca-certificates.crt")
    # except requests.RequestException as exc:
    #     # External service error / network problem
    #     raise HTTPException(status_code=502, detail="Upstream service unreachable") from exc

    # if archives_resp.status_code == 404:
    #     raise HTTPException(status_code=404, detail="User not found")
    # if archives_resp.status_code != 200:
    #     # Unexpected upstream status
    #     raise HTTPException(status_code=502, detail="Upstream service error")

    data = json.loads(curl_get(archives_url))
    archives = data.get("archives", [])
    
    #archives = archives_resp.json().get("archives", [])
    if not archives:
        return []

    games = []
    for archive_url in reversed(archives):
        data = json.loads(curl_get(archive_url))
        month_games = data.get("games", [])
        #month_games = requests.get(archive_url, timeout=10, ).json().get("games", [])
        for g in reversed(month_games):
            games.append({
                "white": g["white"]["username"],
                "black": g["black"]["username"],
                "result": (
                    g["white"]["result"]
                    if g["white"]["username"].lower() == username.lower()
                    else g["black"]["result"]
                ),
                "url": g.get("url"),
                "pgn": g.get("pgn"),
                "time_control": g.get("time_control"),
                "end_time": g.get("end_time"),
            })
            if len(games) >= MAX_GAMES:
                return games

    return games

# =========================
# LLM analysis (OpenAI)
# =========================

def run_llm_analysis(analysis_data: dict) -> dict:
    import openai

    openai.api_key = OPENAI_API_KEY

    prompt = f"""
You are a chess coach.

Analyze the following chess game evaluation and provide a clear, human explanation
for each phase of the game:
- Opening
- Middlegame
- Endgame

Focus on ideas, plans, and common mistakes.
Avoid long tactical variations.

Game evaluation data:
{analysis_data}
"""

    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    text = response.choices[0].message.content

    return {
        "opening": extract_section(text, "Opening"),
        "middlegame": extract_section(text, "Middlegame"),
        "endgame": extract_section(text, "Endgame"),
    }

def extract_section(text: str, title: str) -> str:
    for block in text.split("\n\n"):
        if title.lower() in block.lower():
            return block.strip()
    return text.strip()

# =========================
# Game analysis endpoint
# =========================

@app.post("/api/analyze")
def analyze_game(payload: dict, request: Request):
    #check_api_key(request)

    pgn_text = payload.get("pgn")
    if not pgn_text:
        raise HTTPException(status_code=400, detail="PGN missing")

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    board = game.board()

    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

    evaluations = []
    move_count = 0

    try:
        for move in game.mainline_moves():
            board.push(move)
            move_count += 1

            info = engine.analyse(
                board,
                chess.engine.Limit(depth=12, time=0.5)
            )

            score = info["score"].white().score(mate_score=10000)
            evaluations.append({
                "move_number": move_count,
                "san": board.san(move),
                "evaluation": score
            })

    finally:
        engine.quit()

    # Split into phases (simple & robust)
    total = len(evaluations)
    opening = evaluations[: total // 3]
    middlegame = evaluations[total // 3 : 2 * total // 3]
    endgame = evaluations[2 * total // 3 :]

    analysis_data = {
        "opening": opening,
        "middlegame": middlegame,
        "endgame": endgame,
    }

    llm_text = run_llm_analysis(analysis_data)

    return {
        "phases": analysis_data,
        "analysis": llm_text
    }

# =========================
# Health check (Render)
# =========================

@app.get("/health")
def health():
    return {"status": "ok"}
