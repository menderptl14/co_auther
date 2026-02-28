# Co-Author — Interactive AI Writing Editor

> A production-quality AI-powered document editor with deep contextual integration between the editor and assistant. Built with Flask + Google Gemini + Quill.js.

![Co-Author Preview](https://placehold.co/1200x600/1a1814/faf9f6?text=Co-Author+AI+Writing+Editor)

---

## ✨ Features

- **Dual-pane interface**: Rich text editor (left) + AI chat assistant (right)
- **Context-aware AI**: The assistant reads your full document and can reference any paragraph
- **Selection toolbar**: Select any text → instant Summarize / Fix Grammar / Rewrite / Expand / Shorten / Change Tone
- **AI apply button**: Preview suggested edits, click one button to apply directly to the editor
- **Streaming responses**: Real-time token-by-token AI output
- **Tone analysis**: Full linguistic analysis of your document
- **Version history**: Automatic snapshots before every AI edit
- **Document stats**: Word count, reading time, sentence count
- **Export**: Markdown or plain text download
- **Dark mode**: Full dark theme toggle
- **Keyboard shortcuts**: `Ctrl+Enter` to send, `Escape` to close modals
- **Metrics logging**: SQLite database tracking all AI requests

---

## 🗂 Project Structure

```
co-author/
├── app.py              # Flask backend (single entry point)
├── requirements.txt    # Python dependencies
├── Procfile            # Deployment config (Render/Railway)
├── .env.example        # Environment variables template
├── README.md
├── data/
│   └── metrics.db      # Auto-created SQLite metrics database
└── templates/
    └── index.html      # Full frontend (HTML + Tailwind CDN + JS)
```

---

## 🚀 Local Setup (5 minutes)

### 1. Clone / Download

```bash
git clone <your-repo>
cd co-author
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

Get a free Gemini API key at: https://aistudio.google.com/app/apikey

### 5. Run the server

```bash
python app.py
```

Open http://localhost:5000 — you're live! 🎉

---

## 🌐 Deployment

### Deploy to Render (Recommended — Free tier)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Environment**: Python 3.11
5. Add environment variable: `GEMINI_API_KEY=your_key`
6. Click Deploy

### Deploy to Railway

1. Install Railway CLI: `npm install -g @railway/cli`
2. `railway login`
3. `railway init` in project folder
4. `railway variables set GEMINI_API_KEY=your_key`
5. `railway up`

### Deploy to Fly.io

```bash
fly launch
fly secrets set GEMINI_API_KEY=your_key
fly deploy
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main editor UI |
| `/chat` | POST | Standard chat (non-streaming) |
| `/chat/stream` | POST | Streaming chat (SSE) |
| `/improve` | POST | Improve selected text |
| `/analyze` | POST | Document tone + stats analysis |
| `/export` | POST | Export as markdown or txt |
| `/metrics` | GET | Usage metrics dashboard data |
| `/health` | GET | Health check |

### Example: `/improve` request

```json
POST /improve
{
  "text": "The cat go to the store yesterday.",
  "action": "grammar"
}
```

Available actions: `grammar`, `summarize`, `rewrite_professional`, `expand`, `shorten`, `tone_formal`, `tone_casual`, `tone_persuasive`, `tone_analysis`

### Example: `/chat/stream` request

```json
POST /chat/stream
{
  "message": "What is the tone of the second paragraph?",
  "document_content": "Full document text here..."
}
```

---

## 📊 Metrics

All AI requests are logged to `data/metrics.db`. Access aggregated stats at:

```
GET /metrics
```

Returns: total requests, average response time, breakdown by action type, recent requests.

---

## 🏗 Architecture Decisions

### Why Flask (not FastAPI)?
Simple, battle-tested, minimal boilerplate. For an MVP/demo, Flask's synchronous model is fine. The streaming endpoint uses `Response(stream_with_context(...))` for SSE.

### Why Gemini Flash?
Gemini 1.5 Flash offers the best speed/quality balance for real-time writing assistance. The streaming API enables token-by-token output for a ChatGPT-like feel.

### Why single-file backend?
`app.py` contains everything: routes, prompt templates, DB logic. This makes it trivially easy to deploy anywhere and understand at a glance. Production would split this into modules.

### Why Quill.js (not Tiptap)?
Quill has zero build dependencies and works via CDN. For a demo/prototype, this means zero webpack configuration. Tiptap is better for production but requires Node.js tooling.

### Why SQLite (not JSON files)?
SQLite is serverless, zero-config, and handles concurrent writes gracefully. Perfect for metrics that don't need a full Postgres instance.

---

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | — | Google AI Studio API key |
| `FLASK_DEBUG` | No | `false` | Enable debug mode |
| `PORT` | No | `5000` | Server port |
| `SECRET_KEY` | No | — | Flask session secret |

---

## 🤝 Contributing

Built as a production-quality prototype. PRs welcome for:
- Collaborative editing (WebSockets)
- User authentication
- Document persistence (database)
- More AI models (Claude, GPT-4)
- Mobile responsive layout
