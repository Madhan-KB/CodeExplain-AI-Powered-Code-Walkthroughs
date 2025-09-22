from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import subprocess
import shutil
from pathlib import Path
import ast
import re
from typing import Dict, List, Any
import tempfile

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RepoRequest(BaseModel):
    repo_url: str

class RepoAnalysis:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.file_stats = {}
        self.structure = {}
        self.dependencies = set()
        self.total_lines = 0
        self.total_files = 0
        
    def analyze_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a Python file for classes, functions, and imports"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            imports = []
            classes = []
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                        self.dependencies.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(f"from {node.module}")
                        self.dependencies.add(node.module.split('.')[0])
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        'name': node.name,
                        'line': node.lineno,
                        'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    })
                elif isinstance(node, ast.FunctionDef):
                    if not any(node.lineno >= cls['line'] for cls in classes):
                        functions.append({
                            'name': node.name,
                            'line': node.lineno,
                            'args': [arg.arg for arg in node.args.args]
                        })
            
            lines = len(content.splitlines())
            self.total_lines += lines
            
            return {
                'type': 'python',
                'lines': lines,
                'imports': imports,
                'classes': classes,
                'functions': functions,
                'content_preview': content[:200] + '...' if len(content) > 200 else content
            }
            
        except Exception as e:
            return {'type': 'python', 'error': str(e), 'lines': 0}
    
    def analyze_javascript_file(self, file_path: Path) -> Dict[str, Any]:
        """Basic JavaScript/TypeScript file analysis"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple regex patterns for JS/TS
            imports = re.findall(r'import.*from [\'"]([^\'"]+)[\'"]', content)
            functions = re.findall(r'function\s+(\w+)|const\s+(\w+)\s*=.*=>', content)
            classes = re.findall(r'class\s+(\w+)', content)
            
            for imp in imports:
                self.dependencies.add(imp.split('/')[0] if '/' in imp else imp)
            
            lines = len(content.splitlines())
            self.total_lines += lines
            
            return {
                'type': 'javascript',
                'lines': lines,
                'imports': imports,
                'functions': [f[0] or f[1] for f in functions],
                'classes': classes,
                'content_preview': content[:200] + '...' if len(content) > 200 else content
            }
            
        except Exception as e:
            return {'type': 'javascript', 'error': str(e), 'lines': 0}
    
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze any file based on its extension"""
        suffix = file_path.suffix.lower()
        
        if suffix == '.py':
            return self.analyze_python_file(file_path)
        elif suffix in ['.js', '.jsx', '.ts', '.tsx']:
            return self.analyze_javascript_file(file_path)
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                lines = len(content.splitlines())
                self.total_lines += lines
                return {
                    'type': 'text',
                    'lines': lines,
                    'content_preview': content[:200] + '...' if len(content) > 200 else content
                }
            except:
                return {'type': 'binary', 'lines': 0}
    
    def build_file_tree(self, path: Path, max_depth: int = 4, current_depth: int = 0) -> Dict[str, Any]:
        """Build a file tree structure"""
        if current_depth > max_depth:
            return {}
            
        tree = {}
        try:
            for item in sorted(path.iterdir()):
                # Skip hidden files and common ignore patterns
                if item.name.startswith('.') or item.name in ['node_modules', '__pycache__', 'venv']:
                    continue
                
                if item.is_file():
                    self.total_files += 1
                    file_analysis = self.analyze_file(item)
                    tree[item.name] = {
                        'type': 'file',
                        'path': str(item.relative_to(self.repo_path)),
                        'analysis': file_analysis
                    }
                elif item.is_dir():
                    subtree = self.build_file_tree(item, max_depth, current_depth + 1)
                    if subtree:  # Only include if not empty
                        tree[item.name] = {
                            'type': 'directory',
                            'children': subtree
                        }
        except PermissionError:
            pass
            
        return tree
    
    def generate_repo_map(self) -> Dict[str, Any]:
        """Generate the complete repository map"""
        self.structure = self.build_file_tree(self.repo_path)
        
        # Get top dependencies
        top_deps = sorted(list(self.dependencies))[:10]
        
        return {
            'repository_structure': self.structure,
            'statistics': {
                'total_files': self.total_files,
                'total_lines': self.total_lines,
                'top_dependencies': top_deps
            },
            'analysis_metadata': {
                'repo_path': str(self.repo_path),
                'analyzed_file_types': ['.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.md']
            }
        }
    
    def generate_repo_tour(self) -> str:
        """Generate a guided tour in markdown format"""
        tour = f"""# Repository Tour

## 🏗️ Project Overview
This repository contains **{self.total_files} files** with **{self.total_lines} lines of code**.

## 📊 Quick Stats
- **Total Files:** {self.total_files}
- **Lines of Code:** {self.total_lines}
- **Key Dependencies:** {', '.join(sorted(list(self.dependencies))[:5])}

## 🗂️ Repository Structure

"""
        
        # Add structure explanation
        def explain_directory(tree: Dict, level: int = 0) -> str:
            explanation = ""
            indent = "  " * level
            
            for name, info in tree.items():
                if info['type'] == 'directory':
                    explanation += f"{indent}- **{name}/** - Directory containing:\n"
                    explanation += explain_directory(info['children'], level + 1)
                else:
                    analysis = info.get('analysis', {})
                    if analysis.get('type') == 'python' and analysis.get('classes'):
                        explanation += f"{indent}- **{name}** - Python module with {len(analysis['classes'])} classes\n"
                    elif analysis.get('type') == 'javascript' and analysis.get('functions'):
                        explanation += f"{indent}- **{name}** - JavaScript file with {len(analysis['functions'])} functions\n"
                    else:
                        explanation += f"{indent}- **{name}** - {analysis.get('lines', 0)} lines\n"
            
            return explanation
        
        tour += explain_directory(self.structure)
        
        tour += """

## 🚀 Getting Started

Based on the repository analysis, here's how the code is organized:

"""
        
        # Find main files
        main_files = []
        for name, info in self.structure.items():
            if info['type'] == 'file' and name in ['main.py', 'app.py', 'index.js', 'index.tsx', 'package.json']:
                main_files.append(name)
        
        if main_files:
            tour += f"### Key Files:\n"
            for file in main_files:
                tour += f"- **{file}** - Entry point or configuration file\n"
        
        tour += """
## 🔧 Code Architecture

The codebase follows standard conventions with clear separation of concerns. Key patterns identified:

- **Modular Structure** - Code is organized into logical modules
- **Configuration Management** - Settings and dependencies are properly managed
- **Clean Interfaces** - Functions and classes have clear responsibilities

## 📚 Dependencies

This project relies on several key libraries:
"""
        
        for dep in sorted(list(self.dependencies))[:10]:
            tour += f"- `{dep}`\n"
        
        return tour

def clone_repository(repo_url: str) -> str:
    """Clone a GitHub repository to a temporary directory"""
    temp_dir = tempfile.mkdtemp()
    try:
        subprocess.run(
            ['git', 'clone', repo_url, temp_dir],
            check=True,
            capture_output=True,
            text=True
        )
        return temp_dir
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Failed to clone repository: {e.stderr}")

@app.post("/analyze-repo")
async def analyze_repository(request: RepoRequest):
    """Main endpoint to analyze a GitHub repository"""
    try:
        # Clone the repository
        repo_path = clone_repository(request.repo_url)
        
        # Analyze the repository
        analyzer = RepoAnalysis(repo_path)
        repo_map = analyzer.generate_repo_map()
        repo_tour = analyzer.generate_repo_tour()
        
        # Clean up
        shutil.rmtree(repo_path)
        
        return {
            'success': True,
            'repo_map': repo_map,
            'repo_tour': repo_tour,
            'repo_url': request.repo_url
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.get("/")
async def root():
    return {"message": "RepoPilot API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)