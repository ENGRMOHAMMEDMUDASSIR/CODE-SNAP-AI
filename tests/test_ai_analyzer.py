# tests/test_ai_analyzer.py
import pytest
import json
from unittest.mock import Mock, patch
from backend.ai_analyzer import AIAnalyzer
from backend.config import config

@pytest.fixture
def analyzer():
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        config.AI_PROVIDER = 'openai'
        return AIAnalyzer()

@pytest.fixture
def sample_repo_structure():
    return {
        "src": ["main.py", "utils.py"],
        "tests": ["test_main.py"],
        "docs": ["README.md"]
    }

@pytest.fixture
def sample_important_files():
    return [
        {"path": "main.py", "type": "blob"},
        {"path": "requirements.txt", "type": "blob"}
    ]

def test_fallback_analysis_on_failure(analyzer, sample_repo_structure, sample_important_files):
    with patch.object(analyzer, '_init_client', side_effect=Exception("API Error")):
        result = analyzer.analyze_repository(
            "test-repo", 
            sample_repo_structure, 
            sample_important_files, 
            ["Python"]
        )
        
        assert "description" in result
        assert "onboarding_guide" in result
        assert len(result["onboarding_guide"]) >= 3

def test_fallback_returns_valid_json_structure(analyzer):
    fallback = analyzer._get_fallback_analysis("test-repo", ["Python"])
    
    expected_keys = ["description", "folder_explanations", "architecture_pattern", 
                    "suggested_entry_points", "onboarding_guide", "key_files"]
    
    for key in expected_keys:
        assert key in fallback

@patch('openai.OpenAI')
def test_openai_successful_analysis(mock_openai_class, analyzer, sample_repo_structure, sample_important_files):
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps({
        "description": "Test description",
        "folder_explanations": {"/src": "Source code"},
        "architecture_pattern": "MVC",
        "suggested_entry_points": ["main.py"],
        "onboarding_guide": [{"step": 1, "title": "Install", "description": "Run pip install"}],
        "key_files": {"main.py": "Entry point"}
    })
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai_class.return_value = mock_client
    
    analyzer.client = mock_client
    
    result = analyzer.analyze_repository("test", sample_repo_structure, sample_important_files, ["Python"])
    
    assert result["description"] == "Test description"
    assert result["architecture_pattern"] == "MVC"