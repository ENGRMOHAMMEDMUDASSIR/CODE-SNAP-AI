# backend/github_fetcher.py
import requests
import re
from typing import Dict, List, Tuple, Optional, Set
from urllib.parse import urlparse
from backend.config import config

class GitHubFetcher:
    IGNORED_DIRS = {'node_modules', '.git', 'dist', 'build', '__pycache__', '.venv', 'env', 'target'}
    IMPORTANT_EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.cpp', '.c', '.h', '.cs', '.php', '.rb'}
    
    def __init__(self):
        self.session = requests.Session()
        if config.GITHUB_TOKEN:
            self.session.headers.update({'Authorization': f'token {config.GITHUB_TOKEN}'})
        self.session.headers.update({'Accept': 'application/vnd.github.v3+json'})
    
    def parse_github_url(self, url: str) -> Tuple[str, str]:
        """Extract owner and repo name from GitHub URL"""
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2:
            return path_parts[0], path_parts[1]
        raise ValueError("Invalid GitHub URL format")
    
    def fetch_repo_tree(self, owner: str, repo: str, branch: str = 'main') -> List[Dict]:
        """Fetch complete repository tree using GitHub API"""
        url = f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        
        # Try main branch first, then master
        for try_branch in [branch, 'master']:
            try_url = url.replace(branch, try_branch)
            response = self.session.get(try_url)
            if response.status_code == 200:
                data = response.json()
                return data.get('tree', [])
            elif response.status_code == 404:
                continue
            else:
                response.raise_for_status()
        
        raise Exception(f"Could not access repository: {owner}/{repo}")
    
    def fetch_file_content(self, owner: str, repo: str, path: str, branch: str = 'main') -> Optional[str]:
        """Fetch content of a specific file"""
        url = f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        params = {'ref': branch}
        
        response = self.session.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('encoding') == 'base64':
                import base64
                return base64.b64decode(data['content']).decode('utf-8', errors='ignore')
        return None
    
    def detect_tech_stack(self, tree: List[Dict]) -> List[str]:
        """Detect technology stack based on repository files"""
        tech_stack = set()
        file_paths = [item['path'] for item in tree if item['type'] == 'blob']
        
        # Python detection
        if any('requirements.txt' in f or 'setup.py' in f or 'pyproject.toml' in f or f.endswith('.py') for f in file_paths):
            tech_stack.add("Python")
        
        # JavaScript/TypeScript detection
        if any('package.json' in f for f in file_paths):
            tech_stack.add("JavaScript/Node.js")
        if any(f.endswith('.ts') or f.endswith('.tsx') for f in file_paths):
            tech_stack.add("TypeScript")
        
        # Java detection
        if any('pom.xml' in f or 'build.gradle' in f or f.endswith('.java') for f in file_paths):
            tech_stack.add("Java")
        
        # Go detection
        if any('go.mod' in f or f.endswith('.go') for f in file_paths):
            tech_stack.add("Go")
        
        # Rust detection
        if any('Cargo.toml' in f or f.endswith('.rs') for f in file_paths):
            tech_stack.add("Rust")
        
        # C++ detection
        if any(f.endswith(('.cpp', '.hpp', '.cc')) for f in file_paths):
            tech_stack.add("C++")
        
        # PHP detection
        if any(f.endswith('.php') or 'composer.json' in f for f in file_paths):
            tech_stack.add("PHP")
        
        # Ruby detection
        if any('Gemfile' in f or f.endswith('.rb') for f in file_paths):
            tech_stack.add("Ruby")
        
        # Framework detection
        if any('react' in f.lower() or 'vue' in f.lower() or 'angular' in f.lower() for f in file_paths):
            tech_stack.add("Frontend Framework")
        if any('django' in f.lower() or 'flask' in f.lower() or 'fastapi' in f.lower() for f in file_paths):
            tech_stack.add("Python Web Framework")
        if any('spring' in f.lower() for f in file_paths):
            tech_stack.add("Spring Framework")
        
        return list(tech_stack) if tech_stack else ["Unknown"]
    
    def identify_entry_points(self, tree: List[Dict]) -> List[str]:
        """Identify main entry point files"""
        entry_points = []
        priority_files = ['main.py', 'app.py', 'index.js', 'server.js', 'main.go', 'src/main.rs', 
                         'Main.java', 'Program.cs', 'index.php', 'app.rb']
        
        for item in tree:
            if item['type'] == 'blob':
                path = item['path']
                if path in priority_files or path.endswith('/main.py') or path.endswith('/app.js'):
                    entry_points.append(path)
        
        return entry_points[:5]  # Limit to top 5
    
    def filter_important_files(self, tree: List[Dict], limit: int = 20) -> List[Dict]:
        """Filter out ignored directories and return important files"""
        important_files = []
        
        for item in tree:
            if item['type'] != 'blob':
                continue
            
            path = item['path']
            # Skip ignored directories
            if any(ignored in path.split('/') for ignored in self.IGNORED_DIRS):
                continue
            
            # Prioritize certain file types
            if any(path.endswith(ext) for ext in self.IMPORTANT_EXTENSIONS):
                important_files.append(item)
            
            # Also include config files
            config_files = ['package.json', 'requirements.txt', 'Dockerfile', 'docker-compose.yml', 
                          'README.md', '.env.example', 'config.py', 'settings.py']
            if any(path.endswith(cf) for cf in config_files):
                important_files.append(item)
        
        # Return unique and limit
        seen = set()
        unique_files = []
        for f in important_files:
            if f['path'] not in seen:
                seen.add(f['path'])
                unique_files.append(f)
        
        return unique_files[:limit]