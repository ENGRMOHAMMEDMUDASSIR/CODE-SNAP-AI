# backend/main.py - Complete with all 5 features
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import logging
import os
import json
from datetime import datetime

from backend.database import Database
from backend.auth import get_password_hash, verify_password, create_access_token, get_current_user, get_github_login_url, exchange_github_code
from backend.comparator import compare_repositories
from backend.pdf_export import generate_pdf_report
from backend.ai_explainer import AIExplainer
from backend.rate_limiter import setup_rate_limiting, check_user_rate_limit, check_ip_rate_limit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CodeSnap AI Pro", version="3.0.0")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup rate limiting
limiter = setup_rate_limiting(app)

security = HTTPBearer()
db = Database()
ai_explainer = AIExplainer()

# Pydantic models
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class RepoRequest(BaseModel):
    repo_url: str

class CompareRequest(BaseModel):
    repos: list

# ============ AUTHENTICATION ENDPOINTS ============

@app.post("/register")
@limiter.limit("30/minute")
async def register(request: Request, user: UserCreate):
    password_hash = get_password_hash(user.password)
    success = db.create_user(user.username, password_hash)
    if not success:
        raise HTTPException(status_code=400, detail="Username already exists")
    return {"message": "User created successfully"}

@app.post("/login")
@limiter.limit("30/minute")
async def login(request: Request, user: UserLogin):
    db_user = db.get_user(user.username)
    if not db_user or not verify_password(user.password, db_user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "username": user.username}

@app.get("/auth/github")
async def github_login():
    """Redirect to GitHub OAuth login page"""
    return RedirectResponse(url=get_github_login_url())

@app.get("/auth/github/callback")
async def github_callback(code: str):
    """Handle GitHub OAuth callback"""
    result = await exchange_github_code(code)
    return JSONResponse(content=result)

# ============ MAIN ANALYSIS ENDPOINT ============

@app.post("/analyze")
@limiter.limit("10/minute")  # Stricter limit for analysis
async def analyze_repo(request: Request, repo_req: RepoRequest, token: HTTPAuthorizationCredentials = Depends(security)):
    try:
        user = await get_current_user(token)
        
        # Check per-user rate limit
        check_user_rate_limit(user['id'], "analyze")
        
        repo_url = repo_req.repo_url
        
        # Check cache first
        cached = db.get_cached(repo_url)
        if cached:
            logger.info(f"Cache hit for {repo_url}")
            return JSONResponse(content=cached)
        
        # Parse URL
        parts = repo_url.rstrip('/').split('/')
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid GitHub URL")
        
        owner = parts[-2]
        repo = parts[-1]
        
        # Fetch from GitHub API
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {'User-Agent': 'CodeSnap-AI-Pro'}
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        response.raise_for_status()
        repo_data = response.json()
        
        language = repo_data.get("language") or "Unknown"
        
        # Get AI insights
        ai_insights = ai_explainer.analyze_repository_with_ai({
            "full_name": repo_data.get("full_name"),
            "description": repo_data.get("description"),
            "language": language,
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0)
        })
        
        # Generate analysis result
        result = {
            "repo_name": repo,
            "owner": owner,
            "full_name": repo_data.get("full_name", f"{owner}/{repo}"),
            "description": repo_data.get("description") or "No description provided",
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "language": language,
            "license": repo_data.get("license", {}).get("name") if repo_data.get("license") else "No license",
            "created_at": repo_data.get("created_at", "Unknown"),
            "updated_at": repo_data.get("updated_at", "Unknown"),
            "homepage": repo_data.get("homepage") or "No homepage",
            "url": repo_url,
            "architecture_pattern": ai_insights.get("architecture", "Standard Application"),
            "tech_stack": [language],
            "ai_insights": ai_insights,
            "analyzed_at": datetime.now().isoformat(),
            "ai_provider": ai_insights.get("provider", "mock")
        }
        
        # Save to cache
        db.save_cache(repo_url, result)
        
        # Save to user history
        db.save_history(user['id'], repo_url, result)
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ COMPARE REPOSITORIES ENDPOINT ============

@app.post("/compare")
@limiter.limit("10/minute")
async def compare_repos(request: Request, compare_req: CompareRequest, token: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(token)
    check_user_rate_limit(user['id'], "compare")
    
    repos_data = []
    for repo_url in compare_req.repos:
        cached = db.get_cached(repo_url)
        if cached:
            repos_data.append(cached)
        else:
            parts = repo_url.rstrip('/').split('/')
            owner, repo = parts[-2], parts[-1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {'User-Agent': 'CodeSnap-AI-Pro'}
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token:
                headers['Authorization'] = f'token {github_token}'
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                repos_data.append({
                    "full_name": data.get("full_name"),
                    "stars": data.get("stargazers_count", 0),
                    "forks": data.get("forks_count", 0),
                    "language": data.get("language", "Unknown"),
                    "open_issues": data.get("open_issues_count", 0)
                })
    
    comparison = compare_repositories(repos_data)
    db.save_comparison(user['id'], compare_req.repos, comparison)
    return JSONResponse(content=comparison)

# ============ PDF EXPORT ENDPOINT ============

@app.post("/export-pdf")
@limiter.limit("5/minute")
async def export_pdf(request: Request, repo_req: RepoRequest, token: HTTPAuthorizationCredentials = Depends(security)):
    await get_current_user(token)
    
    repo_url = repo_req.repo_url
    cached = db.get_cached(repo_url)
    
    if not cached:
        raise HTTPException(status_code=404, detail="Repository not analyzed yet")
    
    pdf_buffer = generate_pdf_report(cached, repo_url)
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={cached['repo_name']}_report.pdf"}
    )

# ============ AI EXPLANATION ENDPOINT ============

@app.post("/ai-explain")
@limiter.limit("10/minute")
async def ai_explain(request: Request, repo_req: RepoRequest, token: HTTPAuthorizationCredentials = Depends(security)):
    await get_current_user(token)
    
    repo_url = repo_req.repo_url
    cached = db.get_cached(repo_url)
    
    if not cached:
        raise HTTPException(status_code=404, detail="Repository not analyzed yet")
    
    explanation = ai_explainer.generate_onboarding(cached)
    return JSONResponse(content=explanation)

# ============ HISTORY ENDPOINT ============

@app.get("/history")
@limiter.limit("30/minute")
async def get_history(request: Request, token: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(token)
    history = db.get_history(user['id'])
    return JSONResponse(content=history)

# ============ HEALTH CHECK ============

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.0.0", "features": ["caching", "auth", "compare", "pdf", "ai", "rate_limiting", "social_login", "docker"]}

# ============ HTML FRONTEND (Same as before with social login button) ============

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>CodeSnap AI Pro</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; padding: 2rem; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { font-size: 2.5rem; margin-bottom: 0.5rem; background: linear-gradient(135deg, #58a6ff, #238636); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .feature-box { background: #161b22; padding: 25px; margin: 20px 0; border-radius: 12px; border: 1px solid #30363d; }
        .feature-box h2 { margin-bottom: 15px; color: #58a6ff; }
        input, textarea { padding: 10px; margin: 10px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: white; width: 300px; }
        textarea { width: 500px; }
        .btn { background: #238636; padding: 10px 20px; border: none; border-radius: 6px; color: white; cursor: pointer; margin: 5px; font-weight: 600; }
        .btn:hover { background: #2ea043; transform: translateY(-1px); }
        .btn-github { background: #333; }
        .btn-github:hover { background: #444; }
        pre { background: #010409; padding: 15px; border-radius: 8px; overflow-x: auto; margin-top: 15px; }
        .success { color: #2ea043; }
        .error { color: #f85149; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📸 CodeSnap AI Pro</h1>
        <p>Advanced GitHub Repository Analysis Platform with AI, Caching, Auth, PDF, Compare, Rate Limiting & Docker</p>
        
        <!-- Authentication Section -->
        <div class="feature-box">
            <h2>🔐 Authentication</h2>
            <input type="text" id="username" placeholder="Username">
            <input type="password" id="password" placeholder="Password">
            <button class="btn" onclick="register()">Register</button>
            <button class="btn" onclick="login()">Login</button>
            <button class="btn btn-github" onclick="githubLogin()">🔗 Login with GitHub</button>
            <div id="auth-status"></div>
        </div>
        
        <!-- Analysis Section -->
        <div class="feature-box">
            <h2>📊 Repository Analysis</h2>
            <input type="text" id="repo-url" placeholder="https://github.com/facebook/react" size="50">
            <button class="btn" onclick="analyze()">🔍 Analyze</button>
            <button class="btn" onclick="exportPDF()">📄 Export PDF</button>
            <button class="btn" onclick="aiExplain()">🤖 AI Explain</button>
            <div id="analysis-result"></div>
        </div>
        
        <!-- Comparison Section -->
        <div class="feature-box">
            <h2>🔍 Compare Repositories</h2>
            <textarea id="compare-urls" rows="3" cols="60" placeholder="https://github.com/facebook/react&#10;https://github.com/microsoft/vscode&#10;https://github.com/google/tensorflow"></textarea>
            <button class="btn" onclick="compareRepos()">📊 Compare</button>
            <div id="comparison-result"></div>
        </div>
        
        <!-- History Section -->
        <div class="feature-box">
            <h2>📜 Analysis History</h2>
            <button class="btn" onclick="getHistory()">View History</button>
            <div id="history-result"></div>
        </div>
    </div>
    
    <script>
        let authToken = localStorage.getItem('token');
        
        async function register() {
            const res = await fetch('/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: document.getElementById('username').value,
                    password: document.getElementById('password').value
                })
            });
            const data = await res.json();
            document.getElementById('auth-status').innerHTML = `<div class="${res.ok ? 'success' : 'error'}">${res.ok ? '✅ ' + data.message : '❌ ' + data.detail}</div>`;
        }
        
        async function login() {
            const res = await fetch('/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: document.getElementById('username').value,
                    password: document.getElementById('password').value
                })
            });
            const data = await res.json();
            if (data.access_token) {
                localStorage.setItem('token', data.access_token);
                authToken = data.access_token;
                document.getElementById('auth-status').innerHTML = '<div class="success">✅ Logged in as ' + data.username + '!</div>';
            } else {
                document.getElementById('auth-status').innerHTML = '<div class="error">❌ Login failed</div>';
            }
        }
        
        function githubLogin() {
            window.location.href = '/auth/github';
        }
        
        async function analyze() {
            const url = document.getElementById('repo-url').value;
            if (!url) { alert('Please enter a GitHub URL'); return; }
            if (!authToken) { alert('Please login first'); return; }
            
            document.getElementById('analysis-result').innerHTML = '<p>⏳ Analyzing repository...</p>';
            
            const res = await fetch('/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}`},
                body: JSON.stringify({repo_url: url})
            });
            const data = await res.json();
            document.getElementById('analysis-result').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        }
        
        async function exportPDF() {
            const url = document.getElementById('repo-url').value;
            if (!url) { alert('Please enter a GitHub URL'); return; }
            if (!authToken) { alert('Please login first'); return; }
            
            const res = await fetch('/export-pdf', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}`},
                body: JSON.stringify({repo_url: url})
            });
            const blob = await res.blob();
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'repository_analysis_report.pdf';
            link.click();
        }
        
        async function aiExplain() {
            const url = document.getElementById('repo-url').value;
            if (!url) { alert('Please enter a GitHub URL'); return; }
            if (!authToken) { alert('Please login first'); return; }
            
            const res = await fetch('/ai-explain', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}`},
                body: JSON.stringify({repo_url: url})
            });
            const data = await res.json();
            document.getElementById('analysis-result').innerHTML = `<pre>🤖 AI Analysis:\n${JSON.stringify(data, null, 2)}</pre>`;
        }
        
        async function compareRepos() {
            const urls = document.getElementById('compare-urls').value.split('\\n').filter(u => u.trim());
            if (urls.length < 2) { alert('Please enter at least 2 repository URLs'); return; }
            if (!authToken) { alert('Please login first'); return; }
            
            const res = await fetch('/compare', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}`},
                body: JSON.stringify({repos: urls})
            });
            const data = await res.json();
            document.getElementById('comparison-result').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        }
        
        async function getHistory() {
            if (!authToken) { alert('Please login first'); return; }
            
            const res = await fetch('/history', {
                headers: {'Authorization': `Bearer ${authToken}`}
            });
            const data = await res.json();
            document.getElementById('history-result').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        }
        
        // Check for token in URL (OAuth callback)
        if (window.location.hash) {
            // Handle OAuth callback if needed
        }
    </script>
</body>
</html>
'''

@app.get("/")
async def root():
    return HTMLResponse(content=HTML_PAGE)