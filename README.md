# Tone Shift — Context-Aware Translation Web App

A full-stack web application for multilingual translation and text refinement, powered by Google Gemini AI. Unlike generic translation tools, Tone Shift supports **contextual prompt injection** — allowing users to specify the situational context (e.g. "formal business email", "casual gaming chat") to produce translations that are genuinely context-aware.

Built with **FastAPI** (Python) on the backend and **vanilla JavaScript** on the frontend, communicating via a clean **REST API**.

---

## Features

| Feature | Description |
|---------|-------------|
| **Context-Aware Translation** | Optional context hints (e.g. "legal contract", "restaurant conversation") are injected into AI prompts for situationally accurate translations |
| **Multi-Mode Processing** | Translate between languages, refine text style, or get grammar explanations — all through one unified API endpoint |
| **7+ Translation Styles** | Normal, Literal, Literary, Poetic, Motivational, Satirical, Gen Z |
| **8+ Refinement Tones** | Professional, Casual, Scientific, Creative, Poetic, Motivational, Old English, Gen Z |
| **Grammar Explanation** | After translating, get a friendly AI-generated breakdown of why specific words/grammar were chosen |
| **Local History** | Recent translations are saved to localStorage for quick re-access |
| **Dark Theme UI** | Polished, modern dark interface with smooth animations |
| **Auto-Generated API Docs** | FastAPI's Swagger UI at `/docs` provides interactive, self-documenting API reference |

---

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐         ┌──────────────┐
│     Frontend         │  fetch │     FastAPI          │  HTTP   │  Google      │
│  (HTML/CSS/JS)       │───────→│  Backend             │───────→ │  Gemini API  │
│                      │  JSON  │                      │         │              │
│  • User input        │←───────│  • Prompt builder    │←─────── │  • AI model  │
│  • Mode selection    │  JSON  │  • Request validation│  text   │              │
│  • Context hint      │        │  • Error handling    │         │              │
│  • History (local)   │        │  • CORS middleware   │         │              │
└─────────────────────┘         └──────────────────────┘         └──────────────┘
```

### Request Lifecycle

1. **User** enters text, selects mode/tone, and optionally provides a context hint
2. **Frontend** sends a structured JSON payload via `fetch()` to the backend
3. **FastAPI** validates the request, constructs the full AI prompt server-side
4. **Gemini API** processes the prompt and returns generated text
5. **Backend** validates the response and returns clean JSON to the frontend
6. **Frontend** displays the result with options to copy or request grammar explanation

> **Key design decision:** All prompt engineering happens server-side. The frontend sends structured data (not prompt strings), maintaining a clean separation of concerns.

---

## Project Structure

```
context-aware-translation-app/
│
├── backend/
│   ├── main.py              # FastAPI app, prompt engine, API endpoint
│   ├── requirements.txt     # Python dependencies (pinned versions)
│   ├── .env.example          # Template for environment variables
│   └── .env                  # Your actual API key (git-ignored)
│
├── frontend/
│   ├── index.html           # Main UI layout
│   ├── app.js               # Client logic, API calls, history
│   ├── style.css            # Dark-theme design system
│   └── favicon.png          # App icon
│
├── scripts/
│   └── check_models.py      # Utility: list available Gemini models
│
├── screenshots/              # App screenshots for documentation
├── README.md
└── .gitignore
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- A [Google Gemini API key](https://aistudio.google.com/apikey)

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/context-aware-translation-app.git
cd context-aware-translation-app
```

### 2. Set Up the Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and add your actual GEMINI_API_KEY
```

### 3. Start the Backend Server

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Visit `http://localhost:8000/docs` for interactive API documentation.

### 4. Open the Frontend

Open `frontend/index.html` directly in your browser, or serve it with any static file server:

```bash
# Option A: Open directly
open frontend/index.html         # macOS
xdg-open frontend/index.html    # Linux

# Option B: Use Python's built-in server
cd frontend
python -m http.server 5500
# Then visit http://localhost:5500
```

---

## Security

- **API keys** are loaded from environment variables via `.env` (never hardcoded)
- **`.env` is git-ignored** — secrets are never committed to version control
- **`.env.example`** documents required variables without exposing real values
- **CORS** is configured for development; in production, restrict `allow_origins` to your domain

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | FastAPI | Async REST API framework with auto-generated docs |
| AI Model | Google Gemini | Generative AI for translation and text processing |
| Frontend | Vanilla JS | Client-side logic, no framework dependencies |
| Styling | CSS3 | Custom dark-theme design system |
| Data | Pydantic | Request/response validation and serialization |

---

## API Reference

### `POST /process_text`

Process text based on the specified mode.

**Request Body:**

```json
{
  "source_text": "Hello, how are you?",
  "mode": "translate",
  "source_lang": "auto",
  "target_lang": "Urdu",
  "tone": "Normal",
  "translated_text": null,
  "context_hint": "casual conversation with a friend"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_text` | string | Yes | Text to process (1–5000 chars) |
| `mode` | string | Yes | `translate`, `refine`, or `explain` |
| `source_lang` | string | No | Source language (default: `auto`) |
| `target_lang` | string | No | Target language for translation |
| `tone` | string | No | Style/tone (default: `Normal`) |
| `translated_text` | string | No | Required for `explain` mode |
| `context_hint` | string | No | Situational context for context-aware processing |

**Response:**

```json
{
  "result": "ہیلو، آپ کیسے ہیں؟"
}
```

### `GET /health`

Returns API health status.

---

## Future Improvements

- [ ] User authentication and cloud-saved history
- [ ] Response caching for repeated translations
- [ ] Database-backed translation history
- [ ] Docker containerization for one-command deployment
- [ ] Rate limiting and API usage tracking
- [ ] Additional AI model support (OpenAI, Claude)

---

## License

This project is for academic and portfolio purposes.
