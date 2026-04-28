from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CodeSnap AI", version="1.0.0")

# HTML content with enhanced UI
HTML_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeSnap AI - GitHub Repository Explainer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            line-height: 1.5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        header {
            text-align: center;
            margin-bottom: 3rem;
        }
        
        header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #58a6ff, #238636);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        header p {
            color: #8b949e;
        }
        
        .input-section {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .url-input {
            flex: 1;
            padding: 0.75rem 1rem;
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            color: #c9d1d9;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        .url-input:focus {
            outline: none;
            border-color: #238636;
            box-shadow: 0 0 0 3px rgba(35, 134, 54, 0.1);
        }
        
        .btn-primary {
            padding: 0.75rem 1.5rem;
            background: #238636;
            border: none;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .btn-primary:hover {
            background: #2ea043;
            transform: translateY(-1px);
        }
        
        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: #8b949e;
        }
        
        .loader {
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 3px solid #30363d;
            border-radius: 50%;
            border-top-color: #238636;
            animation: spin 0.8s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .result {
            margin-top: 2rem;
            animation: fadeIn 0.5s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .repo-card {
            background: #161b22;
            border-radius: 12px;
            padding: 2rem;
            border: 1px solid #30363d;
        }
        
        .repo-header {
            border-bottom: 1px solid #30363d;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .repo-header h2 {
            font-size: 1.8rem;
            margin-bottom: 0.5rem;
        }
        
        .repo-stats {
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
            margin: 1.5rem 0;
            padding: 1rem;
            background: #0d1117;
            border-radius: 8px;
        }
        
        .stat {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #58a6ff;
        }
        
        .stat-label {
            color: #8b949e;
            font-size: 0.875rem;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0;
        }
        
        .info-item {
            padding: 0.75rem;
            background: #0d1117;
            border-radius: 6px;
        }
        
        .info-label {
            color: #8b949e;
            font-size: 0.75rem;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }
        
        .info-value {
            font-weight: 500;
        }
        
        a {
            color: #58a6ff;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        .error {
            background: rgba(248, 81, 73, 0.1);
            border: 1px solid #f85149;
            padding: 1rem;
            border-radius: 8px;
            color: #f85149;
            margin-top: 1rem;
        }
        
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .input-section { flex-direction: column; }
            .repo-stats { gap: 1rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📸 CodeSnap AI</h1>
            <p>GitHub Repository Explainer & Onboarding Assistant</p>
        </header>
        
        <div class="main-content">
            <div class="input-section">
                <input type="url" id="repo-url" placeholder="https://github.com/facebook/react" class="url-input">
                <button id="analyze-btn" class="btn-primary">🔍 Analyze Repository</button>
            </div>
            
            <div id="loading" class="loading" style="display: none;">
                <div class="loader"></div>
                <p style="margin-top: 1rem;">Analyzing repository structure...</p>
            </div>
            
            <div id="result" class="result" style="display: none;"></div>
            <div id="error-message" class="error" style="display: none;"></div>
        </div>
    </div>
    
    <script>
        document.getElementById('analyze-btn').onclick = async function() {
            const url = document.getElementById('repo-url').value.trim();
            if (!url) {
                showError('Please enter a GitHub repository URL');
                return;
            }
            
            if (!url.includes('github.com')) {
                showError('Please enter a valid GitHub URL');
                return;
            }
            
            showLoading(true);
            hideError();
            hideResult();
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({repo_url: url})
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.detail || 'Analysis failed');
                }
                
                displayResults(data);
                
            } catch (error) {
                showError(error.message);
            } finally {
                showLoading(false);
            }
        };
        
        function displayResults(data) {
            const resultDiv = document.getElementById('result');
            
            const statsHtml = `
                <div class="repo-card">
                    <div class="repo-header">
                        <h2>📦 ${data.full_name}</h2>
                        <p>${data.description || 'No description provided'}</p>
                    </div>
                    
                    <div class="repo-stats">
                        <div class="stat">
                            <span class="stat-value">${formatNumber(data.stars)}</span>
                            <span class="stat-label">⭐ Stars</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">${formatNumber(data.forks)}</span>
                            <span class="stat-label">🍴 Forks</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">${formatNumber(data.open_issues)}</span>
                            <span class="stat-label">⚠️ Open Issues</span>
                        </div>
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">💻 Primary Language</div>
                            <div class="info-value">${data.language || 'Unknown'}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">📜 License</div>
                            <div class="info-value">${data.license || 'No license'}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">📅 Created</div>
                            <div class="info-value">${formatDate(data.created_at)}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">🔄 Last Updated</div>
                            <div class="info-value">${formatDate(data.updated_at)}</div>
                        </div>
                    </div>
                    
                    ${data.homepage && data.homepage !== 'No homepage' ? `
                    <div class="info-item" style="margin-top: 1rem;">
                        <div class="info-label">🌐 Homepage</div>
                        <div class="info-value"><a href="${data.homepage}" target="_blank">${data.homepage}</a></div>
                    </div>
                    ` : ''}
                    
                    <div class="info-item" style="margin-top: 1rem;">
                        <div class="info-label">🔗 GitHub URL</div>
                        <div class="info-value"><a href="${data.url}" target="_blank">${data.url}</a></div>
                    </div>
                </div>
            `;
            
            resultDiv.innerHTML = statsHtml;
            resultDiv.style.display = 'block';
        }
        
        function formatNumber(num) {
            if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
            if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
            return num.toString();
        }
        
        function formatDate(dateString) {
            if (!dateString || dateString === 'Unknown') return 'Unknown';
            return new Date(dateString).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        }
        
        function showLoading(show) {
            const loadingDiv = document.getElementById('loading');
            const analyzeBtn = document.getElementById('analyze-btn');
            
            if (show) {
                loadingDiv.style.display = 'block';
                analyzeBtn.disabled = true;
                analyzeBtn.textContent = '⏳ Analyzing...';
            } else {
                loadingDiv.style.display = 'none';
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = '🔍 Analyze Repository';
            }
        }
        
        function showError(message) {
            const errorDiv = document.getElementById('error-message');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, 5000);
        }
        
        function hideError() {
            document.getElementById('error-message').style.display = 'none';
        }
        
        function hideResult() {
            document.getElementById('result').style.display = 'none';
        }
        
        // Allow Enter key to submit
        document.getElementById('repo-url').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                document.getElementById('analyze-btn').click();
            }
        });
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
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid GitHub URL format")
        
        owner = parts[-2]
        repo = parts[-1]
        
        # Fetch repo info from GitHub API
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'CodeSnap-AI-App'
        }
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        if response.status_code == 403:
            raise HTTPException(status_code=403, detail="API rate limit exceeded. Please try again later.")
        
        response.raise_for_status()
        repo_data = response.json()
        
        # Extract detailed information
        result = {
            "repo_name": repo,
            "owner": owner,
            "full_name": repo_data.get("full_name", f"{owner}/{repo}"),
            "description": repo_data.get("description") or "No description provided",
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "language": repo_data.get("language") or "Unknown",
            "license": repo_data.get("license", {}).get("name") if repo_data.get("license") else "No license",
            "created_at": repo_data.get("created_at", "Unknown"),
            "updated_at": repo_data.get("updated_at", "Unknown"),
            "homepage": repo_data.get("homepage") or "No homepage",
            "url": repo_url,
            "status": "success"
        }
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch repository data: {str(e)}")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "CodeSnap AI", "version": "1.0.0"}