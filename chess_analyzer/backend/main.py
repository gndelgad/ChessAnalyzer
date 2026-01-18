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
def run_llm_analysis(all_games_eval: list) -> dict:
    """
    Receives a list of game evaluations (opening/middlegame/endgame)
    and returns a global summary in structured JSON.
    """
    import openai
    import json

    openai.api_key = OPENAI_API_KEY

    analysis_data_json = json.dumps(all_games_eval, indent=2)

    prompt = f"""
You are a chess coach.

Analyze the following chess game evaluations (multiple games) and provide a **global summary**
and **recommendations to improve**
from the perspective of the user whose games are provided.
Return the result in **strict JSON format** exactly like this (no extra brackets or markdown):

{{
  "openings": "...summary of common opening ideas/mistakes/improvements...",
  "middlegame": "...summary of middlegame ideas/mistakes/improvements...",
  "endgame": "...summary of endgame ideas/mistakes/improvements..."
}}

Do not include markdown code blocks, explanations, or backticks.
Focus on patterns, common mistakes, and plans across all games to highlight improvement axist.
Be concrete with your recommendations. For example improve pawn structure, activate your towers or castle sooner, occupy the center, avoid typical
opening traps, etc.

Game evaluation data:
{analysis_data_json}
"""

    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    text = response.choices[0].message.content

    # Try parsing JSON; fallback to raw text if parsing fails
    try:
        print(text)
        return json.loads(text)
    # try:
    #     ans = json.loads(text)
    #     if isinstance(ans, str):
    #         return json.loads(ans)    
    #     return ans
    except json.JSONDecodeError:
        return {
            "openings": text,
            "middlegame": text,
            "endgame": text
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
# Analyze all games at once
# =========================
@app.post("/api/analyze-all")
def analyze_all_games(payload: dict, request: Request):
    """
    Analyze all games for a given user in one request.
    Evaluations are normalized relative to the username.
    Returns per-game evaluations + global LLM analysis.
    """
    #check_api_key(request)

    username = payload.get("username")
    pgns = payload.get("pgns")

    if not username:
        raise HTTPException(status_code=400, detail="Username missing")
    if not pgns or not isinstance(pgns, list):
        raise HTTPException(status_code=400, detail="PGNs missing or invalid")

    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    all_evaluations = []

    try:
        for g_idx, pgn_text in enumerate(pgns):
            if not pgn_text:
                continue

            game = chess.pgn.read_game(io.StringIO(pgn_text))
            if game is None:
                continue

            board = game.board()
            evaluations = []

            # Determine user color for this game
            user_color = "white" if game.headers.get("White", "").lower() == username.lower() else "black"

            # Collect legal moves
            moves = [move for move in game.mainline_moves() if move is not None]
            total_moves = len(moves)

            # Sample indices for each phase
            def sample_indices(n_samples, start, end):
                if end - start <= n_samples:
                    return list(range(start, end))
                step = max(1, (end - start) // n_samples)
                return list(range(start, end, step))

            opening_idx = sample_indices(3, 0, total_moves // 3)
            middlegame_idx = sample_indices(4, total_moves // 3, 2 * total_moves // 3)
            endgame_idx = sample_indices(3, 2 * total_moves // 3, total_moves)
            sample_set = set(opening_idx + middlegame_idx + endgame_idx)

            # Iterate moves
            for i, move in enumerate(moves):
                if move not in board.legal_moves:
                    board.push(move)
                    continue

                try:
                    san = board.san(move)
                except AssertionError:
                    board.push(move)
                    continue

                board.push(move)

                if i not in sample_set:
                    continue  # only analyze selected moves

                try:
                    info = engine.analyse(
                        board,
                        chess.engine.Limit(depth=6, time=0.03)
                    )
                    score = info["score"].white().score(mate_score=10000)
                except chess.engine.EngineError:
                    continue

                # Normalize score relative to user
                if score is not None and user_color == "black":
                    score = -score

                evaluations.append({
                    "move_number": i + 1,
                    "san": san,
                    "evaluation": score
                })

            # Split into phases
            total_eval = len(evaluations)
            opening = evaluations[: total_eval // 3]
            middlegame = evaluations[total_eval // 3 : 2 * total_eval // 3]
            endgame = evaluations[2 * total_eval // 3 :]

            all_evaluations.append({
                "opening": opening,
                "middlegame": middlegame,
                "endgame": endgame
            })

    finally:
        engine.quit()

    # Generate global LLM analysis
    llm_text = run_llm_analysis(all_evaluations)

    return {
        "phases": all_evaluations,
        "textual_analysis": llm_text
    }

# =========================
# Health check (Render)
# =========================

@app.get("/health")
def health():
    return {"status": "ok"}
