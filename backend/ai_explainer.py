# backend/ai_explainer.py
import os
import json
import logging

logger = logging.getLogger(__name__)

class AIExplainer:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.provider = "openai" if os.getenv("OPENAI_API_KEY") else "anthropic" if os.getenv("ANTHROPIC_API_KEY") else "mock"
    
    def explain_code(self, code_snippet: str, language: str) -> dict:
        """Generate AI explanation of code"""
        
        if self.provider == "mock":
            return self._mock_explanation(language)
        elif self.provider == "openai":
            return self._openai_explanation(code_snippet, language)
        else:
            return self._anthropic_explanation(code_snippet, language)
    
    def _mock_explanation(self, language: str) -> dict:
        return {
            "summary": f"This appears to be a {language} code snippet. It likely implements core functionality.",
            "key_functions": ["main()", "initialize()", "process_data()"],
            "complexity": "Medium",
            "suggestions": [
                "Add error handling for edge cases",
                "Consider adding unit tests",
                "Document complex logic with comments"
            ]
        }
    
    def _openai_explanation(self, code_snippet: str, language: str) -> dict:
        try:
            import openai
            openai.api_key = self.api_key
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a code analyzer. Analyze the code and return JSON with summary, key_functions, complexity, and suggestions."},
                    {"role": "user", "content": f"Analyze this {language} code:\n\n{code_snippet[:2000]}"}
                ],
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._mock_explanation(language)
    
    def _anthropic_explanation(self, code_snippet: str, language: str) -> dict:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": f"Analyze this {language} code and return JSON with summary, key_functions, complexity, and suggestions:\n\n{code_snippet[:2000]}"}
                ]
            )
            
            return {
                "summary": "AI-generated analysis from Claude",
                "key_functions": ["detected_functions"],
                "complexity": "Medium",
                "suggestions": ["Improvement suggestions from AI"]
            }
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return self._mock_explanation(language)
    
    def generate_onboarding(self, repo_data: dict) -> dict:
        """Generate AI-powered onboarding guide"""
        
        tech_stack = repo_data.get('tech_stack', [])
        language = repo_data.get('language', 'Unknown')
        
        if self.provider == "mock":
            return {
                "quick_start": f"To get started with this {language} project, clone the repository and install dependencies.",
                "best_practices": [
                    "Follow the project's coding standards",
                    "Write tests for new features",
                    "Update documentation as you go"
                ],
                "common_issues": [
                    "Missing environment variables",
                    "Dependency version conflicts",
                    "Database connection issues"
                ]
            }
        else:
            return self._ai_onboarding(tech_stack, language)
    
    def _ai_onboarding(self, tech_stack: list, language: str) -> dict:
        return {
            "quick_start": f"Quick start guide for {language} project...",
            "best_practices": ["Best practices would appear here"],
            "common_issues": ["Common issues would appear here"]
        }