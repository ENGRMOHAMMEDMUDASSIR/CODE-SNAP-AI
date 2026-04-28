# tests/test_github_fetcher.py
import pytest
import json
from unittest.mock import Mock, patch
from backend.github_fetcher import GitHubFetcher

@pytest.fixture
def fetcher():
    return GitHubFetcher()

@pytest.fixture
def mock_tree_response():
    return {
        "tree": [
            {"path": "main.py", "type": "blob", "size": 1024},
            {"path": "requirements.txt", "type": "blob", "size": 100},
            {"path": "src/app.js", "type": "blob", "size": 2048},
            {"path": "node_modules/pkg/index.js", "type": "blob", "size": 5000},
            {"path": "README.md", "type": "blob", "size": 500}
        ]
    }

def test_parse_github_url_valid(fetcher):
    owner, repo = fetcher.parse_github_url("https://github.com/facebook/react")
    assert owner == "facebook"
    assert repo == "react"

def test_parse_github_url_with_git_suffix(fetcher):
    owner, repo = fetcher.parse_github_url("https://github.com/twitter/bootstrap.git")
    assert owner == "twitter"
    assert repo == "bootstrap.git"

def test_parse_github_url_invalid(fetcher):
    with pytest.raises(ValueError):
        fetcher.parse_github_url("https://gitlab.com/user/repo")

def test_detect_tech_stack_python(fetcher, mock_tree_response):
    tech_stack = fetcher.detect_tech_stack(mock_tree_response["tree"])
    assert "Python" in tech_stack

def test_detect_tech_stack_javascript(fetcher):
    tree = [
        {"path": "package.json", "type": "blob"},
        {"path": "index.js", "type": "blob"}
    ]
    tech_stack = fetcher.detect_tech_stack(tree)
    assert "JavaScript/Node.js" in tech_stack

def test_detect_tech_stack_java(fetcher):
    tree = [
        {"path": "pom.xml", "type": "blob"},
        {"path": "src/Main.java", "type": "blob"}
    ]
    tech_stack = fetcher.detect_tech_stack(tree)
    assert "Java" in tech_stack

def test_detect_tech_stack_go(fetcher):
    tree = [
        {"path": "go.mod", "type": "blob"},
        {"path": "main.go", "type": "blob"}
    ]
    tech_stack = fetcher.detect_tech_stack(tree)
    assert "Go" in tech_stack

def test_detect_tech_stack_rust(fetcher):
    tree = [
        {"path": "Cargo.toml", "type": "blob"},
        {"path": "src/main.rs", "type": "blob"}
    ]
    tech_stack = fetcher.detect_tech_stack(tree)
    assert "Rust" in tech_stack

def test_filter_important_files_excludes_node_modules(fetcher, mock_tree_response):
    important = fetcher.filter_important_files(mock_tree_response["tree"])
    paths = [f["path"] for f in important]
    assert "node_modules/pkg/index.js" not in paths

def test_filter_important_files_includes_config(fetcher, mock_tree_response):
    important = fetcher.filter_important_files(mock_tree_response["tree"])
    paths = [f["path"] for f in important]
    assert "requirements.txt" in paths
    assert "README.md" in paths

def test_identify_entry_points(fetcher):
    tree = [
        {"path": "main.py", "type": "blob"},
        {"path": "src/app.js", "type": "blob"},
        {"path": "tests/test_main.py", "type": "blob"}
    ]
    entry_points = fetcher.identify_entry_points(tree)
    assert "main.py" in entry_points

@patch('requests.Session.get')
def test_fetch_repo_tree_success(mock_get, fetcher):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"tree": [{"path": "file.py"}]}
    mock_get.return_value = mock_response
    
    tree = fetcher.fetch_repo_tree("owner", "repo")
    assert len(tree) == 1

@patch('requests.Session.get')
def test_fetch_repo_tree_fallback_to_master(mock_get, fetcher):
    mock_response_404 = Mock()
    mock_response_404.status_code = 404
    
    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {"tree": []}
    
    mock_get.side_effect = [mock_response_404, mock_response_200]
    
    tree = fetcher.fetch_repo_tree("owner", "repo")
    assert mock_get.call_count == 2