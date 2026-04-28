from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CodeSnap AI", version="1.0.0")

# HTML content (same as before)
HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>CodeSnap AI</title>
    <style>
        body{font-family:Arial;background:#0d1117;color:#c9d1d9;padding:2rem;text-align:center}
        input,button{padding:10px;margin:10px;border-radius:5px}
        .btn-primary{background:#238636;color:white;border:none;cursor:pointer}
        .url-input{width:400px}
        .result{text-align:left;background:#161b22;padding:20px;border-radius:10px;margin-top:20px}
        .loading{display:none;color:#8b949e}
    </style>
</head>
<body>
    <h1>📸 CodeSnap AI</h1>
    <p>GitHub Repository Explainer & Onboarding Assistant</p>
    <input type="url" id="repo-url" placeholder="https://github.com/facebook/react" class="url-input">
    <button id="analyze-btn" class="btn-primary">🔍 Analyze Repository</button>
    <div id="loading" class="loading">⏳ Analyzing repository...</div>
    <div id="result" class="result"></div>
    
    <script>
        document.getElementById('analyze-btn').onclick = async function() {
            const url = document.getElementById('repo-url').value;
            if (!url) { alert('Please enter a GitHub URL'); return; }
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').innerHTML = '';
            
            try {
                const res = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({repo_url: url})
                });
                const data = await res.json();
                document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch(e) {
                document.getElementById('result').innerHTML = '<p style="color:red">Error: ' + e.message + '</p>';
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        };
    </script>
</body>
</html>
'''

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=HTML_PAGE)

@app.post("/analyze")
async def analyze_repo(repo_req: dict):
    try:
        repo_url = repo_req.get('repo_url')
        if not repo_url:
            raise HTTPException(status_code=400, detail="repo_url required")
        
        # Extract owner and repo from URL
        parts = repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo = parts[-1]
        
        # Fetch repo info from GitHub API
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(api_url)
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        repo_data = response.json()
        
        result = {
            "repo_name": repo,
            "owner": owner,
            "description": repo_data.get("description", "No description"),
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "language": repo_data.get("language", "Unknown"),
            "url": repo_url,
            "status": "success"
        }
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "CodeSnap AI"}
