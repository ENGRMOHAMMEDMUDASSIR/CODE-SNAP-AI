from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import requests
import logging
import os
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CodeSnap AI", version="1.0.0")

# HTML content with Mermaid.js integration
HTML_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeSnap AI - GitHub Repository Explainer</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
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
            max-width: 1400px;
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
        
        .tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid #30363d;
            flex-wrap: wrap;
        }
        
        .tab-btn {
            padding: 0.75rem 1.5rem;
            background: none;
            border: none;
            color: #8b949e;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        .tab-btn.active {
            color: #c9d1d9;
            border-bottom: 2px solid #238636;
        }
        
        .tab-content {
            display: none;
            animation: fadeIn 0.3s ease-in;
        }
        
        .tab-content.active {
            display: block;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
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
        
        .tech-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 1rem 0;
        }
        
        .tech-badge {
            background: #238636;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
        }
        
        .mermaid {
            background: #ffffff;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            text-align: center;
            overflow-x: auto;
        }
        
        .onboarding-step {
            background: #0d1117;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border-left: 3px solid #238636;
        }
        
        .step-title {
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #58a6ff;
        }
        
        .step-commands {
            background: #010409;
            padding: 0.75rem;
            border-radius: 6px;
            font-family: monospace;
            margin-top: 0.5rem;
            font-size: 0.875rem;
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
            
            <div id="results" style="display: none;">
                <div class="tabs">
                    <button class="tab-btn active" data-tab="overview">📋 Overview</button>
                    <button class="tab-btn" data-tab="diagram">📊 Architecture Diagram</button>
                    <button class="tab-btn" data-tab="onboarding">🚀 Onboarding Guide</button>
                    <button class="tab-btn" data-tab="tech">💻 Tech Stack</button>
                </div>
                
                <div id="overview" class="tab-content active"></div>
                <div id="diagram" class="tab-content">
                    <div class="repo-card">
                        <h3>📐 Repository Architecture</h3>
                        <div id="mermaid-diagram" class="mermaid"></div>
                    </div>
                </div>
                <div id="onboarding" class="tab-content">
                    <div class="repo-card">
                        <h3>📚 Developer Onboarding Guide</h3>
                        <div id="onboarding-content"></div>
                    </div>
                </div>
                <div id="tech" class="tab-content">
                    <div class="repo-card">
                        <h3>💻 Technology Stack</h3>
                        <div id="tech-content"></div>
                    </div>
                </div>
            </div>
            
            <div id="error-message" class="error" style="display: none;"></div>
        </div>
    </div>
    
    <script>
        mermaid.initialize({ startOnLoad: false, theme: 'dark' });
        let currentData = null;
        
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
            document.getElementById('results').style.display = 'none';
            
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
                
                currentData = data;
                displayResults(data);
                document.getElementById('results').style.display = 'block';
                
                // Render mermaid diagram
                if (data.architecture_diagram) {
                    const diagramElement = document.getElementById('mermaid-diagram');
                    diagramElement.textContent = data.architecture_diagram;
                    mermaid.contentLoaded();
                }
                
            } catch (error) {
                showError(error.message);
            } finally {
                showLoading(false);
            }
        };
        
        function displayResults(data) {
            // Overview Tab
            const overviewHtml = `
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
            document.getElementById('overview').innerHTML = overviewHtml;
            
            // Tech Stack Tab
            const techHtml = `
                <div class="info-item" style="margin-bottom: 1rem;">
                    <div class="info-label">Primary Language</div>
                    <div class="info-value" style="font-size: 1.5rem; color: #58a6ff;">${data.language || 'Unknown'}</div>
                </div>
                <div class="tech-badges">
                    ${data.tech_stack && data.tech_stack.length ? data.tech_stack.map(t => `<span class="tech-badge">${t}</span>`).join('') : '<span class="tech-badge">Analyzing...</span>'}
                </div>
                <div class="info-item" style="margin-top: 1rem;">
                    <div class="info-label">Architecture Pattern</div>
                    <div class="info-value">${data.architecture_pattern || 'Standard Application'}</div>
                </div>
            `;
            document.getElementById('tech-content').innerHTML = techHtml;
            
            // Onboarding Guide Tab
            let onboardingHtml = '';
            if (data.onboarding_guide && data.onboarding_guide.length) {
                data.onboarding_guide.forEach(step => {
                    onboardingHtml += `
                        <div class="onboarding-step">
                            <div class="step-title">${step.step}. ${step.title}</div>
                            <div>${step.description}</div>
                            ${step.commands ? `
                                <div class="step-commands">
                                    ${step.commands.map(cmd => `<div>$ ${cmd}</div>`).join('')}
                                </div>
                            ` : ''}
                        </div>
                    `;
                });
            } else {
                onboardingHtml = '<p>Generating onboarding guide...</p>';
            }
            document.getElementById('onboarding-content').innerHTML = onboardingHtml;
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
        
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.getElementById(tabId).classList.add('active');
            });
        });
        
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

def generate_architecture_diagram(language, repo_name):
    """Generate Mermaid.js architecture diagram based on language"""
    
    if language == "JavaScript" or language == "TypeScript":
        return """
graph TD
    A[Browser] --> B[React/Vue/Angular]
    B --> C[State Management]
    B --> D[API Client]
    D --> E[Backend APIs]
    C --> F[Redux/Context]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#bfb,stroke:#333,stroke-width:2px
"""
    elif language == "Python":
        return """
graph TD
    A[HTTP Request] --> B[FastAPI/Django/Flask]
    B --> C[Middleware]
    C --> D[Business Logic]
    D --> E[Database]
    D --> F[External APIs]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#bfb,stroke:#333,stroke-width:2px
"""
    elif language == "Java":
        return """
graph TD
    A[Client] --> B[Spring Boot]
    B --> C[Controller]
    C --> D[Service Layer]
    D --> E[Repository]
    E --> F[(Database)]
    D --> G[External Services]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#bfb,stroke:#333,stroke-width:2px
"""
    elif language == "Go":
        return """
graph TD
    A[HTTP Request] --> B[Gin/Echo]
    B --> C[Handlers]
    C --> D[Services]
    D --> E[Repository]
    E --> F[(Database)]
    D --> G[External APIs]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#bfb,stroke:#333,stroke-width:2px
"""
    else:
        return """
graph TD
    A[User] --> B[Application]
    B --> C[Core Logic]
    B --> D[Data Layer]
    D --> E[(Storage)]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#bfb,stroke:#333,stroke-width:2px
"""

def generate_onboarding_guide(language, repo_name):
    """Generate onboarding guide based on language"""
    
    guides = {
        "JavaScript": [
            {"step": 1, "title": "Clone the Repository", "description": "Get the code on your local machine", "commands": [f"git clone https://github.com/.../{repo_name}.git", f"cd {repo_name}"]},
            {"step": 2, "title": "Install Dependencies", "description": "Install Node.js packages", "commands": ["npm install", "yarn install"]},
            {"step": 3, "title": "Set Up Environment", "description": "Configure environment variables", "commands": ["cp .env.example .env", "Edit .env with your settings"]},
            {"step": 4, "title": "Run Development Server", "description": "Start the app locally", "commands": ["npm start", "npm run dev"]},
            {"step": 5, "title": "Run Tests", "description": "Verify everything works", "commands": ["npm test"]}
        ],
        "Python": [
            {"step": 1, "title": "Clone the Repository", "description": "Get the code on your local machine", "commands": [f"git clone https://github.com/.../{repo_name}.git", f"cd {repo_name}"]},
            {"step": 2, "title": "Create Virtual Environment", "description": "Isolate dependencies", "commands": ["python -m venv venv", "source venv/bin/activate  # On Windows: venv\\\\Scripts\\\\activate"]},
            {"step": 3, "title": "Install Dependencies", "description": "Install Python packages", "commands": ["pip install -r requirements.txt"]},
            {"step": 4, "title": "Set Up Environment", "description": "Configure environment variables", "commands": ["cp .env.example .env", "Edit .env with your settings"]},
            {"step": 5, "title": "Run the Application", "description": "Start the app", "commands": ["python main.py", "flask run", "uvicorn main:app --reload"]},
            {"step": 6, "title": "Run Tests", "description": "Verify everything works", "commands": ["pytest", "python -m unittest"]}
        ],
        "Java": [
            {"step": 1, "title": "Clone the Repository", "description": "Get the code on your local machine", "commands": [f"git clone https://github.com/.../{repo_name}.git", f"cd {repo_name}"]},
            {"step": 2, "title": "Build the Project", "description": "Compile using Maven/Gradle", "commands": ["./mvnw clean install", "./gradlew build"]},
            {"step": 3, "title": "Run the Application", "description": "Start the Spring Boot app", "commands": ["./mvnw spring-boot:run", "./gradlew bootRun"]},
            {"step": 4, "title": "Run Tests", "description": "Verify everything works", "commands": ["./mvnw test", "./gradlew test"]}
        ],
        "Go": [
            {"step": 1, "title": "Clone the Repository", "description": "Get the code on your local machine", "commands": [f"git clone https://github.com/.../{repo_name}.git", f"cd {repo_name}"]},
            {"step": 2, "title": "Download Dependencies", "description": "Get Go modules", "commands": ["go mod download"]},
            {"step": 3, "title": "Build the Application", "description": "Compile the binary", "commands": ["go build -o app ."]},
            {"step": 4, "title": "Run the Application", "description": "Start the server", "commands": ["./app", "go run main.go"]},
            {"step": 5, "title": "Run Tests", "description": "Verify everything works", "commands": ["go test ./..."]}
        ]
    }
    
    default_guide = [
        {"step": 1, "title": "Clone the Repository", "description": "Get the code on your local machine", "commands": [f"git clone https://github.com/.../{repo_name}.git", f"cd {repo_name}"]},
        {"step": 2, "title": "Check Documentation", "description": "Read the README for setup instructions", "commands": ["cat README.md", "Open README.md in your editor"]},
        {"step": 3, "title": "Install Dependencies", "description": "Install required packages based on the tech stack", "commands": ["Check package.json, requirements.txt, or go.mod"]},
        {"step": 4, "title": "Run the Application", "description": "Start the app following the README instructions", "commands": ["Follow the README for run commands"]},
        {"step": 5, "title": "Run Tests", "description": "Ensure everything works correctly", "commands": ["Check README for test commands"]}
    ]
    
    return guides.get(language, default_guide)

def detect_tech_stack(language):
    """Detect additional technologies based on primary language"""
    tech_stack = [language]
    
    if language == "JavaScript" or language == "TypeScript":
        tech_stack.append("Node.js")
        tech_stack.append("npm/yarn")
        tech_stack.append("Webpack/Babel")
    elif language == "Python":
        tech_stack.append("pip")
        tech_stack.append("Virtual Environment")
    elif language == "Java":
        tech_stack.append("JVM")
        tech_stack.append("Maven/Gradle")
    elif language == "Go":
        tech_stack.append("Go Modules")
    
    return tech_stack

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
        
        # Fetch repo info from GitHub API with authentication
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'CodeSnap-AI-App'
        }
        
        # Add GitHub token if available (increases rate limit to 5000/hour)
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            headers['Authorization'] = f'token {github_token}'
            logger.info("Using GitHub token for authentication")
        else:
            logger.info("No GitHub token found. Rate limit: 60 requests/hour. Add GITHUB_TOKEN for 5000/hour.")
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        if response.status_code == 403:
            error_msg = "API rate limit exceeded. "
            if not github_token:
                error_msg += "Add a GitHub token (GITHUB_TOKEN) in Render environment variables for 5000 requests/hour. "
            error_msg += "Please try again later."
            raise HTTPException(status_code=403, detail=error_msg)
        
        response.raise_for_status()
        repo_data = response.json()
        
        language = repo_data.get("language") or "Unknown"
        
        # Generate architecture diagram based on language
        architecture_diagram = generate_architecture_diagram(language, repo)
        
        # Generate onboarding guide
        onboarding_guide = generate_onboarding_guide(language, repo)
        
        # Detect tech stack
        tech_stack = detect_tech_stack(language)
        
        # Determine architecture pattern
        if "JavaScript" in language or "TypeScript" in language:
            architecture_pattern = "Frontend/Full-Stack Application"
        elif "Python" in language:
            architecture_pattern = "Backend API / Web Application"
        elif "Java" in language:
            architecture_pattern = "Enterprise Java Application"
        elif "Go" in language:
            architecture_pattern = "Microservices / API Gateway"
        else:
            architecture_pattern = "Standard Application Architecture"
        
        # Extract detailed information
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
            "architecture_diagram": architecture_diagram,
            "onboarding_guide": onboarding_guide,
            "tech_stack": tech_stack,
            "architecture_pattern": architecture_pattern,
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