# backend/main.py - Complete with all features
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
from backend.rate_limiter import setup_rate_limiting, check_user_rate_limit, check_ip_rate_limit, trial_manager
from backend.ai_formatter import formatter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CodeSnap AI Pro", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = setup_rate_limiting(app)
security = HTTPBearer()
db = Database()
ai_explainer = AIExplainer()

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
    return RedirectResponse(url=get_github_login_url())

@app.get("/auth/github/callback")
async def github_callback(code: str):
    result = await exchange_github_code(code)
    return JSONResponse(content=result)

# ============ MAIN ANALYSIS ENDPOINT ============

@app.post("/analyze")
@limiter.limit("10/minute")
async def analyze_repo(request: Request, repo_req: RepoRequest, token: HTTPAuthorizationCredentials = Depends(security)):
    try:
        user = await get_current_user(token)
        check_user_rate_limit(user['id'], "analyze")
        
        repo_url = repo_req.repo_url
        cached = db.get_cached(repo_url)
        if cached:
            logger.info(f"Cache hit for {repo_url}")
            return JSONResponse(content=cached)
        
        parts = repo_url.rstrip('/').split('/')
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid GitHub URL")
        
        owner = parts[-2]
        repo = parts[-1]
        
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
        
        ai_insights = ai_explainer.analyze_repository_with_ai({
            "full_name": repo_data.get("full_name"),
            "description": repo_data.get("description"),
            "language": language,
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0)
        })
        
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
        
        db.save_cache(repo_url, result)
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

# ============ NEW ENDPOINTS FOR FORMATTING & TEMPLATES ============

@app.post("/api/formatting-suggestions")
@limiter.limit("30/minute")
async def get_formatting_suggestions(request: Request, data: dict, token: HTTPAuthorizationCredentials = Depends(security)):
    await get_current_user(token)
    language = data.get('language', 'Python')
    code_snippet = data.get('code', '')
    suggestions = formatter.get_formatting_suggestions(language, code_snippet)
    return JSONResponse(content=suggestions)

@app.post("/api/apply-template")
@limiter.limit("30/minute")
async def apply_template(request: Request, data: dict, token: HTTPAuthorizationCredentials = Depends(security)):
    await get_current_user(token)
    template_name = data.get('template', 'default')
    content = data.get('content', {})
    result = formatter.apply_template(template_name, content)
    return JSONResponse(content=result)

@app.get("/api/templates")
@limiter.limit("60/minute")
async def get_templates(request: Request):
    return JSONResponse(content={
        "templates": formatter.TEMPLATES,
        "default": "default"
    })

@app.get("/api/language-themes")
@limiter.limit("60/minute")
async def get_language_themes(request: Request):
    return JSONResponse(content={
        "themes": formatter.LANGUAGE_THEMES,
        "languages": list(formatter.LANGUAGE_THEMES.keys())
    })

@app.post("/api/trial/grant")
@limiter.limit("5/minute")
async def grant_trial(request: Request, token: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(token)
    expiry = trial_manager.grant_trial(str(user['id']))
    return JSONResponse(content={
        "message": "Trial pack granted! 7 days of premium features.",
        "expires_at": expiry.isoformat(),
        "remaining_days": 7
    })

@app.get("/api/trial/status")
@limiter.limit("30/minute")
async def get_trial_status(request: Request, token: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(token)
    has_trial = trial_manager.has_trial(str(user['id']))
    remaining_days = trial_manager.get_trial_remaining(str(user['id']))
    return JSONResponse(content={
        "has_trial": has_trial,
        "remaining_days": remaining_days,
        "features": ["premium_rate_limits", "advanced_templates", "priority_support"]
    })

@app.get("/api/rate-limit-status")
@limiter.limit("60/minute")
async def get_rate_limit_status(request: Request, token: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(token)
    return JSONResponse(content={
        "free_tier": {
            "requests_per_minute": 100,
            "requests_per_day": 1000
        },
        "premium_tier": {
            "requests_per_minute": 500,
            "requests_per_day": 10000
        },
        "current_plan": "free",
        "upgrade_url": "/pricing"
    })

# ============ HEALTH CHECK ============

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.0.0", "features": ["caching", "auth", "compare", "pdf", "ai", "rate_limiting", "social_login", "docker", "formatting", "templates", "trial_packs"]}

# ============ HTML FRONTEND (Complete with new UI) ============

HTML_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeSnap AI Pro - GitHub Repository Explainer</title>
    <link rel="stylesheet" href="/static/css/themes.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 2rem; transition: background 0.3s ease, color 0.3s ease; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { font-size: 2.5rem; margin-bottom: 0.5rem; background: linear-gradient(135deg, #58a6ff, #238636); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .feature-box { padding: 25px; margin: 20px 0; border-radius: 12px; border: 1px solid; transition: all 0.3s ease; }
        input, textarea { padding: 10px; margin: 10px; border-radius: 6px; border: 1px solid; width: 300px; }
        textarea { width: 500px; }
        .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; margin: 5px; font-weight: 600; transition: transform 0.2s ease; }
        .btn:hover { transform: translateY(-1px); }
        pre { padding: 15px; border-radius: 8px; overflow-x: auto; margin-top: 15px; }
        .success { color: #2ea043; }
        .error { color: #f85149; }
        
        body.light-theme .btn { background: #0969da; color: white; }
        body.light-theme .btn:hover { background: #0550ae; }
        body.dark-theme .btn { background: #238636; color: white; }
        body.dark-theme .btn:hover { background: #2ea043; }
        
        .loading { text-align: center; padding: 2rem; }
        .loader { display: inline-block; width: 40px; height: 40px; border: 3px solid; border-radius: 50%; border-top-color: #238636; animation: spin 0.8s ease-in-out infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>📸 CodeSnap AI Pro</h1>
        <p>Advanced GitHub Repository Analysis Platform with AI, Caching, Auth, PDF, Compare, Rate Limiting, Formatting & Templates</p>
        
        <!-- Authentication Section -->
        <div class="feature-box">
            <h2>🔐 Authentication</h2>
            <input type="text" id="username" placeholder="Username">
            <input type="password" id="password" placeholder="Password">
            <button class="btn" onclick="register()">Register</button>
            <button class="btn" onclick="login()">Login</button>
            <button class="btn" onclick="githubLogin()">🔗 Login with GitHub</button>
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
        
        <!-- Formatting Controls Section -->
        <div class="feature-box">
            <h2>🎨 Formatting & Templates</h2>
            <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                <select id="template-select" class="url-input" style="width: auto;">
                    <option value="default">📄 Default - GitHub Style</option>
                    <option value="tutorial">📚 Tutorial - Step by Step</option>
                    <option value="social">🐦 Social - Twitter/LinkedIn</option>
                    <option value="presentation">📊 Presentation - Slide Friendly</option>
                </select>
                <button class="btn" onclick="applyTemplate()">Apply Template</button>
                <button class="btn" onclick="exportAsImage()">📸 Export as PNG</button>
                <button class="btn" onclick="shareToSocial()">🔗 Share</button>
            </div>
            <div id="formatting-preview" style="margin-top: 15px;"></div>
        </div>
        
        <!-- Theme Controls -->
        <div class="feature-box">
            <h2>🎨 Theme Settings</h2>
            <div style="display: flex; gap: 10px;">
                <button class="btn" onclick="setTheme('dark')">🌙 Dark</button>
                <button class="btn" onclick="setTheme('light')">☀️ Light</button>
                <button class="btn" onclick="setTheme('auto')">🔄 Auto (System)</button>
            </div>
            <div style="margin-top: 10px;">
                <label>Code Font:</label>
                <select id="font-select" onchange="changeFont(this.value)">
                    <option value="Fira Code">Fira Code</option>
                    <option value="Source Code Pro">Source Code Pro</option>
                    <option value="JetBrains Mono">JetBrains Mono</option>
                    <option value="Consolas">Consolas</option>
                </select>
            </div>
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
        
        <!-- Trial Pack Info -->
        <div class="feature-box" id="trial-box">
            <h2>🎁 Free Trial Pack</h2>
            <p>New users get 7 days of premium features!</p>
            <button class="btn" onclick="activateTrial()">Activate Free Trial</button>
            <div id="trial-status"></div>
        </div>
    </div>
    
    <div id="loading" class="loading" style="display: none;">
        <div class="loader"></div>
        <p>Processing...</p>
    </div>
    
    <script src="/static/js/theme.js"></script>
    <script>
        let authToken = localStorage.getItem('token');
        
        function showLoading(show) {
            document.getElementById('loading').style.display = show ? 'block' : 'none';
        }
        
        function showNotification(message, type) {
            const notification = document.createElement('div');
            notification.textContent = message;
            notification.style.cssText = `
                position: fixed; bottom: 20px; right: 20px; padding: 12px 24px;
                background: ${type === 'success' ? '#238636' : '#f85149'};
                color: white; border-radius: 8px; z-index: 10000;
                animation: fadeInOut 3s ease;
            `;
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 3000);
        }
        
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
                checkTrialStatus();
            } else {
                document.getElementById('auth-status').innerHTML = '<div class="error">❌ Login failed</div>';
            }
        }
        
        function githubLogin() { window.location.href = '/auth/github'; }
        
        async function analyze() {
            const url = document.getElementById('repo-url').value;
            if (!url) { alert('Please enter a GitHub URL'); return; }
            if (!authToken) { alert('Please login first'); return; }
            showLoading(true);
            try {
                const res = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}`},
                    body: JSON.stringify({repo_url: url})
                });
                const data = await res.json();
                document.getElementById('analysis-result').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            } catch(e) { showNotification(e.message, 'error'); }
            finally { showLoading(false); }
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
            const res = await fetch('/history', { headers: {'Authorization': `Bearer ${authToken}`} });
            const data = await res.json();
            document.getElementById('history-result').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        }
        
        function setTheme(theme) {
            if (theme === 'dark') {
                document.body.classList.add('dark-theme');
                document.body.classList.remove('light-theme');
                localStorage.setItem('codeSnapTheme', 'dark');
            } else if (theme === 'light') {
                document.body.classList.add('light-theme');
                document.body.classList.remove('dark-theme');
                localStorage.setItem('codeSnapTheme', 'light');
            } else if (theme === 'auto') {
                localStorage.removeItem('codeSnapTheme');
                if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
                    document.body.classList.add('dark-theme');
                    document.body.classList.remove('light-theme');
                } else {
                    document.body.classList.add('light-theme');
                    document.body.classList.remove('dark-theme');
                }
            }
        }
        
        function changeFont(fontName) {
            const codeBlocks = document.querySelectorAll('pre code');
            codeBlocks.forEach(block => { block.style.fontFamily = fontName; });
            localStorage.setItem('codeFont', fontName);
        }
        
        async function applyTemplate() {
            const template = document.getElementById('template-select').value;
            const repoUrl = document.getElementById('repo-url').value;
            if (!repoUrl) { alert('Please analyze a repository first'); return; }
            if (!authToken) { alert('Please login first'); return; }
            showLoading(true);
            try {
                const res = await fetch('/api/apply-template', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}`},
                    body: JSON.stringify({
                        template: template,
                        content: { code: document.getElementById('analysis-result')?.innerText || '', language: 'code' }
                    })
                });
                const data = await res.json();
                document.getElementById('formatting-preview').innerHTML = data.formatted_content || 'Template applied!';
            } catch(e) { console.error(e); }
            finally { showLoading(false); }
        }
        
        async function exportAsImage() {
            const element = document.getElementById('analysis-result');
            if (!element || !element.innerText) { alert('Please analyze a repository first'); return; }
            if (typeof html2canvas === 'undefined') {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
                document.head.appendChild(script);
                await new Promise(resolve => script.onload = resolve);
            }
            try {
                const canvas = await html2canvas(element);
                const link = document.createElement('a');
                link.download = 'codesnap-snippet.png';
                link.href = canvas.toDataURL();
                link.click();
                showNotification('Export successful!', 'success');
            } catch(e) { showNotification('Export failed', 'error'); }
        }
        
        function shareToSocial() {
            const content = document.getElementById('analysis-result')?.innerText || '';
            const encoded = encodeURIComponent(content.substring(0, 280));
            window.open(`https://twitter.com/intent/tweet?text=${encoded}%20via%20@CodeSnapAI`, '_blank');
        }
        
        async function activateTrial() {
            if (!authToken) { alert('Please login first to activate trial'); return; }
            const res = await fetch('/api/trial/grant', { method: 'POST', headers: { 'Authorization': `Bearer ${authToken}` } });
            const data = await res.json();
            document.getElementById('trial-status').innerHTML = `<div class="success">✅ ${data.message}</div>`;
        }
        
        async function checkTrialStatus() {
            if (!authToken) return;
            const res = await fetch('/api/trial/status', { headers: { 'Authorization': `Bearer ${authToken}` } });
            const data = await res.json();
            if (data.has_trial) {
                document.getElementById('trial-status').innerHTML = `✨ Trial active! ${data.remaining_days} days remaining`;
            }
        }
        
        const savedFont = localStorage.getItem('codeFont');
        if (savedFont && document.getElementById('font-select')) {
            document.getElementById('font-select').value = savedFont;
        }
        
        checkTrialStatus();
    </script>
</body>
</html>
'''

@app.get("/")
async def root():
    return HTMLResponse(content=HTML_PAGE)