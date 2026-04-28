# backend/ai_analyzer.py
import json
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        self.provider = "mock"  # No API key needed
        logger.info("Running in MOCK mode - no API key required")
    
    def analyze_repository(self, repo_name: str, repo_structure: Dict, 
                          important_files: List[Dict], tech_stack: List[str]) -> Dict[str, Any]:
        """Generate smart analysis without using any API"""
        
        # Generate intelligent folder explanations based on common patterns
        folder_explanations = {}
        for folder in repo_structure.keys():
            if folder in ['src', 'source', 'lib', 'app']:
                folder_explanations[folder] = f"Main source code directory containing the core application logic for {repo_name}."
            elif folder in ['test', 'tests', '__tests__', 'spec']:
                folder_explanations[folder] = "Unit and integration tests to ensure code reliability."
            elif folder in ['docs', 'documentation']:
                folder_explanations[folder] = "Project documentation and guides."
            elif folder in ['config', 'conf', 'settings']:
                folder_explanations[folder] = "Configuration files for environment setup."
            elif folder in ['public', 'static', 'assets']:
                folder_explanations[folder] = "Static assets like images, CSS, and frontend files."
            elif folder in ['api', 'routes', 'controllers']:
                folder_explanations[folder] = "API endpoints and routing logic."
            elif folder in ['models', 'entities', 'domain']:
                folder_explanations[folder] = "Data models and business logic entities."
            elif folder in ['utils', 'helpers', 'common']:
                folder_explanations[folder] = "Utility functions and shared helper code."
            else:
                folder_explanations[folder] = f"Contains files related to {folder} functionality."

        # Detect architecture pattern
        architecture_pattern = self._detect_architecture(repo_structure, tech_stack)
        
        # Generate onboarding guide
        onboarding_guide = self._generate_onboarding_guide(tech_stack, repo_name)
        
        # Explain key files
        key_files_explained = self._explain_key_files(important_files)
        
        return {
            "description": self._generate_description(repo_name, tech_stack),
            "folder_explanations": folder_explanations,
            "architecture_pattern": architecture_pattern,
            "suggested_entry_points": self._find_entry_points(important_files),
            "onboarding_guide": onboarding_guide,
            "key_files": key_files_explained
        }
    
    def _detect_architecture(self, repo_structure: Dict, tech_stack: List[str]) -> str:
        if any(f in str(repo_structure).lower() for f in ['frontend', 'ui', 'client']):
            if any(f in str(repo_structure).lower() for f in ['backend', 'api', 'server']):
                return "Full-Stack Application (Frontend + Backend)"
            return "Frontend Application"
        elif any(f in str(repo_structure).lower() for f in ['api', 'backend', 'server']):
            return "Backend API Service"
        elif 'micro' in str(repo_structure).lower():
            return "Microservices Architecture"
        else:
            return "Standard Application Architecture"
    
    def _generate_description(self, repo_name: str, tech_stack: List[str]) -> str:
        tech_str = ", ".join(tech_stack) if tech_stack else "various technologies"
        return f"{repo_name} is a software project built with {tech_str}. The repository follows standard development practices with organized code structure for maintainability and scalability."
    
    def _generate_onboarding_guide(self, tech_stack: List[str], repo_name: str) -> List[Dict]:
        guide = [
            {
                "step": 1,
                "title": "Clone the Repository",
                "description": "Get a copy of the code on your local machine",
                "commands": [f"git clone https://github.com/owner/{repo_name}.git", f"cd {repo_name}"]
            },
            {
                "step": 2,
                "title": "Install Dependencies",
                "description": "Install all required packages and libraries",
                "commands": []
            },
            {
                "step": 3,
                "title": "Configure Environment",
                "description": "Set up environment variables and configuration files",
                "commands": ["cp .env.example .env", "Edit .env with your settings"]
            },
            {
                "step": 4,
                "title": "Run the Application",
                "description": "Start the development server",
                "commands": []
            },
            {
                "step": 5,
                "title": "Run Tests (Optional)",
                "description": "Verify everything is working correctly",
                "commands": ["npm test" if "JavaScript" in tech_stack else "pytest" if "Python" in tech_stack else "./gradlew test"]
            }
        ]
        
        # Customize based on tech stack
        if "Python" in tech_stack:
            guide[1]["commands"] = ["pip install -r requirements.txt", "pip install -e ."]
            guide[3]["commands"] = ["python main.py", "python app.py", "flask run", "uvicorn main:app --reload"]
        elif "JavaScript/Node.js" in tech_stack or "TypeScript" in tech_stack:
            guide[1]["commands"] = ["npm install", "yarn install"]
            guide[3]["commands"] = ["npm start", "npm run dev", "yarn dev"]
        elif "Java" in tech_stack:
            guide[1]["commands"] = ["./mvnw install", "gradle build"]
            guide[3]["commands"] = ["./mvnw spring-boot:run", "java -jar target/*.jar"]
        elif "Go" in tech_stack:
            guide[1]["commands"] = ["go mod download"]
            guide[3]["commands"] = ["go run main.go", "go build && ./app"]
        else:
            guide[1]["commands"] = ["Check README.md for setup instructions"]
            guide[3]["commands"] = ["Check README.md for run instructions"]
        
        return guide
    
    def _explain_key_files(self, important_files: List[Dict]) -> Dict[str, str]:
        explanations = {}
        for file in important_files[:10]:  # Limit to 10 files
            path = file['path']
            if 'readme' in path.lower():
                explanations[path] = "Project documentation with setup and usage instructions."
            elif 'package.json' in path:
                explanations[path] = "Node.js dependencies and scripts configuration."
            elif 'requirements.txt' in path:
                explanations[path] = "Python dependencies list for the project."
            elif 'docker' in path.lower():
                explanations[path] = "Docker configuration for containerized deployment."
            elif '.env' in path:
                explanations[path] = "Environment variables configuration file."
            elif 'config' in path.lower():
                explanations[path] = "Application configuration settings."
            elif 'main' in path.lower() or 'app' in path.lower():
                explanations[path] = "Main entry point of the application."
            elif 'test' in path.lower():
                explanations[path] = "Test file containing unit or integration tests."
            else:
                explanations[path] = f"Contains code related to {path.split('/')[-1].replace('.', ' ')} functionality."
        
        if not explanations:
            explanations["README.md"] = "Check the README for project information."
        
        return explanations
    
    def _find_entry_points(self, important_files: List[Dict]) -> List[str]:
        priority = ['main.py', 'app.py', 'index.js', 'server.js', 'main.go', 'Main.java', 'Program.cs']
        for file in important_files:
            if file['path'] in priority:
                return [file['path']]
        return ["Check README.md or main application file"]