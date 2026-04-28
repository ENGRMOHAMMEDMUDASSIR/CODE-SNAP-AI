# backend/diagram_generator.py
from typing import Dict, List, Set

class DiagramGenerator:
    def generate_mermaid_diagram(self, repo_structure: Dict, tech_stack: List[str]) -> str:
        """Generate Mermaid.js architecture diagram"""
        
        # Detect architecture pattern
        is_frontend = any(fw in str(tech_stack).lower() for fw in ['react', 'vue', 'angular', 'frontend'])
        is_backend = any(bk in str(tech_stack).lower() for bk in ['django', 'flask', 'express', 'spring', 'fastapi'])
        
        if is_frontend and is_backend:
            return self._generate_fullstack_diagram(repo_structure)
        elif is_frontend:
            return self._generate_frontend_diagram(repo_structure)
        elif is_backend:
            return self._generate_backend_diagram(repo_structure)
        else:
            return self._generate_simple_tree_diagram(repo_structure)
    
    def _generate_fullstack_diagram(self, structure: Dict) -> str:
        return """```mermaid
graph TD
    A[Client Browser] --> B[Frontend App]
    B --> C[API Gateway]
    C --> D[Backend Services]
    D --> E[Database]
    D --> F[External APIs]
    
    subgraph "Frontend"
        B1[UI Components]
        B2[State Management]
        B3[Routing]
    end
    
    subgraph "Backend"
        D1[Business Logic]
        D2[Authentication]
        D3[Data Processing]
    end
    
    B -.-> B1
    B -.-> B2
    B -.-> B3
    D -.-> D1
    D -.-> D2
    D -.-> D3
```"""
    
    def _generate_backend_diagram(self, structure: Dict) -> str:
        return """```mermaid
graph LR
    A[HTTP Request] --> B[Router/Controller]
    B --> C[Middleware]
    C --> D[Service Layer]
    D --> E[Repository/DAO]
    E --> F[(Database)]
    
    D --> G[External Services]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#bbf,stroke:#333,stroke-width:2px
```"""
    
    def _generate_frontend_diagram(self, structure: Dict) -> str:
        return """```mermaid
graph TB
    A[index.html] --> B[Main App Component]
    B --> C[Routing]
    C --> D[Pages]
    D --> E[Shared Components]
    
    B --> F[State Management]
    F --> G[Redux/Context]
    
    B --> H[API Client]
    H --> I[Backend APIs]
    
    style A fill:#ff9,stroke:#333,stroke-width:2px
    style B fill:#9f9,stroke:#333,stroke-width:2px
```"""
    
    def _generate_simple_tree_diagram(self, structure: Dict) -> str:
        return """```mermaid
graph TD
    A[Project Root] --> B[Source Code]
    A --> C[Config Files]
    A --> D[Documentation]
    A --> E[Tests]
    
    B --> B1[Main Entry]
    B --> B2[Modules]
    
    C --> C1[dependencies]
    C --> C2[environment]
    
    style A fill:#ff9999,stroke:#333,stroke-width:2px
```"""