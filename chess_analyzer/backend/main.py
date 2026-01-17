from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import chess.pgn
import chess.engine
import io
import os

app = FastAPI()

# Serve static files & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Path to Stockfish binary
STOCKFISH_PATH = "./stockfish"

# LLM placeholder (replace with OpenAI or any LLM API)
def llm_analysis(summary_json):
    # For simplicity, just return a dummy analysis
    return {
        "opening": "Opening phase analysis: You played solidly.",
        "middlegame": "Middlegame: You missed some tactical opportunities.",
        "endgame": "Endgame: You converted your advantage cleanly."
    }

# Serve frontend
@app.get("/", response_class=HTMLResponse)
def get_frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Fetch last 10 games from Chess.com
@app.get("/api/games/{username}")
def get_last_10_games(username: str):
    url = f"https://api.chess.com/pub/player/{username}/games/archives"
    archives = requests.get(url).json().get("archives", [])
    if not archives:
        return JSONResponse({"error": "No games found"}, status_code=404)

    # Take last month archive first
    latest_archive = archives[-1]
    games_resp = requests.get(latest_archive).json()
    games = games_resp.get("games", [])[-10:]  # last 10 games

    result_list = []
    for g in games:
        game_data = {
            "white": g["white"]["username"],
            "black": g["black"]["username"],
            "result": g["white"]["result"] if g["white"]["username"].lower() == username.lower() else g["black"]["result"],
            "url": g.get("url"),
            "pgn": g.get("pgn")
        }
        result_list.append(game_data)
    return result_list

# Analyze a game with Stockfish + LLM
@app.post("/api/analyze")
def analyze_game(payload: dict):
    pgn_text = payload.get("pgn")
    if not pgn_text:
        return JSONResponse({"error": "No PGN provided"}, status_code=400)

    # Parse PGN
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    board = game.board()

    # Initialize engine
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    evaluations = []

    for i, move in enumerate(game.mainline_moves()):
        board.push(move)
        info = engine.analyse(board, chess.engine.Limit(depth=12))
        score = info["score"].white().score(mate_score=10000)
        evaluations.append({"move": board.san(move), "eval": score})

    engine.quit()

    # Split phases roughly
    total_moves = len(evaluations)
    opening = evaluations[:total_moves//3]
    middlegame = evaluations[total_moves//3: 2*total_moves//3]
    endgame = evaluations[2*total_moves//3:]

    analysis_json = {
        "opening": opening,
        "middlegame": middlegame,
        "endgame": endgame
    }

    # Call LLM for textual explanation
    textual_analysis = llm_analysis(analysis_json)

    return {
        "evaluation": analysis_json,
        "textual_analysis": textual_analysis
    }
