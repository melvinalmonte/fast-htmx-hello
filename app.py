from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def index():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hello World</title>
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
</head>
<body>
    <h1>Hello World</h1>
    <button hx-get="/greeting" hx-target="#greeting" hx-swap="innerHTML">Click me</button>
    <div id="greeting"></div>
</body>
</html>"""


@app.get("/greeting", response_class=HTMLResponse)
def greeting():
    return "<p>Hello from HTMX!</p>"
