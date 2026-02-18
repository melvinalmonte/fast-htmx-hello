import os
import base64
import hashlib
from pathlib import Path

import boto3
import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TOKEN_TYPES = {
    "gitlab_token": "gitlab",
    "jira_token": "jira",
    "claude_token": "claude",
    "confluence_token": "confluence",
}

app = FastAPI()

_VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
app.mount("/vendor", StaticFiles(directory=str(_VENDOR_DIR)), name="vendor")

GIT_COMMITTER_EMAIL = os.environ.get("GIT_COMMITTER_EMAIL", "")
CODER_AGENT_URL = os.environ.get("CODER_AGENT_URL", "")
CODER_AGENT_TOKEN = os.environ.get("CODER_AGENT_TOKEN", "")


def _fetch_git_ssh_key() -> dict:
    """Fetch the Git SSH key pair from the Coder agent API.

    Returns a dict with 'public_key' and 'private_key' fields.
    """
    with httpx.Client(timeout=10.0) as client:
        r = client.get(
            f"{CODER_AGENT_URL}/api/v2/workspaceagents/me/gitsshkey",
            headers={"Authorization": f"Bearer {CODER_AGENT_TOKEN}"},
        )
        r.raise_for_status()
        return r.json()

def _ed25519_to_x25519(ed_priv_key, ed_pub_key):
    """Convert Ed25519 keys to X25519 keys for key exchange."""
    priv_bytes = ed_priv_key.private_bytes_raw()
    h = hashlib.sha512(priv_bytes).digest()
    x25519_priv_bytes = bytearray(h[:32])
    x25519_priv_bytes[0] &= 248
    x25519_priv_bytes[31] &= 127
    x25519_priv_bytes[31] |= 64

    pub_bytes = ed_pub_key.public_bytes_raw()
    p = 2**255 - 19
    y = int.from_bytes(pub_bytes, "little") & ((1 << 255) - 1)
    u = ((1 + y) * pow(1 - y, -1, p)) % p
    x25519_pub_bytes = u.to_bytes(32, "little")

    return (
        x25519.X25519PrivateKey.from_private_bytes(bytes(x25519_priv_bytes)),
        x25519.X25519PublicKey.from_public_bytes(x25519_pub_bytes),
    )


def _derive_key(shared_key: bytes) -> bytes:
    """Derive AES key from shared secret using HKDF."""
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=b"wallet-encryption"
    ).derive(shared_key)


def _encrypt_payload(plaintext: str, peer_x25519_pub) -> str:
    """Encrypt plaintext via X25519 key exchange. Returns base64-encoded payload."""
    ephemeral_key = x25519.X25519PrivateKey.generate()
    shared_key = ephemeral_key.exchange(peer_x25519_pub)
    derived_key = _derive_key(shared_key)

    iv = os.urandom(12)
    encryptor = Cipher(algorithms.AES(derived_key), modes.GCM(iv)).encryptor()
    ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()

    payload = iv + ephemeral_key.public_key().public_bytes_raw() + encryptor.tag + ciphertext
    return base64.b64encode(payload).decode("utf-8")


def _store_secret(sm_client, secret_name: str, value: str):
    """Store secret in AWS Secrets Manager, creating if it doesn't exist."""
    try:
        sm_client.create_secret(Name=secret_name, SecretString=value)
    except sm_client.exceptions.ResourceExistsException:
        sm_client.put_secret_value(SecretId=secret_name, SecretString=value)


def _create_wallet_secret(token_type: str, plaintext_key: str) -> str:
    """Encrypt a token and store it in AWS Secrets Manager.

    Follows the reference run_test flow:
      1. Fetch SSH keys from Coder agent API
      2. Load Ed25519 private key -> derive X25519 public key
      3. Build wallet_id from email + public key
      4. Encrypt the plaintext token with X25519 key exchange
      5. Store the encrypted blob in Secrets Manager

    Returns the secret name on success, raises on failure.
    """
    ssh_keys = _fetch_git_ssh_key()
    pub_ssh = ssh_keys["public_key"].strip()
    priv_openssh = ssh_keys["private_key"].strip()

    private_key_obj = serialization.load_ssh_private_key(priv_openssh.encode(), password=None)
    public_key_obj = private_key_obj.public_key()
    _, x25519_pub = _ed25519_to_x25519(private_key_obj, public_key_obj)

    wallet_id = hashlib.sha256(f"{GIT_COMMITTER_EMAIL}-{pub_ssh}".encode()).hexdigest()[:32]
    prefix = TOKEN_TYPES[token_type]
    secret_name = f"{prefix}-{wallet_id}"

    encoded_blob = _encrypt_payload(plaintext_key, x25519_pub)

    sm_client = boto3.client("secretsmanager", region_name=AWS_REGION)
    _store_secret(sm_client, secret_name, encoded_blob)

    return secret_name


def _get_wallet_id() -> str:
    """Compute the wallet ID from the user's email and Coder SSH public key."""
    ssh_keys = _fetch_git_ssh_key()
    pub_ssh = ssh_keys["public_key"].strip()
    return hashlib.sha256(f"{GIT_COMMITTER_EMAIL}-{pub_ssh}".encode()).hexdigest()[:32]


def _list_wallet_secrets() -> list[dict]:
    """Check which of the 4 possible secrets exist for this wallet.

    Returns a list of dicts with 'secret_name', 'prefix', and 'truncated' keys.
    """
    wallet_id = _get_wallet_id()
    sm_client = boto3.client("secretsmanager", region_name=AWS_REGION)
    found = []
    for token_type, prefix in TOKEN_TYPES.items():
        secret_name = f"{prefix}-{wallet_id}"
        try:
            resp = sm_client.describe_secret(SecretId=secret_name)
            if "DeletedDate" in resp:
                continue
            truncated = f"{prefix}-{wallet_id[:3]}..."
            found.append({
                "secret_name": secret_name,
                "prefix": prefix,
                "truncated": truncated,
                "token_type": token_type,
            })
        except sm_client.exceptions.ResourceNotFoundException:
            continue
    return found


def _validate_secret_ownership(secret_name: str) -> bool:
    """Verify a secret_name matches one of the expected patterns for this wallet."""
    wallet_id = _get_wallet_id()
    return any(
        secret_name == f"{prefix}-{wallet_id}"
        for prefix in TOKEN_TYPES.values()
    )


def _update_wallet_secret(secret_name: str, plaintext_key: str):
    """Re-encrypt a new value and store it under an existing secret name."""
    ssh_keys = _fetch_git_ssh_key()
    priv_openssh = ssh_keys["private_key"].strip()

    private_key_obj = serialization.load_ssh_private_key(priv_openssh.encode(), password=None)
    public_key_obj = private_key_obj.public_key()
    _, x25519_pub = _ed25519_to_x25519(private_key_obj, public_key_obj)

    encoded_blob = _encrypt_payload(plaintext_key, x25519_pub)

    sm_client = boto3.client("secretsmanager", region_name=AWS_REGION)
    sm_client.put_secret_value(SecretId=secret_name, SecretString=encoded_blob)


def _delete_wallet_secret(secret_name: str):
    """Permanently delete a secret from AWS Secrets Manager."""
    sm_client = boto3.client("secretsmanager", region_name=AWS_REGION)
    sm_client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)


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


def _key_row_html(secret: dict) -> str:
    """Render a single wallet-key row with Update / Delete actions."""
    sn = secret["secret_name"]
    return f"""<div class="flex items-center justify-between px-3.5 py-2.5 bg-[#12151b] border border-white/[0.07] rounded-[10px]">
            <span class="font-mono text-sm text-gray-200">{secret['truncated']}</span>
            <div class="flex gap-1.5">
                <button class="{_BTN_GHOST} !w-auto !py-1.5 !px-3 !text-xs" type="button"
                    hx-get="/update-key-form?secret_name={sn}"
                    hx-target="#connect-area"
                    hx-swap="outerHTML">Update</button>
                <button class="{_BTN_DANGER} !w-auto !py-1.5 !px-3 !text-xs" type="button"
                    hx-post="/delete-key"
                    hx-target="#connect-area"
                    hx-swap="outerHTML"
                    hx-vals='{{"secret_name":"{sn}"}}'
                    hx-confirm="Are you sure you want to delete {secret['truncated']}? This cannot be undone.">Delete</button>
            </div>
        </div>"""


def _actions_area_html(message: str = "", error: bool = False, keys: list[dict] | None = None) -> str:
    """HTML for the wallet actions area.

    Shows existing keys with per-key Update / Delete, or an empty-state prompt.
    """
    msg_html = ""
    if message:
        if error:
            msg_html = f'<p class="text-sm text-center px-3 py-2.5 rounded-[10px] text-red-400 bg-red-400/[0.12] mb-1">{message}</p>'
        else:
            msg_html = f'<p class="text-sm text-center px-3 py-2.5 rounded-[10px] text-emerald-400 bg-emerald-400/10 mb-1">{message}</p>'

    if keys is None:
        try:
            keys = _list_wallet_secrets()
        except Exception:
            keys = []

    if keys:
        rows = "\n".join(_key_row_html(k) for k in keys)
        body = f"""<div class="flex flex-col gap-1.5 mb-3">
            {rows}
        </div>"""
    else:
        body = f"""<div class="text-center py-6 mb-3">
            <p class="text-sm text-gray-400 mb-1">No wallet keys found</p>
            <p class="text-xs text-gray-500">Add a wallet key to get started.</p>
        </div>"""

    return f"""<div id="connect-area" class="flex flex-col gap-2 mt-1">
        {msg_html}
        {body}
        <button class="{_BTN}" type="button"
            hx-get="/add-key-form"
            hx-target="#connect-area"
            hx-swap="outerHTML"
            hx-indicator="#add-spinner"
            hx-disabled-elt="this">
            <span class="btn-text">Add Wallet Key</span>
            <span id="add-spinner" class="{_SPINNER}" aria-hidden="true"></span>
        </button>
    </div>"""


_TOKEN_LABELS = {
    "gitlab_token": "GitLab token",
    "jira_token": "JIRA token",
    "claude_token": "Claude token",
    "confluence_token": "Confluence token",
}


def _add_key_form_html(error: bool = False, error_msg: str = "") -> str:
    """HTML for the add key form, only showing token types not yet created."""
    try:
        existing = _list_wallet_secrets()
    except Exception:
        existing = []
    taken = {k["token_type"] for k in existing}
    available = {tt for tt in TOKEN_TYPES if tt not in taken}

    if not available:
        return f"""<div id="connect-area" class="mt-1">
            <div class="text-center py-6 mb-3">
                <p class="text-sm text-gray-400 mb-1">All token types are already configured</p>
                <p class="text-xs text-gray-500">Use Update to change an existing key.</p>
            </div>
            <button class="{_BTN_GHOST}" type="button" hx-get="/actions" hx-target="#connect-area" hx-swap="outerHTML">Back</button>
        </div>"""

    err = ""
    if error_msg:
        err = f'<p class="text-[0.78rem] text-red-400 bg-red-400/[0.12] px-3 py-2 rounded-[10px] mb-3">{error_msg}</p>'
    elif error:
        err = f'<p class="text-[0.78rem] text-red-400 bg-red-400/[0.12] px-3 py-2 rounded-[10px] mb-3">Failed to add key. Try again.</p>'

    radios = ""
    first = True
    for tt in TOKEN_TYPES:
        if tt not in available:
            continue
        req = " required" if first else ""
        first = False
        radios += f"""<label class="{_RADIO_OPTION}">
                    <input class="{_RADIO_INPUT}" type="radio" name="token_type" value="{tt}"{req} />
                    <span class="text-sm font-medium text-gray-200">{_TOKEN_LABELS[tt]}</span>
                </label>
"""

    return f"""<div id="connect-area" class="mt-1">
        {err}
        <form class="text-left" id="add-key-form" hx-post="/add-key" hx-target="#connect-area" hx-swap="outerHTML" hx-indicator="#submit-spinner" hx-disabled-elt="find button[type='submit']">
            <label class="{_LABEL}">Token type</label>
            <div class="flex flex-col gap-1.5 mb-4">
                {radios}
            </div>
            <div id="add-key-input-wrap" class="hidden">
                <label class="{_LABEL}" for="wallet-key">Key</label>
                <input class="{_INPUT}" id="wallet-key" name="key" type="text" placeholder="Enter your token" autocomplete="off" required />
            </div>
            <div class="flex gap-2 mt-2">
                <button class="{_BTN_GHOST} flex-1" type="button" hx-get="/actions" hx-target="#connect-area" hx-swap="outerHTML">
                    Cancel
                </button>
                <button class="{_BTN} flex-1" type="submit">
                    <span class="btn-text">Save key</span>
                    <span id="submit-spinner" class="{_SPINNER}" aria-hidden="true"></span>
                </button>
            </div>
        </form>
    </div>"""


def _update_key_form_html(secret_name: str, error: bool = False) -> str:
    """HTML for the update key form targeting a specific secret."""
    prefix = secret_name.split("-")[0]
    wallet_id_fragment = secret_name.split("-", 1)[1][:3]
    truncated = f"{prefix}-{wallet_id_fragment}..."
    err = f'<p class="text-[0.78rem] text-red-400 bg-red-400/[0.12] px-3 py-2 rounded-[10px] mb-3">Update failed. Try again.</p>' if error else ""
    return f"""<div id="connect-area" class="mt-1">
        {err}
        <form class="text-left" id="update-key-form" hx-post="/update-key" hx-target="#connect-area" hx-swap="outerHTML" hx-indicator="#update-submit-spinner" hx-disabled-elt="find button[type='submit']">
            <input type="hidden" name="secret_name" value="{secret_name}" />
            <p class="text-sm text-gray-400 mb-4">Updating <span class="font-mono text-gray-200">{truncated}</span></p>
            <label class="{_LABEL}" for="new-key">New key</label>
            <input class="{_INPUT}" id="new-key" name="key" type="text" placeholder="Enter new token value" autocomplete="off" required />
            <div class="flex gap-2 mt-2">
                <button class="{_BTN_GHOST} flex-1" type="button" hx-get="/actions" hx-target="#connect-area" hx-swap="outerHTML">
                    Cancel
                </button>
                <button class="{_BTN} flex-1" type="submit">
                    <span class="btn-text">Save</span>
                    <span id="update-submit-spinner" class="{_SPINNER}" aria-hidden="true"></span>
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
def get_update_key_form(secret_name: str):
    return _update_key_form_html(secret_name)


@app.post("/add-key", response_class=HTMLResponse)
def add_key(token_type: str = Form(...), key: str = Form(...)):
    if token_type not in TOKEN_TYPES:
        return HTMLResponse(_add_key_form_html(error=True), status_code=422)
    try:
        existing = _list_wallet_secrets()
        if any(k["token_type"] == token_type for k in existing):
            label = _TOKEN_LABELS[token_type]
            return HTMLResponse(
                _add_key_form_html(error_msg=f"A {label} already exists. Use Update instead."),
                status_code=422,
            )
        _create_wallet_secret(token_type, key)
        return _actions_area_html(message="Key added successfully.")
    except Exception:
        return HTMLResponse(_add_key_form_html(error=True), status_code=422)


@app.post("/update-key", response_class=HTMLResponse)
def update_key(secret_name: str = Form(...), key: str = Form(...)):
    try:
        if not _validate_secret_ownership(secret_name):
            return HTMLResponse(
                _update_key_form_html(secret_name, error=True), status_code=422
            )
        _update_wallet_secret(secret_name, key)
        return _actions_area_html(message="Key updated successfully.")
    except Exception:
        return HTMLResponse(
            _update_key_form_html(secret_name, error=True), status_code=422
        )


@app.post("/delete-key", response_class=HTMLResponse)
def delete_key(secret_name: str = Form(...)):
    try:
        if not _validate_secret_ownership(secret_name):
            return _actions_area_html(message="Delete failed. Try again.", error=True)
        _delete_wallet_secret(secret_name)
        return _actions_area_html(message="Key deleted successfully.")
    except Exception:
        return _actions_area_html(message="Delete failed. Try again.", error=True)


@app.get("/", response_class=HTMLResponse)
def index():
    email_cls = "text-gray-500 italic" if not GIT_COMMITTER_EMAIL else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wallet</title>
    <link rel="stylesheet" href="./vendor/css/fonts.css">
    <script src="./vendor/js/tailwindcss.js"></script>
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
    <script src="./vendor/js/htmx-2.0.4.min.js"></script>
    <script>
    document.addEventListener("htmx:beforeSwap", function(e) {{
        if (e.detail.xhr.status === 422) {{ e.detail.shouldSwap = true; }}
    }});
    document.addEventListener("change", function(e) {{
        if (e.target.matches('#add-key-form input[name="token_type"]')) {{
            document.getElementById('add-key-input-wrap').classList.remove('hidden');
            document.getElementById('wallet-key').required = true;
        }}
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
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-6 bg-[#090b0f] text-gray-200 font-sans">
    <div class="w-full max-w-[400px]">
        <h1 class="text-[1.75rem] font-bold tracking-tight text-center text-white mb-0.5">Wallet</h1>
        <p class="text-sm text-gray-500 text-center mb-8">Secure. Simple. Yours.</p>

        <div class="bg-white/[0.03] backdrop-blur-xl border border-white/[0.07] rounded-[14px] px-6 py-5 text-left mb-3">
            <div class="text-[0.65rem] font-semibold uppercase tracking-wider text-gray-500 mb-2">Email</div>
            <div class="font-mono text-sm break-all {email_cls}">{GIT_COMMITTER_EMAIL or "Not set"}</div>
        </div>

        {_actions_area_html()}

    </div>
</body>
</html>"""
