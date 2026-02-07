import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

GIT_COMMITTER_EMAIL = os.environ.get("GIT_COMMITTER_EMAIL", "")
CODER_WORKSPACE_ID = os.environ.get("CODER_WORKSPACE_ID", "")


@app.get("/", response_class=HTMLResponse)
def index():
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
    </style>
</head>
<body>
    <div class="container">
        <h1 class="logo">RDX Wallet</h1>
        <p class="tagline">Secure. Simple. Yours.</p>
        <div class="card">
            <div class="card-title">Git committer</div>
            <div class="card-value {'empty' if not GIT_COMMITTER_EMAIL else ''}">{GIT_COMMITTER_EMAIL or "Not set"}</div>
        </div>
        <div class="card">
            <div class="card-title">Workspace</div>
            <div class="card-value {'empty' if not CODER_WORKSPACE_ID else ''}">{CODER_WORKSPACE_ID or "Not set"}</div>
        </div>
        <button class="btn" type="button">Connect wallet</button>
    </div>
</body>
</html>"""