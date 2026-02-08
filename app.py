import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

POSTS_API = "https://jsonplaceholder.typicode.com/posts"

app = FastAPI()

_VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
app.mount("/vendor", StaticFiles(directory=str(_VENDOR_DIR)), name="vendor")

GIT_COMMITTER_EMAIL = os.environ.get("GIT_COMMITTER_EMAIL", "")

MOCK_TOKENS = [
    {"id": "tok_1", "type": "GitLab PAT", "name": "gitlab-deploy-key", "masked": "glpat-****Xk9f"},
    {"id": "tok_2", "type": "JIRA", "name": "jira-automation", "masked": "jira-****m3Qz"},
    {"id": "tok_3", "type": "GitLab PAT", "name": "gitlab-ci-runner", "masked": "glpat-****Lw2d"},
]


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


# ---------------------------------------------------------------------------
# Shared CSS class strings (keeps the f-strings readable)
# ---------------------------------------------------------------------------
_BTN = "btn relative inline-flex items-center justify-center w-full py-3 px-5 text-sm font-semibold bg-emerald-400 text-gray-950 rounded-[10px] cursor-pointer transition-all duration-200 hover:brightness-110 hover:shadow-[0_4px_20px_rgba(52,211,153,0.2)] active:scale-[0.98]"
_BTN_SECONDARY = "btn relative inline-flex items-center justify-center w-full py-3 px-5 text-sm font-semibold text-gray-200 bg-white/[0.03] border border-white/[0.07] backdrop-blur-sm rounded-[10px] cursor-pointer transition-all duration-200 hover:bg-white/[0.07] hover:border-white/[0.14] hover:text-white active:scale-[0.98]"
_BTN_GHOST = "btn relative inline-flex items-center justify-center w-full py-3 px-5 text-sm font-semibold text-gray-500 bg-transparent border border-white/[0.07] rounded-[10px] cursor-pointer transition-all duration-200 hover:bg-white/[0.05] hover:border-white/[0.14] hover:text-gray-200 active:scale-[0.98]"
_BTN_DANGER = "btn relative inline-flex items-center justify-center w-full py-3 px-5 text-sm font-semibold bg-red-400 text-white rounded-[10px] cursor-pointer transition-all duration-200 hover:brightness-110 hover:shadow-[0_4px_20px_rgba(248,113,113,0.2)] active:scale-[0.98]"
_SPINNER = "btn-spinner hidden w-[1em] h-[1em] border-2 border-gray-950 border-t-transparent rounded-full animate-spin"
_SPINNER_LIGHT = "btn-spinner hidden w-[1em] h-[1em] border-2 border-white border-t-transparent rounded-full animate-spin"
_SPINNER_SECONDARY = "btn-spinner hidden w-[1em] h-[1em] border-2 border-gray-200 border-t-transparent rounded-full animate-spin"
_LABEL = "block text-[0.65rem] font-semibold uppercase tracking-wider text-gray-500 mb-2"
_INPUT = "w-full px-3.5 py-2.5 mb-4 font-mono text-sm text-gray-200 bg-[#12151b] border border-white/[0.07] rounded-[10px] transition-all duration-200 placeholder:text-gray-500 focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-400/10"
_RADIO_OPTION = "radio-option flex items-center gap-3 px-3.5 py-2.5 bg-[#12151b] border border-white/[0.07] rounded-[10px] cursor-pointer transition-all duration-200 hover:border-white/[0.14] hover:bg-white/[0.04] has-[:checked]:border-emerald-400 has-[:checked]:bg-emerald-400/10"
_RADIO_INPUT = "radio-dot appearance-none w-4 h-4 border-2 border-gray-500 rounded-full cursor-pointer transition-all duration-150 shrink-0 checked:border-emerald-400 checked:bg-emerald-400 checked:shadow-[inset_0_0_0_3px_#12151b]"


def _actions_area_html(message: str = "", error: bool = False) -> str:
    """HTML for the wallet actions area: Add Wallet Key + Update / Delete."""
    msg_html = ""
    if message:
        if error:
            msg_html = f'<p class="text-sm text-center px-3 py-2.5 rounded-[10px] text-red-400 bg-red-400/[0.12] mb-1">{message}</p>'
        else:
            msg_html = f'<p class="text-sm text-center px-3 py-2.5 rounded-[10px] text-emerald-400 bg-emerald-400/10 mb-1">{message}</p>'
    return f"""<div id="connect-area" class="flex flex-col gap-2 mt-1">
        {msg_html}
        <button class="{_BTN}" type="button"
            hx-get="./add-key-form"
            hx-target="#connect-area"
            hx-swap="outerHTML"
            hx-indicator="#add-spinner"
            hx-disabled-elt="this">
            <span class="btn-text">Add Wallet Key</span>
            <span id="add-spinner" class="{_SPINNER}" aria-hidden="true"></span>
        </button>
        <div class="flex gap-2">
            <button class="{_BTN_SECONDARY}" type="button"
                hx-get="./update-key-form"
                hx-target="#connect-area"
                hx-swap="outerHTML"
                hx-indicator="#update-spinner"
                hx-disabled-elt="this">
                <span class="btn-text">Update key</span>
                <span id="update-spinner" class="{_SPINNER_SECONDARY}" aria-hidden="true"></span>
            </button>
            <button class="{_BTN_SECONDARY}" type="button"
                hx-get="./delete-key-form"
                hx-target="#connect-area"
                hx-swap="outerHTML"
                hx-indicator="#delete-spinner"
                hx-disabled-elt="this">
                <span class="btn-text">Delete key</span>
                <span id="delete-spinner" class="{_SPINNER_SECONDARY}" aria-hidden="true"></span>
            </button>
        </div>
    </div>"""


def _add_key_form_html(error: bool = False) -> str:
    """HTML for the add key form (radio token type, then key input after selection)."""
    err = f'<p class="text-[0.78rem] text-red-400 bg-red-400/[0.12] px-3 py-2 rounded-[10px] mb-3">Failed to add key. Try again.</p>' if error else ""
    return f"""<div id="connect-area" class="mt-1">
        {err}
        <form class="text-left" id="add-key-form" hx-post="./add-key" hx-target="#connect-area" hx-swap="outerHTML" hx-indicator="#submit-spinner" hx-disabled-elt="find button[type='submit']">
            <label class="{_LABEL}">Token type</label>
            <div class="flex flex-col gap-1.5 mb-4">
                <label class="{_RADIO_OPTION}">
                    <input class="{_RADIO_INPUT}" type="radio" name="token_type" value="gitlab_pat" required />
                    <span class="text-sm font-medium text-gray-200">GitLab PAT token</span>
                </label>
                <label class="{_RADIO_OPTION}">
                    <input class="{_RADIO_INPUT}" type="radio" name="token_type" value="jira" />
                    <span class="text-sm font-medium text-gray-200">JIRA token</span>
                </label>
            </div>
            <div id="add-key-input-wrap" class="hidden">
                <label class="{_LABEL}" for="wallet-key">Key</label>
                <input class="{_INPUT}" id="wallet-key" name="key" type="text" placeholder="Enter your token" autocomplete="off" required />
            </div>
            <div class="flex gap-2 mt-2">
                <button class="{_BTN_GHOST} flex-1" type="button" hx-get="./actions" hx-target="#connect-area" hx-swap="outerHTML">
                    Cancel
                </button>
                <button class="{_BTN} flex-1" type="submit">
                    <span class="btn-text">Save key</span>
                    <span id="submit-spinner" class="{_SPINNER}" aria-hidden="true"></span>
                </button>
            </div>
        </form>
    </div>"""


def _token_radios() -> str:
    """Build radio-option HTML for each mock token."""
    html = ""
    for t in MOCK_TOKENS:
        html += f"""<label class="{_RADIO_OPTION}">
                    <input class="{_RADIO_INPUT}" type="radio" name="token_id" value="{t['id']}" required />
                    <span>
                        <span class="block text-sm font-medium text-gray-200">{t['name']}</span>
                        <span class="block font-mono text-[0.7rem] text-gray-500 mt-0.5">{t['type']} &middot; {t['masked']}</span>
                    </span>
                </label>
"""
    return html


def _update_key_form_html(error: bool = False) -> str:
    """HTML for the update key form (select token, then new key input after selection)."""
    err = f'<p class="text-[0.78rem] text-red-400 bg-red-400/[0.12] px-3 py-2 rounded-[10px] mb-3">Update failed. Try again.</p>' if error else ""
    return f"""<div id="connect-area" class="mt-1">
        {err}
        <form class="text-left" id="update-key-form" hx-post="./update-key" hx-target="#connect-area" hx-swap="outerHTML" hx-indicator="#update-submit-spinner" hx-disabled-elt="find button[type='submit']">
            <label class="{_LABEL}">Select token to update</label>
            <div class="flex flex-col gap-1.5 mb-4">
                {_token_radios()}
            </div>
            <div id="update-new-key-wrap" class="hidden">
                <label class="{_LABEL}" for="new-key">New key</label>
                <input class="{_INPUT}" id="new-key" name="key" type="text" placeholder="Enter new token value" autocomplete="off" required />
            </div>
            <div class="flex gap-2 mt-2">
                <button class="{_BTN_GHOST} flex-1" type="button" hx-get="./actions" hx-target="#connect-area" hx-swap="outerHTML">
                    Cancel
                </button>
                <button class="{_BTN} flex-1" type="submit">
                    <span class="btn-text">Save</span>
                    <span id="update-submit-spinner" class="{_SPINNER}" aria-hidden="true"></span>
                </button>
            </div>
        </form>
    </div>"""


def _delete_key_form_html(message: str = "", error: bool = False) -> str:
    """HTML for the delete key form (token list + confirm)."""
    msg_html = ""
    if message:
        if error:
            msg_html = f'<p class="text-[0.78rem] text-red-400 bg-red-400/[0.12] px-3 py-2 rounded-[10px] mb-3">{message}</p>'
        else:
            msg_html = f'<p class="text-sm text-center px-3 py-2.5 rounded-[10px] text-emerald-400 bg-emerald-400/10 mb-1">{message}</p>'
    return f"""<div id="connect-area" class="mt-1">
        {msg_html}
        <form class="text-left" id="delete-key-form">
            <label class="{_LABEL}">Select token to delete</label>
            <div class="flex flex-col gap-1.5 mb-4">
                {_token_radios()}
            </div>
            <div class="flex gap-2 mt-2">
                <button class="{_BTN_GHOST} flex-1" type="button" hx-get="./actions" hx-target="#connect-area" hx-swap="outerHTML">
                    Cancel
                </button>
                <button class="{_BTN_DANGER} flex-1" type="button"
                    hx-post="./delete-key"
                    hx-target="#connect-area"
                    hx-swap="outerHTML"
                    hx-include="#delete-key-form"
                    hx-confirm="Are you sure you want to delete this token? This action cannot be undone."
                    hx-disabled-elt="this"
                    hx-indicator="#delete-confirm-spinner">
                    <span class="btn-text">Delete</span>
                    <span id="delete-confirm-spinner" class="{_SPINNER_LIGHT}" aria-hidden="true"></span>
                </button>
            </div>
        </form>
    </div>"""


@app.get("/actions", response_class=HTMLResponse)
def get_actions():
    return _actions_area_html()


@app.get("/add-key-form", response_class=HTMLResponse)
def get_add_key_form():
    return _add_key_form_html()


@app.get("/update-key-form", response_class=HTMLResponse)
def get_update_key_form():
    return _update_key_form_html()


@app.get("/delete-key-form", response_class=HTMLResponse)
def get_delete_key_form():
    return _delete_key_form_html()


@app.post("/add-key", response_class=HTMLResponse)
def add_key(token_type: str = Form(...), key: str = Form(...)):
    ok = _call_placeholder_post({"title": token_type, "body": key, "userId": 1})
    if ok:
        return _actions_area_html(message="Key added.", error=False)
    return HTMLResponse(_add_key_form_html(error=True), status_code=422)


@app.post("/update-key", response_class=HTMLResponse)
def update_key(token_id: str = Form(...), key: str = Form(...)):
    ok = _call_placeholder_post({"title": "update_key", "body": key, "tokenId": token_id})
    if ok:
        return _actions_area_html(message="Key updated.", error=False)
    return HTMLResponse(_update_key_form_html(error=True), status_code=422)


@app.post("/delete-key", response_class=HTMLResponse)
def delete_key(token_id: str = Form(...)):
    ok = _call_placeholder_delete()
    if ok:
        return _actions_area_html(message="Token deleted.", error=False)
    return HTMLResponse(_delete_key_form_html(message="Delete failed. Try again.", error=True), status_code=422)


@app.get("/", response_class=HTMLResponse)
def index():
    email_cls = "text-gray-500 italic" if not GIT_COMMITTER_EMAIL else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RDX Wallet</title>
    <link rel="stylesheet" href="/vendor/css/fonts.css">
    <script src="/vendor/js/tailwindcss.js"></script>
    <script>
    tailwind.config = {{
        theme: {{
            extend: {{
                fontFamily: {{
                    sans: ['Outfit', 'system-ui', '-apple-system', 'sans-serif'],
                    mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
                }},
            }},
        }},
    }}
    </script>
    <script src="/vendor/js/htmx-2.0.4.min.js"></script>
    <script>
    document.addEventListener("htmx:beforeSwap", function(e) {{
        if (e.detail.xhr.status === 422) {{ e.detail.shouldSwap = true; }}
    }});
    </script>
    <style>
        body {{
            background-image: radial-gradient(ellipse 60% 40% at 50% -10%, rgba(52,211,153,0.08), transparent);
        }}
        /* htmx spinner states */
        .btn.htmx-request .btn-text {{ visibility: hidden; }}
        .btn.htmx-request .btn-spinner {{ display: inline-block; position: absolute; }}
        form.htmx-request .btn .btn-text {{ visibility: hidden; }}
        form.htmx-request .btn .btn-spinner {{ display: inline-block; position: absolute; }}
        /* Radio-reveal: show key input when a radio is selected */
        #add-key-form:has(input[name="token_type"]:checked) #add-key-input-wrap,
        #update-key-form:has(input[name="token_id"]:checked) #update-new-key-wrap {{
            display: block !important;
        }}
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-6 bg-[#090b0f] text-gray-200 font-sans">
    <div class="w-full max-w-[400px]">
        <h1 class="text-[1.75rem] font-bold tracking-tight text-center text-white mb-0.5">RDX Wallet</h1>
        <p class="text-sm text-gray-500 text-center mb-8">Secure. Simple. Yours.</p>

        <div class="bg-white/[0.03] backdrop-blur-xl border border-white/[0.07] rounded-[14px] px-6 py-5 text-left mb-3">
            <div class="text-[0.65rem] font-semibold uppercase tracking-wider text-gray-500 mb-2">Email</div>
            <div class="font-mono text-sm break-all {email_cls}">{GIT_COMMITTER_EMAIL or "Not set"}</div>
        </div>

        {_actions_area_html()}

        <p class="text-xs text-gray-500 text-center mt-5 leading-relaxed">Auto-deletion policy: All tokens are automatically deleted after 30 days. This is non-adjustable.</p>
    </div>
</body>
</html>"""
