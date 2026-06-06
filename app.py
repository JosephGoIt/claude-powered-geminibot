import asyncio
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="BlueBot")

# In-memory job store: job_id -> {status, result}
_jobs: dict = {}

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BlueBot</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0f172a;
      color: #e2e8f0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px 20px 80px;
    }
    .container { width: 100%; max-width: 740px; }
    .header { margin-bottom: 36px; }
    .header h1 { font-size: 1.75rem; font-weight: 700; color: #7dd3fc; }
    .header p { margin-top: 6px; color: #64748b; font-size: 0.9rem; }
    .card {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 20px;
    }
    textarea {
      width: 100%;
      background: transparent;
      border: none;
      outline: none;
      color: #e2e8f0;
      font-size: 0.95rem;
      font-family: inherit;
      resize: vertical;
      min-height: 130px;
      line-height: 1.65;
      caret-color: #7dd3fc;
    }
    textarea::placeholder { color: #475569; }
    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid #334155;
    }
    .hint { font-size: 0.78rem; color: #475569; }
    button {
      background: #3b82f6;
      color: #fff;
      border: none;
      padding: 9px 22px;
      border-radius: 8px;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s, opacity 0.15s;
    }
    button:hover:not(:disabled) { background: #2563eb; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .status {
      display: none;
      align-items: center;
      gap: 10px;
      margin-top: 22px;
      color: #94a3b8;
      font-size: 0.88rem;
    }
    .status.visible { display: flex; }
    .spinner {
      flex-shrink: 0;
      width: 16px; height: 16px;
      border: 2px solid #334155;
      border-top-color: #3b82f6;
      border-radius: 50%;
      animation: spin 0.65s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .result-card {
      display: none;
      margin-top: 24px;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 14px;
      overflow: hidden;
    }
    .result-card.visible { display: block; }
    .result-card.error { border-color: #7f1d1d; }
    .result-header {
      padding: 10px 18px;
      background: #0f172a;
      border-bottom: 1px solid #334155;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #475569;
    }
    .result-card.error .result-header { color: #f87171; border-color: #7f1d1d; }
    .result-body {
      padding: 18px;
      font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
      font-size: 0.85rem;
      color: #a5f3fc;
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.65;
    }
    .result-card.error .result-body { color: #fca5a5; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>BlueBot</h1>
      <p>Describe a task for the browser agent in plain language, then hit Send.</p>
    </div>

    <div class="card">
      <textarea id="task-input"
        placeholder="E.g. Go to maersk.com/tracking, enter BL number 721144157, and return the Actual Time of Arrival in Singapore as JSON."
        autofocus></textarea>
      <div class="card-footer">
        <span class="hint">Ctrl+Enter to send</span>
        <button id="send-btn" onclick="sendTask()">Send</button>
      </div>
    </div>

    <div class="status" id="status">
      <div class="spinner"></div>
      <span id="status-text">Running browser agent — this can take up to a minute...</span>
    </div>

    <div class="result-card" id="result-card">
      <div class="result-header" id="result-header">Result</div>
      <div class="result-body" id="result-body"></div>
    </div>
  </div>

  <script>
    let _pollTimer = null;

    async function sendTask() {
      const input = document.getElementById('task-input');
      const task = input.value.trim();
      if (!task) return;

      const btn = document.getElementById('send-btn');
      const status = document.getElementById('status');
      const card = document.getElementById('result-card');
      const header = document.getElementById('result-header');
      const body = document.getElementById('result-body');

      btn.disabled = true;
      status.classList.add('visible');
      card.className = 'result-card';
      body.textContent = '';

      if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }

      try {
        const res = await fetch('/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ task })
        });
        const data = await res.json();
        if (!res.ok) {
          showError(data.detail || 'Failed to start task.');
          btn.disabled = false;
          status.classList.remove('visible');
          return;
        }

        pollResult(data.job_id, btn, status, card, header, body);
      } catch (err) {
        showError('Network error: ' + err.message);
        btn.disabled = false;
        status.classList.remove('visible');
      }
    }

    function pollResult(jobId, btn, status, card, header, body) {
      let elapsed = 0;
      _pollTimer = setInterval(async () => {
        elapsed += 3;
        document.getElementById('status-text').textContent =
          `Running browser agent — ${elapsed}s elapsed...`;
        try {
          const res = await fetch('/result/' + jobId);
          const data = await res.json();

          if (data.status === 'done') {
            clearInterval(_pollTimer);
            card.classList.add('visible');
            header.textContent = 'Result';
            body.textContent = typeof data.result === 'object'
              ? JSON.stringify(data.result, null, 2)
              : data.result;
            btn.disabled = false;
            status.classList.remove('visible');
          } else if (data.status === 'error') {
            clearInterval(_pollTimer);
            showError(data.result || 'An unexpected error occurred.');
            btn.disabled = false;
            status.classList.remove('visible');
          }
          // status === 'pending' → keep polling
        } catch (err) {
          clearInterval(_pollTimer);
          showError('Network error while polling: ' + err.message);
          btn.disabled = false;
          status.classList.remove('visible');
        }
      }, 3000);
    }

    function showError(msg) {
      const card = document.getElementById('result-card');
      const header = document.getElementById('result-header');
      const body = document.getElementById('result-body');
      card.classList.add('visible', 'error');
      header.textContent = 'Error';
      body.textContent = msg;
    }

    document.getElementById('task-input').addEventListener('keydown', e => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) sendTask();
    });
  </script>
</body>
</html>"""


class TaskRequest(BaseModel):
    task: str


@app.get("/", response_class=HTMLResponse)
async def index():
    return PAGE


@app.post("/run")
async def run(request: TaskRequest):
    if not request.task.strip():
        raise HTTPException(status_code=400, detail="Task cannot be empty.")
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "result": None}
    asyncio.create_task(_run_job(job_id, request.task))
    return {"job_id": job_id}


@app.get("/result/{job_id}")
async def get_result(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


async def _run_job(job_id: str, task: str):
    try:
        from bluebot import run_agent
        result = await run_agent(task)
        _jobs[job_id] = {"status": "done", "result": result}
    except Exception as e:
        _jobs[job_id] = {"status": "error", "result": str(e)}
