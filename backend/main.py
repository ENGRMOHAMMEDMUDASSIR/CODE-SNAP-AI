# backend/main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import logging
import json
import sqlite3
from pathlib import Path
from datetime import datetime

from backend.config import config
from backend.models import RepoRequest
from backend.github_fetcher import GitHubFetcher
from backend.ai_analyzer import AIAnalyzer
from backend.diagram_generator import DiagramGenerator
from backend.cache_manager import CacheManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="CodeSnap AI", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
github_fetcher = GitHubFetcher()
ai_analyzer = AIAnalyzer()
diagram_generator = DiagramGenerator()
cache_manager = CacheManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CodeSnap AI starting...")
    cache_manager.clear_expired()
    yield
    logger.info("CodeSnap AI shutting down...")

app.router.lifespan_context = lifespan

# HTML content directly in the code
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeSnap AI - GitHub Repository Explainer</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0d1117;color:#c9d1d9;line-height:1.5;}
        .container{max-width:1200px;margin:0 auto;padding:2rem;}
        header{text-align:center;margin-bottom:3rem;}
        header h1{font-size:2.5rem;margin-bottom:0.5rem;}
        .input-section{display:flex;gap:1rem;margin-bottom:2rem;}
        .url-input{flex:1;padding:0.75rem 1rem;background:#161b22;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;font-size:1rem;}
        .btn-primary{padding:0.75rem 1.5rem;background:#238636;border:none;border-radius:6px;color:white;font-weight:600;cursor:pointer;}
        .btn-primary:hover{background:#2ea043;}
        .loading{text-align:center;padding:2rem;color:#8b949e;}
        .results{margin-top:2rem;}
        .repo-header{background:#161b22;padding:1.5rem;border-radius:6px;margin-bottom:1.5rem;}
        .tech-badges{display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:0.5rem;}
        .tech-badge{background:#21262d;padding:0.25rem 0.75rem;border-radius:2rem;font-size:0.75rem;}
        .tabs{display:flex;gap:0.5rem;border-bottom:1px solid #30363d;margin-bottom:1.5rem;}
        .tab-btn{padding:0.5rem 1rem;background:none;border:none;color:#8b949e;cursor:pointer;font-size:1rem;}
        .tab-btn.active{color:#c9d1d9;border-bottom:2px solid #238636;}
        .tab-content{display:none;padding:1rem 0;}
        .tab-content.active{display:block;}
        .mermaid{background:white;padding:1rem;border-radius:6px;text-align:center;color:black;}
        .onboarding-step{background:#161b22;padding:1rem;border-radius:6px;margin-bottom:1rem;}
        .step-title{font-weight:600;margin-bottom:0.5rem;}
        .step-commands{background:#010409;padding:0.75rem;border-radius:6px;font-family:monospace;margin-top:0.5rem;}
        .error{background:rgba(248,81,73,0.1);border:1px solid #f85149;padding:1rem;border-radius:6px;color:#f85149;}
        .hidden{display:none;}
        .folder-item{background:#161b22;padding:0.75rem;border-radius:6px;margin-bottom:0.5rem;}
        @media(max-width:768px){.container{padding:1rem;}.input-section{flex-direction:column;}}
    </style>
</head>
<body>
    <div class="container">
        <header><h1>📸 CodeSnap AI</h1><p>GitHub Repository Explainer & Onboarding Assistant</p></header>
        <div class="main-content">
            <div class="input-section">
                <input type="url" id="repo-url" placeholder="https://github.com/owner/repo" class="url-input">
                <button id="analyze-btn" class="btn-primary">🔍 Analyze Repository</button>
                <div id="loading" class="loading hidden">Analyzing repository structure...</div>
            </div>
            <div id="results" class="results hidden">
                <div class="repo-header"><h2 id="repo-name"></h2><div id="tech-stack" class="tech-badges"></div></div>
                <div class="tabs">
                    <button class="tab-btn active" data-tab="overview">📋 Overview</button>
                    <button class="tab-btn" data-tab="diagram">📊 Architecture</button>
                    <button class="tab-btn" data-tab="onboarding">🚀 Onboarding Guide</button>
                    <button class="tab-btn" data-tab="files">📁 Key Files</button>
                </div>
                <div id="overview" class="tab-content active"><div id="description"></div><div id="folder-structure"></div></div>
                <div id="diagram" class="tab-content"><div id="mermaid-diagram" class="mermaid"></div></div>
                <div id="onboarding" class="tab-content"><div id="onboarding-steps"></div></div>
                <div id="files" class="tab-content"><div id="key-files"></div><div id="entry-points"></div></div>
            </div>
            <div id="error-message" class="error hidden"></div>
        </div>
    </div>
    <script>
        mermaid.initialize({startOnLoad:false,theme:'default'});
        document.getElementById('analyze-btn').onclick=()=>analyze();
        document.getElementById('repo-url').onkeypress=e=>{if(e.key==='Enter')analyze();};
        async function analyze(){
            const url=document.getElementById('repo-url').value.trim();
            if(!url){alert('Enter GitHub URL');return;}
            document.getElementById('loading').classList.remove('hidden');
            try{
                const res=await fetch('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({repo_url:url})});
                const data=await res.json();
                if(!res.ok)throw new Error(data.detail);
                display(data.data);
            }catch(e){alert(e.message);}
            finally{document.getElementById('loading').classList.add('hidden');}
        }
        function display(d){
            document.getElementById('results').classList.remove('hidden');
            document.getElementById('repo-name').innerText=d.repo_name;
            document.getElementById('tech-stack').innerHTML=d.tech_stack.map(t=>`<span class="tech-badge">${t}</span>`).join('');
            document.getElementById('description').innerHTML=`<h3>📖 Description</h3><p>${d.description}</p><p><strong>Architecture:</strong> ${d.architecture_pattern}</p>`;
            let fs='<h3>📁 Folder Structure</h3>';
            for(const[f,ex]of Object.entries(d.folder_structure_explanation))fs+=`<div class="folder-item"><strong>${f}</strong><p>${ex}</p></div>`;
            document.getElementById('folder-structure').innerHTML=fs;
            document.getElementById('mermaid-diagram').innerHTML=d.architecture_diagram.replace(/```mermaid|```/g,'');
            mermaid.contentLoaded();
            let guide='<h3>🚀 Onboarding Guide</h3>';
            d.onboarding_guide.forEach(s=>{guide+=`<div class="onboarding-step"><div class="step-title">${s.step}. ${s.title}</div><div>${s.description}</div>${s.commands?`<div class="step-commands">${s.commands.map(c=>`$ ${c}`).join('<br>')}</div>`:''}</div>`;});
            document.getElementById('onboarding-steps').innerHTML=guide;
            let keys='<h3>📄 Key Files</h3>';
            for(const[f,ex]of Object.entries(d.key_files_explained))keys+=`<div class="onboarding-step"><strong>${f}</strong><p>${ex}</p></div>`;
            document.getElementById('key-files').innerHTML=keys;
            document.getElementById('entry-points').innerHTML=`<h3>🎯 Entry Points</h3><div class="onboarding-step"><p>Start here: <strong>${d.entry_points.join(', ')||'README.md'}</strong></p></div>`;
            const btns=document.querySelectorAll('.tab-btn');
            btns.forEach((b,i)=>{
                b.onclick=()=>{
                    btns.forEach(x=>x.classList.remove('active'));
                    b.classList.add('active');
                    document.querySelectorAll('.tab-content').forEach((c,j)=>{
                        c.classList.toggle('active',i===j);
                    });
                };
            });
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return HTMLResponse(content=HTML_PAGE)

@app.post("/analyze")
@limiter.limit(f"{config.RATE_LIMIT_REQUESTS}/minute")
async def analyze_repo(request: Request, repo_req: RepoRequest):
    try:
        repo_url = str(repo_req.repo_url)
        
        cached = cache_manager.get_cached(repo_url)
        if cached:
            return JSONResponse(content={"status": "success", "data": cached, "cached": True})
        
        owner, repo = github_fetcher.parse_github_url(repo_url)
        tree = github_fetcher.fetch_repo_tree(owner, repo)
        
        tech_stack = github_fetcher.detect_tech_stack(tree)
        entry_points = github_fetcher.identify_entry_points(tree)
        important_files = github_fetcher.filter_important_files(tree)
        
        folder_structure = {}
        for item in tree:
            if '/' in item['path']:
                folder = item['path'].split('/')[0]
                if folder not in folder_structure:
                    folder_structure[folder] = []
                folder_structure[folder].append(item['path'])
        
        ai_analysis = ai_analyzer.analyze_repository(
            repo, folder_structure, important_files, tech_stack
        )
        
        diagram = diagram_generator.generate_mermaid_diagram(folder_structure, tech_stack)
        
        result = {
            "repo_name": repo,
            "repo_url": repo_url,
            "description": ai_analysis.get("description", f"Analysis of {repo}"),
            "tech_stack": tech_stack,
            "folder_structure_explanation": ai_analysis.get("folder_explanations", {}),
            "architecture_diagram": diagram,
            "key_files_explained": ai_analysis.get("key_files", {}),
            "onboarding_guide": ai_analysis.get("onboarding_guide", []),
            "entry_points": entry_points or ai_analysis.get("suggested_entry_points", []),
            "dependencies": {"runtime": [], "dev": []},
            "architecture_pattern": ai_analysis.get("architecture_pattern", "Standard"),
            "analyzed_at": datetime.now().isoformat()
        }
        
        cache_manager.save_analysis(repo_url, result)
        
        return JSONResponse(content={"status": "success", "data": result, "cached": False})
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "CodeSnap AI"}

@app.get("/history")
async def get_history(request: Request):
    try:
        with sqlite3.connect(config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT repo_url, analysis_data, created_at 
                   FROM analyses 
                   WHERE expires_at > datetime('now') 
                   ORDER BY created_at DESC 
                   LIMIT 50"""
            )
            rows = cursor.fetchall()
            
            history = []
            for row in rows:
                data = json.loads(row['analysis_data'])
                history.append({
                    "repo_url": row['repo_url'],
                    "repo_name": data.get('repo_name', 'Unknown'),
                    "tech_stack": data.get('tech_stack', []),
                    "description": data.get('description', ''),
                    "analyzed_at": row['created_at']
                })
            
            return JSONResponse(content={"status": "success", "data": history})
    
    except Exception as e:
        logger.error(f"History fetch failed: {e}")
        return JSONResponse(content={"status": "success", "data": []})

@app.delete("/history")
async def delete_history(request: Request):
    try:
        body = await request.json()
        repo_url = body.get('repo_url')
        
        if not repo_url:
            raise HTTPException(status_code=400, detail="repo_url required")
        
        repo_hash = cache_manager._get_repo_hash(repo_url)
        
        with sqlite3.connect(config.DATABASE_PATH) as conn:
            conn.execute("DELETE FROM analyses WHERE repo_hash = ?", (repo_hash,))
        
        return JSONResponse(content={"status": "success", "message": "Deleted"})
    
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))