from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

HTML_CONTENT = '''
<!DOCTYPE html>
<html>
<head><title>CodeSnap AI</title></head>
<body>
<h1>CodeSnap AI is Running!</h1>
<p>Your backend is working.</p>
</body>
</html>
'''

@app.get("/")
async def root():
    return HTMLResponse(content=HTML_CONTENT)

@app.get("/health")
async def health():
    return {"status": "healthy"}
