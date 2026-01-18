# ChessAnalyzer

## ✨ Features

* Analyze historical Chess.com games
* Engine-based evaluation using **Stockfish**
* LLM-powered insights and coaching feedback
* Phase-specific recommendations:

  * Opening
  * Middlegame
  * Endgame
* Deployed and run on **Render**
* Configurable number of games to analyze

---

## 🧠 How It Works

1. Past games are retrieved from Chess.com.
2. Each game is analyzed move-by-move using the Stockfish engine.
3. Key moments, inaccuracies, and patterns are extracted.
4. An LLM processes the engine evaluations to generate:

   * Clear explanations
   * Actionable improvement tips
   * Strategic lessons per game phase

---

## ⚙️ Configuration

### Environment Variables

| Variable             | Description                                  | Default      |
| -------------------- | -------------------------------------------- | ------------ |
| `MAX_GAMES_ANALYZED` | Maximum number of games analyzed per request | `10`         |
| `OPENAI_API_KEY`     | API key for OpenAI                           | `***`        |
| `OPENAI_MODEL`       | OpenAI model used for analysis               | `gpt-5-mini` |

> ⚠️ `OPENAI_API_KEY` **must** be set with a valid key for the application to function correctly.

---

## 🚀 Running the Application

This application is designed to run on **Render**, which automatically manages the `PORT` environment variable.

### Build Command

```bash
chess_analyze/backend pip install -r requirements.txt && bash ../scripts/setup_stockfish.sh
```

### Start Command

```bash
chess_analyze/backend uvicorn main:app --host 0.0.0.0 --port $PORT
```

This launches the FastAPI backend using Uvicorn.

---

## 🛠 Tech Stack

* **Python**
* **FastAPI**
* **Uvicorn**
* **Stockfish**
* **OpenAI API**
* **Render** (deployment)

---

## 📁 Project Structure (Simplified)

```
chess_analyzer/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── ...
├── scripts/
│   └── setup_stockfish.sh
└── README.md
```

---

## 📄 License

This project is provided as-is for educational and personal improvement purposes.

---
