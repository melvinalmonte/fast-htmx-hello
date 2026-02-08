import os

import httpx
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

USERS_API = "https://jsonplaceholder.typicode.com/users"
COMMENTS_API = "https://jsonplaceholder.typicode.com/comments"
POSTS_API = "https://jsonplaceholder.typicode.com/posts"

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


def _call_placeholder_post(body: dict) -> bool:
    """POST to JSONPlaceholder (for update-key simulation). Return True if ok."""
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(POSTS_API, json=body)
            r.raise_for_status()
            return True
    except Exception:
        return False


def _call_placeholder_delete() -> bool:
    """DELETE to JSONPlaceholder (for delete-key simulation). Return True if ok."""
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.delete(f"{POSTS_API}/1")
            r.raise_for_status()
            return True
    except Exception:
        return False


def _actions_area_html(message: str = "", error: bool = False) -> str:
    """HTML for the wallet actions area: Update Wallet Key + Delete key."""
    msg_html = ""
    if message:
        cls = "actions-message actions-error" if error else "actions-message actions-success"
        msg_html = f'<p class="{cls}">{message}</p>'
    return f"""<div id="connect-area" class="connect-area actions-area">
        {msg_html}
        <button class="btn" type="button"
            hx-get="./update-key-form"
            hx-target="#connect-area"
            hx-swap="outerHTML"
            hx-indicator="#update-spinner">
            <span class="btn-text">Update Wallet Key</span>
            <span id="update-spinner" class="btn-spinner" aria-hidden="true"></span>
        </button>
        <button class="btn btn-secondary" type="button" onclick="document.getElementById('delete-modal').showModal()">
            Delete key
        </button>
    </div>"""


def _update_key_form_html(error: bool = False) -> str:
    """HTML for the update key form (input + submit/cancel)."""
    err = '<p class="connect-error">Update failed. Try again.</p>' if error else ""
    return f"""<div id="connect-area" class="connect-area">
        {err}
        <form class="update-key-form" hx-post="./update-key" hx-target="#connect-area" hx-swap="outerHTML" hx-indicator="#submit-spinner">
            <label class="form-label" for="wallet-key">Wallet key</label>
            <input class="form-input" id="wallet-key" name="key" type="text" required placeholder="Enter your key" autocomplete="off" />
            <div class="form-actions">
                <button class="btn btn-ghost" type="button" hx-get="./actions" hx-target="#connect-area" hx-swap="outerHTML">
                    Cancel
                </button>
                <button class="btn" type="submit">
                    <span class="btn-text">Save key</span>
                    <span id="submit-spinner" class="btn-spinner" aria-hidden="true"></span>
                </button>
            </div>
        </form>
    </div>"""


@app.get("/actions", response_class=HTMLResponse)
def get_actions():
    return _actions_area_html()


@app.get("/update-key-form", response_class=HTMLResponse)
def get_update_key_form():
    return _update_key_form_html()


@app.post("/update-key", response_class=HTMLResponse)
def update_key(key: str = Form(...)):
    ok = _call_placeholder_post({"title": "wallet_key", "body": key, "userId": 1})
    if ok:
        return _actions_area_html(message="Key updated.", error=False)
    return _update_key_form_html(error=True)


@app.post("/delete-key", response_class=HTMLResponse)
def delete_key():
    if _call_placeholder_delete():
        return _actions_area_html(message="Key deleted.", error=False)
    return _actions_area_html(message="Delete failed. Try again.", error=True)


@app.get("/", response_class=HTMLResponse)
def index():
    greeting = _greeting_from_email(GIT_COMMITTER_EMAIL)
    wallet_keys = _wallet_keys_count()
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
        .btn-secondary {{
            background: rgba(255, 255, 255, 0.06);
            color: var(--text);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        .btn-secondary:hover {{
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            border-color: rgba(255, 255, 255, 0.3);
        }}
        .btn-ghost {{
            background: rgba(255, 255, 255, 0.06);
            color: var(--text);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        .btn-ghost:hover {{
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            border-color: rgba(255, 255, 255, 0.3);
        }}
        .actions-area .btn {{
            margin-top: 0.5rem;
        }}
        .actions-message {{
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
        }}
        .actions-success {{ color: var(--accent); }}
        .actions-error {{ color: #e57373; }}
        .update-key-form {{
            text-align: left;
        }}
        .form-label {{
            display: block;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }}
        .form-input {{
            width: 100%;
            padding: 0.75rem 1rem;
            margin-bottom: 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            color: var(--text);
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
        }}
        .form-input::placeholder {{
            color: var(--text-muted);
        }}
        .form-input:focus {{
            outline: none;
            border-color: var(--accent);
        }}
        .form-actions {{
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }}
        .form-actions .btn {{
            flex: 1;
            margin-top: 0;
        }}
        form.htmx-request .btn .btn-text {{
            visibility: hidden;
        }}
        form.htmx-request .btn .btn-spinner {{
            display: inline-block;
            position: absolute;
        }}
        dialog {{
            margin: auto;
            padding: 0;
            border: 1px solid var(--border);
            border-radius: 16px;
            background: var(--surface);
            color: var(--text);
            max-width: 90%;
            width: 360px;
        }}
        dialog::backdrop {{
            background: rgba(0, 0, 0, 0.6);
        }}
        .modal-content {{
            padding: 1.5rem 1.75rem;
        }}
        .modal-content h3 {{
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }}
        .modal-content p {{
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-bottom: 1.25rem;
        }}
        .modal-actions {{
            display: flex;
            gap: 0.5rem;
            justify-content: flex-end;
        }}
        .modal-actions .btn {{
            margin-top: 0;
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
        <div id="connect-area" class="connect-area actions-area">
        <button class="btn" type="button"
            hx-get="./update-key-form"
            hx-target="#connect-area"
            hx-swap="outerHTML"
            hx-indicator="#update-spinner">
            <span class="btn-text">Update Wallet Key</span>
            <span id="update-spinner" class="btn-spinner" aria-hidden="true"></span>
        </button>
        <button class="btn btn-secondary" type="button" onclick="document.getElementById('delete-modal').showModal()">
            Delete key
        </button>
    </div>
    <dialog id="delete-modal">
        <div class="modal-content">
            <h3>Delete key</h3>
            <p>Are you sure you want to delete your key? This action cannot be undone.</p>
            <div class="modal-actions">
                <button class="btn btn-ghost" type="button" onclick="document.getElementById('delete-modal').close()">Cancel</button>
                <button class="btn" type="button"
                    hx-post="./delete-key"
                    hx-target="#connect-area"
                    hx-swap="outerHTML">
                    Delete
                </button>
            </div>
        </div>
    </dialog>
    <script>
    document.body.addEventListener('htmx:afterSwap', function(ev) {{
        if (ev.detail?.target?.id === 'connect-area') {{
            var modal = document.getElementById('delete-modal');
            if (modal && typeof modal.close === 'function') modal.close();
        }}
    }});
    </script>
    </div>
</body>
</html>"""