import csv
import io
import logging
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

import config
from agent import Agent
from tools.leads import get_lead_store

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

app = FastAPI(
    title="Lead Scraping Agent API",
    description="Claude-powered lead scraping agent — trouve et exporte des leads qualifiés",
    version="2.0.0",
)

agent = Agent()


# ─── Models ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def ui():
    """Simple chat UI."""
    return HTML_UI


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message to the agent and get a full response."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if not config.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    logger.info(f"[/chat] message='{req.message[:100]}'")
    try:
        response = agent.run(req.message)
        return ChatResponse(response=response)
    except Exception as e:
        logger.error(f"[/chat] error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream the agent response as Server-Sent Events."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if not config.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    logger.info(f"[/chat/stream] message='{req.message[:100]}'")

    async def generate() -> AsyncGenerator[str, None]:
        try:
            for chunk in agent.stream(req.message):
                # SSE format
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"[stream] error: {e}")
            yield f"data: Error: {e}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/leads/download")
async def download_leads():
    """Télécharger les derniers leads extraits en CSV."""
    leads = get_lead_store()
    if not leads:
        raise HTTPException(status_code=404, detail="Aucun lead disponible. Demandez d'abord à l'agent de trouver des leads.")

    fieldnames = ["name", "company", "email", "phone", "website", "source"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for lead in leads:
        writer.writerow({k: lead.get(k, "") for k in fieldnames})

    content = output.getvalue().encode("utf-8-sig")  # UTF-8 BOM pour Excel

    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": config.MODEL,
        "api_key_set": bool(config.ANTHROPIC_API_KEY),
        "tools": ["search_web", "scrape_url", "extract_leads", "export_leads_csv", "run_python"],
        "leads_in_store": len(get_lead_store()),
    }


# ─── HTML UI ──────────────────────────────────────────────────────────────────

HTML_UI = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Agent</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f172a; color: #e2e8f0; height: 100vh; display: flex;
         flex-direction: column; }
  header { background: #1e293b; padding: 16px 24px; border-bottom: 1px solid #334155;
           display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 1.25rem; font-weight: 600; color: #f1f5f9; }
  .badge { background: #6366f1; color: white; font-size: 0.7rem; padding: 2px 8px;
           border-radius: 9999px; font-weight: 500; }
  #chat { flex: 1; overflow-y: auto; padding: 24px; display: flex;
          flex-direction: column; gap: 16px; }
  .msg { max-width: 80%; padding: 12px 16px; border-radius: 12px; line-height: 1.6;
         white-space: pre-wrap; word-break: break-word; }
  .user { align-self: flex-end; background: #6366f1; color: white;
          border-bottom-right-radius: 4px; }
  .agent { align-self: flex-start; background: #1e293b; color: #e2e8f0;
           border-bottom-left-radius: 4px; border: 1px solid #334155; }
  .typing { color: #94a3b8; font-style: italic; }
  footer { background: #1e293b; padding: 16px 24px; border-top: 1px solid #334155; }
  #form { display: flex; gap: 12px; }
  #input { flex: 1; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;
           padding: 12px 16px; border-radius: 8px; font-size: 1rem; outline: none;
           transition: border-color 0.2s; }
  #input:focus { border-color: #6366f1; }
  button { background: #6366f1; color: white; border: none; padding: 12px 24px;
           border-radius: 8px; font-size: 1rem; cursor: pointer; font-weight: 500;
           transition: background 0.2s; }
  button:hover { background: #4f46e5; }
  button:disabled { background: #334155; cursor: not-allowed; }
  em { color: #94a3b8; }
  strong { color: #f1f5f9; }
</style>
</head>
<body>
<header>
  <h1>AI Agent</h1>
  <span class="badge">Claude</span>
  <span class="badge" style="background:#0ea5e9">Web Search</span>
  <span class="badge" style="background:#10b981">Lead Scraping</span>
  <span class="badge" style="background:#f59e0b">CSV Export</span>
</header>
<div id="chat">
  <div class="msg agent">Bonjour! Je suis votre agent de scraping de leads. Dites-moi quel type de leads vous cherchez — secteur, ville, critères — et je vais les trouver et les exporter en CSV.\n\nExemples :\n• "Trouve des plombiers à Paris avec leur email"\n• "Cherche des agences immobilières à Lyon"\n• "Leads de restaurants à Montréal"</div>
</div>
<footer>
  <form id="form">
    <input id="input" type="text" placeholder="Posez votre question..." autocomplete="off" />
    <button type="submit" id="btn">Envoyer</button>
  </form>
</footer>

<script>
const chat = document.getElementById('chat');
const form = document.getElementById('form');
const input = document.getElementById('input');
const btn = document.getElementById('btn');

function addMsg(text, cls) {
  const div = document.createElement('div');
  div.className = 'msg ' + cls;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function renderMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code style="background:#0f172a;padding:2px 6px;border-radius:4px;">$1</code>');
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = input.value.trim();
  if (!msg) return;

  addMsg(msg, 'user');
  input.value = '';
  btn.disabled = true;

  const agentDiv = addMsg('Réflexion en cours...', 'agent typing');
  let fullText = '';

  try {
    const resp = await fetch('/chat/stream', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg})
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    agentDiv.textContent = '';
    agentDiv.classList.remove('typing');

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      const lines = decoder.decode(value).split('\\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const chunk = line.slice(6);
          if (chunk === '[DONE]') break;
          fullText += chunk;
          agentDiv.innerHTML = renderMarkdown(fullText);
          chat.scrollTop = chat.scrollHeight;
        }
      }
    }
  } catch (err) {
    agentDiv.textContent = 'Erreur: ' + err.message;
    agentDiv.classList.remove('typing');
  } finally {
    btn.disabled = false;
    input.focus();
  }
});

input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    form.dispatchEvent(new Event('submit'));
  }
});
</script>
</body>
</html>
"""


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=False)
