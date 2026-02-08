import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

USERS_API = "https://jsonplaceholder.typicode.com/users"
COMMENTS_API = "https://jsonplaceholder.typicode.com/comments"

app = FastAPI()

GIT_COMMITTER_EMAIL = os.environ.get("GIT_COMMITTER_EMAIL", "")
CODER_WORKSPACE_ID = os.environ.get("CODER_WORKSPACE_ID", "")


def _wallet_keys_count() -> int | None:
    """Fetch users from JSONPlaceholder and return the length, or None on error."""
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(USERS_API)
            r.raise_for_status()
            data = r.json()
            return len(data) if isinstance(data, list) else None
    except Exception:
        return None


def _fetch_comments_ok() -> bool:
    """Fetch comments from JSONPlaceholder; return True if successful."""
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(COMMENTS_API)
            r.raise_for_status()
            data = r.json()
            return isinstance(data, list)
    except Exception:
        return False


def _greeting_from_email(email: str) -> str:
    """Turn email like admin@coder.local into 'Hello Admin'."""
    if not email or "@" not in email:
        return "Hello"
    local = email.split("@", 1)[0].strip()
    name = (local[:1].upper() + local[1:].lower()) if local else "Hello"
    return f"Hello {name}"


def _base_path(request: Request) -> str:
    """Path prefix when app is behind a proxy (e.g. Coder workspace)."""
    raw = os.environ.get("BASE_PATH", "").strip()
    if not raw:
        raw = request.scope.get("root_path", "") or ""
    if not raw and "x-forwarded-prefix" in request.headers:
        raw = request.headers["x-forwarded-prefix"]
    return raw.rstrip("/")


def _connect_area_html(connected: bool, error: bool = False, connect_url: str = "/connect") -> str:
    """HTML for the connect button area (initial or after connect)."""
    if connected:
        return """<div id="connect-area" class="connect-area">
            <div class="status-badge status-connected">
                <span class="status-dot"></span>
                Connected
            </div>
        </div>"""
    err = '<p class="connect-error">Connection failed. Try again.</p>' if error else ""
    return f"""<div id="connect-area" class="connect-area">
        {err}
        <button class="btn" type="button"
            hx-post="{connect_url}"
            hx-target="#connect-area"
            hx-swap="outerHTML"
            hx-indicator="#connect-spinner">
            <span class="btn-text">Connect wallet</span>
            <span id="connect-spinner" class="btn-spinner" aria-hidden="true"></span>
        </button>
    </div>"""


@app.post("/connect", response_class=HTMLResponse)
def connect(request: Request):
    base = _base_path(request)
    connect_url = f"{base}/connect" if base else "/connect"
    if _fetch_comments_ok():
        return _connect_area_html(connected=True, connect_url=connect_url)
    return _connect_area_html(connected=False, error=True, connect_url=connect_url)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    greeting = _greeting_from_email(GIT_COMMITTER_EMAIL)
    wallet_keys = _wallet_keys_count()
    base = _base_path(request)
    connect_url = f"{base}/connect" if base else "/connect"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RDX Wallet</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    <style>
        :root {{
            --bg: #0c0e12;
            --surface: #151922;
            --surface-hover: #1c202a;
            --border: rgba(255,255,255,0.06);
            --text: #e8eaed;
            --text-muted: #8b92a0;
            --accent: #00d4aa;
            --accent-dim: rgba(0, 212, 170, 0.15);
            --glow: rgba(0, 212, 170, 0.25);
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Outfit', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            background-image:
                radial-gradient(ellipse 80% 50% at 50% -20%, var(--accent-dim), transparent),
                linear-gradient(180deg, var(--bg) 0%, #0f1218 100%);
        }}
        .container {{
            width: 100%;
            max-width: 420px;
            text-align: center;
        }}
        .logo {{
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
            background: linear-gradient(135deg, #fff 0%, var(--text-muted) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .tagline {{
            font-size: 0.95rem;
            font-weight: 300;
            color: var(--text-muted);
            margin-bottom: 2rem;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem 1.75rem;
            text-align: left;
            margin-bottom: 1rem;
        }}
        .card-title {{
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            margin-bottom: 0.75rem;
        }}
        .card-value {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text);
            word-break: break-all;
        }}
        .card-value.empty {{
            color: var(--text-muted);
            font-style: italic;
        }}
        .btn {{
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            padding: 1rem 1.5rem;
            margin-top: 0.5rem;
            font-family: inherit;
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--bg);
            background: var(--accent);
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        .btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 8px 24px var(--glow);
        }}
        .btn:active {{
            transform: translateY(0);
        }}
        .connect-area {{
            margin-top: 0.5rem;
        }}
        .btn-spinner {{
            display: none;
            width: 1em;
            height: 1em;
            margin-left: 0.5rem;
            border: 2px solid var(--bg);
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }}
        .btn.htmx-request .btn-text {{
            visibility: hidden;
        }}
        .btn.htmx-request .btn-spinner {{
            display: inline-block;
            position: absolute;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            width: 100%;
            justify-content: center;
            padding: 1rem 1.5rem;
            font-size: 0.95rem;
            font-weight: 600;
            border-radius: 12px;
        }}
        .status-connected {{
            background: rgba(0, 212, 170, 0.2);
            color: var(--accent);
            border: 1px solid rgba(0, 212, 170, 0.4);
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent);
            box-shadow: 0 0 8px var(--accent);
        }}
        .connect-error {{
            font-size: 0.8rem;
            color: #e57373;
            margin-bottom: 0.5rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="logo">RDX Wallet</h1>
        <p class="tagline">Secure. Simple. Yours.</p>
        <div class="card">
            <div class="card-title">Workspace owner</div>
            <div class="card-value {'empty' if not GIT_COMMITTER_EMAIL else ''}">{greeting}</div>
        </div>
        <div class="card">
            <div class="card-title">Workspace ID</div>
            <div class="card-value {'empty' if not CODER_WORKSPACE_ID else ''}">{CODER_WORKSPACE_ID or "Not set"}</div>
        </div>
        <div class="card">
            <div class="card-title">Wallet keys</div>
            <div class="card-value {'empty' if wallet_keys is None else ''}">{wallet_keys if wallet_keys is not None else "—"}</div>
        </div>
        <div id="connect-area" class="connect-area">
        <button class="btn" type="button"
            hx-post="{connect_url}"
            hx-target="#connect-area"
            hx-swap="outerHTML"
            hx-indicator="#connect-spinner">
            <span class="btn-text">Connect wallet</span>
            <span id="connect-spinner" class="btn-spinner" aria-hidden="true"></span>
        </button>
    </div>
    </div>
</body>
</html>"""