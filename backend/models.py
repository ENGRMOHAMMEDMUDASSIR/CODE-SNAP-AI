# backend/models.py
from pydantic import BaseModel, HttpUrl, Field, validator
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class RepoRequest(BaseModel):
    repo_url: HttpUrl = Field(..., description="Public GitHub repository URL")
    
    @validator('repo_url')
    def validate_github_url(cls, v):
        if 'github.com' not in str(v):
            raise ValueError('URL must be a valid GitHub repository URL')
        return v

class RepoResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

class FileInfo(BaseModel):
    path: str
    type: str
    size: Optional[int] = None
    url: Optional[str] = None

class AnalysisResult(BaseModel):
    id: Optional[int] = None
    repo_name: str
    repo_url: str
    description: str
    tech_stack: List[str]
    folder_structure_explanation: Dict[str, str]
    architecture_diagram: str
    key_files_explained: Dict[str, str]
    onboarding_guide: List[Dict[str, Any]]
    entry_points: List[str]
    dependencies: Dict[str, List[str]]
    architecture_pattern: str
    analyzed_at: Optional[datetime] = None

class CacheEntry(BaseModel):
    repo_url: str
    analysis_data: Dict[str, Any]
    created_at: datetime
    expires_at: datetime