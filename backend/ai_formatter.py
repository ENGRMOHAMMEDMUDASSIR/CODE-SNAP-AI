# backend/ai_formatter.py
import os
import json
import logging

logger = logging.getLogger(__name__)

class AIFormatter:
    """AI-powered formatting suggestions for code snippets"""
    
    LANGUAGE_THEMES = {
        "Python": {
            "theme": "monokai",
            "font": "Fira Code",
            "font_size": 14,
            "background": "#1e1e2e",
            "line_numbers": True,
            "suggestions": [
                "Use snake_case for variables",
                "Add type hints for better readability",
                "Follow PEP 8 guidelines"
            ]
        },
        "JavaScript": {
            "theme": "vs2015",
            "font": "Source Code Pro", 
            "font_size": 14,
            "background": "#2d2d2d",
            "line_numbers": True,
            "suggestions": [
                "Use const/let instead of var",
                "Add semicolons consistently",
                "Use arrow functions where appropriate"
            ]
        },
        "TypeScript": {
            "theme": "vs2015",
            "font": "Source Code Pro",
            "font_size": 14,
            "background": "#2d2d2d",
            "line_numbers": True,
            "suggestions": [
                "Define proper interfaces",
                "Use strict type checking",
                "Avoid using 'any' type"
            ]
        },
        "Java": {
            "theme": "eclipse",
            "font": "Consolas",
            "font_size": 14,
            "background": "#1e1e1e",
            "line_numbers": True,
            "suggestions": [
                "Follow camelCase naming",
                "Use meaningful class names",
                "Add Javadoc comments"
            ]
        },
        "HTML": {
            "theme": "vs2015",
            "font": "JetBrains Mono",
            "font_size": 14,
            "background": "#252526",
            "line_numbers": False,
            "suggestions": [
                "Use semantic HTML5 tags",
                "Add alt attributes to images",
                "Ensure proper indentation"
            ]
        },
        "CSS": {
            "theme": "vs2015",
            "font": "JetBrains Mono",
            "font_size": 14,
            "background": "#252526",
            "line_numbers": False,
            "suggestions": [
                "Use CSS variables for consistency",
                "Follow BEM naming convention",
                "Add responsive media queries"
            ]
        },
        "SQL": {
            "theme": "default",
            "font": "Fira Code",
            "font_size": 14,
            "background": "#1e1e2e",
            "line_numbers": True,
            "suggestions": [
                "Use uppercase for keywords",
                "Add proper indexing",
                "Format queries for readability"
            ]
        },
        "Go": {
            "theme": "monokai",
            "font": "Fira Code",
            "font_size": 14,
            "background": "#1e1e2e",
            "line_numbers": True,
            "suggestions": [
                "Follow Go naming conventions",
                "Use error handling properly",
                "Keep functions small"
            ]
        },
        "Rust": {
            "theme": "monokai",
            "font": "Fira Code",
            "font_size": 14,
            "background": "#1e1e2e",
            "line_numbers": True,
            "suggestions": [
                "Use proper error handling with Result",
                "Follow Rust ownership rules",
                "Add documentation tests"
            ]
        }
    }
    
    TEMPLATES = {
        "default": {
            "name": "Default - GitHub Style",
            "description": "Clean, professional look inspired by GitHub",
            "layout": "standard",
            "show_metadata": True,
            "show_line_numbers": True
        },
        "tutorial": {
            "name": "Tutorial - Step by Step",
            "description": "Step-by-step guide format with numbered sections",
            "layout": "steps",
            "show_metadata": True,
            "show_line_numbers": True,
            "include_explanations": True
        },
        "social": {
            "name": "Social - Twitter/LinkedIn Ready",
            "description": "Optimized for social media sharing",
            "layout": "compact",
            "show_metadata": False,
            "show_line_numbers": False,
            "max_width": "600px"
        },
        "presentation": {
            "name": "Presentation - Slide Friendly",
            "description": "Large text, slide-friendly format",
            "layout": "fullscreen",
            "show_metadata": True,
            "show_line_numbers": True,
            "font_size": 18
        }
    }
    
    def get_formatting_suggestions(self, language: str, code_snippet: str = "") -> dict:
        theme_config = self.LANGUAGE_THEMES.get(language, {
            "theme": "default",
            "font": "monospace",
            "font_size": 14,
            "background": "#0d1117",
            "line_numbers": True,
            "suggestions": ["Use consistent indentation", "Add comments for complex logic"]
        })
        
        extra_suggestions = self._analyze_code_snippet(code_snippet, language)
        
        return {
            "language": language,
            "theme": theme_config["theme"],
            "font": theme_config["font"],
            "font_size": theme_config["font_size"],
            "background": theme_config["background"],
            "line_numbers": theme_config["line_numbers"],
            "suggestions": theme_config["suggestions"] + extra_suggestions,
            "ai_provider": "mock"
        }
    
    def _analyze_code_snippet(self, code: str, language: str) -> list:
        suggestions = []
        if not code:
            return suggestions
        
        if language == "Python":
            if "print(" in code and "def " not in code:
                suggestions.append("Consider wrapping code in functions for reusability")
            if "except:" in code:
                suggestions.append("Specify exception types instead of bare except")
            if len(code.split('\n')) > 50:
                suggestions.append("Consider splitting this code into multiple files")
        elif language == "JavaScript":
            if "var " in code:
                suggestions.append("Replace 'var' with 'const' or 'let'")
            if "== " in code and "===" not in code:
                suggestions.append("Use strict equality (===) instead of loose equality (==)")
        
        if len(code.split('\n')) > 100:
            suggestions.append("This file is quite long. Consider refactoring into smaller modules")
        
        return suggestions
    
    def apply_template(self, template_name: str, content: dict) -> dict:
        template = self.TEMPLATES.get(template_name, self.TEMPLATES["default"])
        return {
            "template": template,
            "formatted_content": self._render_template(template, content)
        }
    
    def _render_template(self, template: dict, content: dict) -> str:
        if template["layout"] == "steps":
            return self._render_step_template(content)
        elif template["layout"] == "compact":
            return self._render_compact_template(content)
        elif template["layout"] == "fullscreen":
            return self._render_fullscreen_template(content)
        else:
            return self._render_standard_template(content)
    
    def _render_standard_template(self, content: dict) -> str:
        return f"""
        <div class="code-block">
            <div class="code-header">
                <span class="language">{content.get('language', 'Code')}</span>
                <span class="filename">{content.get('filename', 'snippet')}</span>
            </div>
            <pre><code>{content.get('code', '')}</code></pre>
        </div>
        """
    
    def _render_step_template(self, content: dict) -> str:
        steps = content.get('steps', [])
        steps_html = ""
        for i, step in enumerate(steps, 1):
            steps_html += f"""
            <div class="tutorial-step">
                <div class="step-number">{i}</div>
                <div class="step-content">
                    <h4>{step.get('title', f'Step {i}')}</h4>
                    <p>{step.get('description', '')}</p>
                    <pre><code>{step.get('code', '')}</code></pre>
                </div>
            </div>
            """
        return steps_html
    
    def _render_compact_template(self, content: dict) -> str:
        return f"""
        <div style="font-family: monospace; font-size: 12px; padding: 10px;">
            <pre style="margin: 0; white-space: pre-wrap;"><code>{content.get('code', '')}</code></pre>
        </div>
        """
    
    def _render_fullscreen_template(self, content: dict) -> str:
        return f"""
        <div style="width: 100%; min-height: 100vh; display: flex; align-items: center; justify-content: center;">
            <div style="max-width: 1200px; width: 100%; padding: 40px;">
                <h1>{content.get('title', 'Code Presentation')}</h1>
                <pre style="font-size: 18px; line-height: 1.6;"><code>{content.get('code', '')}</code></pre>
            </div>
        </div>
        """

formatter = AIFormatter()