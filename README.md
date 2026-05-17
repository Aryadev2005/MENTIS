# MENTIS — Your Unfair Advantage

India's most advanced real-time AI career intelligence platform.

**Brand:** #6C3AFF (violet) · #00D4AA (teal)

---

## Quick Start

```bash
# 1. Clone and enter directory
cd mentis

# 2. Copy and fill environment variables
cp .env.example .env
# Edit .env with your API keys

# 3. Start databases
docker compose up -d

# 4. Set up databases and seed data
chmod +x scripts/setup_db.sh
./scripts/setup_db.sh

# 5. Install Node dependencies
npm install

# 6. Install Python dependencies
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 7. Start development
npm run dev          # Electron + React
uvicorn api.main:app --reload  # FastAPI (separate terminal)
```

## Architecture

```
MENTIS/
├── electron/          # Desktop app (main process)
├── renderer/          # React UI (view layer)
├── api/               # FastAPI backend (MVC)
│   ├── controllers/   # Business logic
│   ├── models/        # DB models + Pydantic schemas
│   ├── routers/       # HTTP routes
│   ├── agents/        # LangGraph AI agents
│   ├── services/      # Claude, Deepgram, OpenAI
│   └── views/         # Response serializers
└── scripts/           # DB setup + seeding
```

## Global Hotkeys

| Hotkey | Action |
|--------|--------|
| `⌘/Ctrl + Shift + H` | Toggle overlay |
| `⌘/Ctrl + Shift + S` | OA screenshot capture |
| `⌘/Ctrl + Shift + C` | Copy current answer |
| `⌘/Ctrl + Shift + M` | Show/hide main window |

## AI Models Used

- **Claude Sonnet 4** — Primary interview answers (streaming)
- **Claude Haiku** — Question detection, confidence scoring, fast tasks
- **GPT-4o Vision** — OA screenshot parsing
- **Deepgram Nova-3** — Real-time audio transcription
- **text-embedding-3-large** — Question/answer embeddings

## Latency Targets

| Stage | Target |
|-------|--------|
| Audio → transcript | < 300ms |
| Question detection | < 100ms |
| Context retrieval | < 150ms |
| First streaming token | < 500ms |
| Full answer | < 2000ms |

---

*MENTIS. Your Unfair Advantage.*
