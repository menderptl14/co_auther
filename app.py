"""
Co-Author: Interactive AI Writing Editor
Backend: Flask + Google Gemini API
Architecture: Single-file backend with modular prompt templates
"""

import os
import json
import time
import sqlite3
import datetime
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# print("API KEY:", GEMINI_API_KEY)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "metrics.db")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None

# ─── Database Setup ────────────────────────────────────────────────────────────
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            action_type TEXT,
            response_time_ms REAL,
            input_length INTEGER,
            output_length INTEGER,
            success INTEGER
        )
    """)
    conn.commit()
    conn.close()

def log_metric(action_type, response_time_ms, input_length, output_length, success=1):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO metrics (timestamp, action_type, response_time_ms, input_length, output_length, success)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.datetime.utcnow().isoformat(), action_type, response_time_ms, input_length, output_length, success))
        conn.commit()
        conn.close()
    except Exception as e:
        app.logger.error(f"Metrics logging error: {e}")

# ─── Prompt Templates ──────────────────────────────────────────────────────────
PROMPTS = {
    "grammar": """You are a professional copy editor. Fix all grammar, spelling, and punctuation errors in the text below. 
Preserve the original voice and meaning. Return ONLY the corrected text, no explanations.

Text: {text}""",

    "summarize": """You are an expert summarizer. Create a concise summary of the text below.
Capture the key points in 2-4 sentences. Return ONLY the summary.

Text: {text}""",

    "rewrite_professional": """You are a professional business writer. Rewrite the text below in a polished, 
professional tone suitable for business communication. Maintain all key information.
Return ONLY the rewritten text.

Text: {text}""",

    "expand": """You are a creative writer. Expand the text below with more detail, context, and depth.
Add relevant examples or elaboration. Aim for roughly 2x the original length.
Return ONLY the expanded text.

Text: {text}""",

    "shorten": """You are a skilled editor. Shorten the text below to its most essential points.
Remove redundancy while preserving core meaning. Aim for roughly half the original length.
Return ONLY the shortened text.

Text: {text}""",

    "tone_formal": """Rewrite the following text in a formal, academic tone. 
Use sophisticated vocabulary and structured sentences. Return ONLY the rewritten text.

Text: {text}""",

    "tone_casual": """Rewrite the following text in a friendly, casual conversational tone.
Make it feel warm and approachable. Return ONLY the rewritten text.

Text: {text}""",

    "tone_persuasive": """Rewrite the following text in a compelling, persuasive tone.
Use rhetorical techniques to make it more convincing. Return ONLY the rewritten text.

Text: {text}""",

    "tone_analysis": """Analyze the tone of the following text. Provide:
1. Primary tone (e.g., formal, casual, persuasive, informative, emotional)
2. Sentiment (positive, negative, neutral)
3. Writing style characteristics (2-3 key traits)
4. Audience suitability
5. One specific suggestion to improve the tone

Format your response as a structured analysis. Be concise and specific.

Text: {text}""",

    "chat": """You are Co-Author, an intelligent AI writing assistant embedded in a document editor.
You have full access to the user's current document content.

CURRENT DOCUMENT CONTENT:
---
{document_content}
---

Your capabilities:
- Analyze, improve, and edit any part of the document
- Answer questions about the document content
- Suggest improvements, fix grammar, change tone
- Help with writing structure and flow
- When suggesting edits, clearly show what should change

When the user asks you to fix or improve something, provide the improved version clearly 
marked so it can be applied. Use format: [SUGGESTED EDIT: <improved text>] for inline suggestions.

Be concise, helpful, and actionable. You are a trusted writing partner."""
}

def call_gemini(prompt: str, stream: bool = False) -> str:
    """Call Gemini API with error handling."""
    if not model:
        return "⚠️ API key not configured. Please set GEMINI_API_KEY in your .env file."
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )
        return response.text
    except Exception as e:
        app.logger.error(f"Gemini API error: {e}")
        raise

# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    """Main chat endpoint - context-aware conversation about the document."""
    data = request.get_json()
    message = data.get("message", "").strip()
    document_content = data.get("document_content", "").strip()
    
    if not message:
        return jsonify({"error": "Message is required"}), 400

    start_time = time.time()
    
    try:
        system_prompt = PROMPTS["chat"].format(
            document_content=document_content if document_content else "(empty document)"
        )
        full_prompt = f"{system_prompt}\n\nUser: {message}\n\nAssistant:"
        
        response_text = call_gemini(full_prompt)
        elapsed = (time.time() - start_time) * 1000
        
        log_metric("chat", elapsed, len(message), len(response_text))
        
        return jsonify({
            "response": response_text,
            "response_time_ms": round(elapsed, 2)
        })
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        log_metric("chat", elapsed, len(message), 0, success=0)
        return jsonify({"error": str(e)}), 500

@app.route("/chat/stream", methods=["POST"])
def chat_stream():
    """Streaming chat endpoint for real-time feel."""
    data = request.get_json()
    message = data.get("message", "").strip()
    document_content = data.get("document_content", "").strip()
    
    if not message:
        return jsonify({"error": "Message is required"}), 400

    if not model:
        def no_key():
            yield f"data: {json.dumps({'chunk': '⚠️ API key not configured. Please set GEMINI_API_KEY in your .env file.'})}\n\n"
            yield "data: [DONE]\n\n"
        return Response(stream_with_context(no_key()), mimetype="text/event-stream")

    def generate():
        start_time = time.time()
        full_text = ""
        try:
            system_prompt = PROMPTS["chat"].format(
                document_content=document_content if document_content else "(empty document)"
            )
            full_prompt = f"{system_prompt}\n\nUser: {message}\n\nAssistant:"
            
            response = model.generate_content(
                full_prompt,
                stream=True,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                )
            )
            
            for chunk in response:
                if chunk.text:
                    full_text += chunk.text
                    yield f"data: {json.dumps({'chunk': chunk.text})}\n\n"
                    time.sleep(0.01)  # slight delay for smooth streaming feel
            
            elapsed = (time.time() - start_time) * 1000
            log_metric("chat_stream", elapsed, len(message), len(full_text))
            yield f"data: {json.dumps({'done': True, 'response_time_ms': round(elapsed, 2)})}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            log_metric("chat_stream", elapsed, len(message), 0, success=0)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/improve", methods=["POST"])
def improve():
    """Improve selected text with a specific action."""
    data = request.get_json()
    text = data.get("text", "").strip()
    action = data.get("action", "grammar").strip()
    
    if not text:
        return jsonify({"error": "Text is required"}), 400
    
    if action not in PROMPTS:
        return jsonify({"error": f"Unknown action: {action}"}), 400

    start_time = time.time()
    
    try:
        prompt = PROMPTS[action].format(text=text)
        improved = call_gemini(prompt)
        elapsed = (time.time() - start_time) * 1000
        
        log_metric(action, elapsed, len(text), len(improved))
        
        return jsonify({
            "original": text,
            "improved": improved,
            "action": action,
            "response_time_ms": round(elapsed, 2)
        })
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        log_metric(action, elapsed, len(text), 0, success=0)
        return jsonify({"error": str(e)}), 500

@app.route("/analyze", methods=["POST"])
def analyze():
    """Analyze document tone and statistics."""
    data = request.get_json()
    text = data.get("text", "").strip()
    
    if not text:
        return jsonify({"error": "Text is required"}), 400

    start_time = time.time()
    
    try:
        prompt = PROMPTS["tone_analysis"].format(text=text[:3000])  # limit for analysis
        analysis = call_gemini(prompt)
        elapsed = (time.time() - start_time) * 1000
        
        log_metric("tone_analysis", elapsed, len(text), len(analysis))
        
        # Calculate stats
        words = len(text.split())
        sentences = text.count('.') + text.count('!') + text.count('?')
        reading_time = max(1, round(words / 200))  # avg 200 wpm
        
        return jsonify({
            "analysis": analysis,
            "stats": {
                "words": words,
                "sentences": max(1, sentences),
                "characters": len(text),
                "paragraphs": len([p for p in text.split('\n\n') if p.strip()]),
                "reading_time_minutes": reading_time
            },
            "response_time_ms": round(elapsed, 2)
        })
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        log_metric("analyze", elapsed, len(text), 0, success=0)
        return jsonify({"error": str(e)}), 500

@app.route("/metrics", methods=["GET"])
def metrics():
    """Return aggregated metrics dashboard data."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        total = conn.execute("SELECT COUNT(*) as count FROM metrics").fetchone()["count"]
        avg_rt = conn.execute("SELECT AVG(response_time_ms) as avg FROM metrics WHERE success=1").fetchone()["avg"]
        by_action = conn.execute("""
            SELECT action_type, COUNT(*) as count, AVG(response_time_ms) as avg_ms
            FROM metrics GROUP BY action_type ORDER BY count DESC
        """).fetchall()
        recent = conn.execute("""
            SELECT * FROM metrics ORDER BY id DESC LIMIT 20
        """).fetchall()
        
        conn.close()
        
        return jsonify({
            "total_requests": total,
            "avg_response_time_ms": round(avg_rt or 0, 2),
            "by_action": [dict(r) for r in by_action],
            "recent": [dict(r) for r in recent]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/export", methods=["POST"])
def export():
    """Export document content as Markdown or TXT."""
    data = request.get_json()
    content = data.get("content", "")
    format_type = data.get("format", "markdown")
    title = data.get("title", "document")
    
    if format_type == "markdown":
        # Basic HTML to Markdown conversion
        import re
        md = content
        md = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1', md, flags=re.DOTALL)
        md = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', md, flags=re.DOTALL)
        md = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', md, flags=re.DOTALL)
        md = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', md, flags=re.DOTALL)
        md = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', md, flags=re.DOTALL)
        md = re.sub(r'<br\s*/?>', '\n', md)
        md = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', md, flags=re.DOTALL)
        md = re.sub(r'<[^>]+>', '', md)
        md = re.sub(r'\n{3,}', '\n\n', md)
        
        return Response(
            md.strip(),
            mimetype="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={title}.md"}
        )
    else:
        # Plain text
        import re
        txt = re.sub(r'<[^>]+>', '', content)
        txt = re.sub(r'\n{3,}', '\n\n', txt)
        
        return Response(
            txt.strip(),
            mimetype="text/plain",
            headers={"Content-Disposition": f"attachment; filename={title}.txt"}
        )

# ─── Health Check ──────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "api_configured": bool(GEMINI_API_KEY),
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
