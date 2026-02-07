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
    <title>Hello World</title>
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
</head>
<body>
    <h1>Hello World</h1>
    <p>GIT_COMMITTER_EMAIL: {GIT_COMMITTER_EMAIL or "(not set)"}</p>
    <p>CODER_WORKSPACE_ID: {CODER_WORKSPACE_ID or "(not set)"}</p>
</body>
</html>"""