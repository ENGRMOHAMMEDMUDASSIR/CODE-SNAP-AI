# backend/ai_explainer.py
import os
import json
import logging

logger = logging.getLogger(__name__)

class AIExplainer:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.provider = "openai" if self.openai_key else "anthropic" if self.anthropic_key else "mock"
        
        if self.openai_key:
            try:
                import openai
                openai.api_key = self.openai_key
                logger.info("OpenAI initialized")
            except:
                pass
        
        logger.info(f"AI Provider: {self.provider}")
    
    def analyze_repository_with_ai(self, repo_data: dict) -> dict:
        """Use AI to analyze repository and provide insights"""
        
        prompt = f"""
        Analyze this GitHub repository and provide insights as JSON:
        
        Repository: {repo_data.get('full_name')}
        Description: {repo_data.get('description', 'No description')}
        Language: {repo_data.get('language', 'Unknown')}
        Stars: {repo_data.get('stars', 0)}
        Forks: {repo_data.get('forks', 0)}
        
        Return JSON with these exact fields:
        - architecture: description of the architecture pattern
        - onboarding_steps: list of 5 steps to onboard a new developer
        - key_files: list of 5 important files to understand
        - improvements: list of 3 potential improvements
        - complexity: rating from 1-10
        """
        
        if self.provider == "openai":
            return self._openai_analysis(prompt)
        elif self.provider == "anthropic":
            return self._anthropic_analysis(prompt)
        else:
            return self._mock_analysis(repo_data)
    
    def _openai_analysis(self, prompt: str) -> dict:
        try:
            import openai
            
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a senior software architect. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
                
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return self._mock_analysis({})
    
    def _anthropic_analysis(self, prompt: str) -> dict:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.anthropic_key)
            
            response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {"analysis": response.content[0].text, "provider": "anthropic"}
            
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            return self._mock_analysis({})
    
    def _mock_analysis(self, repo_data: dict) -> dict:
        language = repo_data.get('language', 'Unknown')
        return {
            "architecture": f"Standard {language} application architecture with modular components",
            "onboarding_steps": [
                "Clone the repository using git clone",
                "Install dependencies (npm install / pip install -r requirements.txt)",
                "Set up environment variables (.env file)",
                "Configure database (if applicable)",
                "Run the application (npm start / python main.py)"
            ],
            "key_files": [
                "README.md - Project documentation",
                f"main.{'js' if language in ['JavaScript', 'TypeScript'] else 'py'} - Entry point",
                "package.json / requirements.txt - Dependencies",
                ".env.example - Environment variables template",
                "docker-compose.yml - Container configuration"
            ],
            "improvements": [
                "Add more comprehensive unit tests",
                "Improve inline code documentation",
                "Set up CI/CD pipeline for automated testing"
            ],
            "complexity": "5",
            "provider": "mock"
        }
    
    def generate_onboarding(self, repo_data: dict) -> dict:
        """Generate AI-powered onboarding guide"""
        return self.analyze_repository_with_ai(repo_data)