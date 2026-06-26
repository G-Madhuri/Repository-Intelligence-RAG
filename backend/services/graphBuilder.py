import os
import re
from typing import Dict, List, Any

# Simple regexes to find imports
PYTHON_IMPORT_RE = re.compile(r'^\s*(?:import\s+([\w\.,\s]+)|from\s+([\w\.]+)\s+import\s+([\w\.,\s\*]+))')
JS_IMPORT_RE = re.compile(r'(?:import\s+(?:[\w\s\{\}\*\,]+from\s+)?[\'"]([^\'"]+)[\'"]|require\([\'"]([^\'"]+)[\'"]\))')

def clean_python_import(imp_str: str) -> List[str]:
    """
    Cleans Python import strings. E.g. 'sys, os' -> ['sys', 'os']
    """
    if not imp_str:
        return []
    return [i.strip().split('.')[0] for i in imp_str.split(',') if i.strip()]

def extract_python_imports(content: str) -> List[str]:
    """
    Finds Python imports in code content.
    """
    imports = []
    for line in content.splitlines():
        match = PYTHON_IMPORT_RE.match(line)
        if match:
            group1, group2, _ = match.groups()
            if group1:
                # import X, Y
                imports.extend(clean_python_import(group1))
            if group2:
                # from X import Y
                # extract X
                parts = group2.split('.')
                if parts:
                    imports.append(parts[0])
    return list(set(imports))

def extract_js_imports(content: str) -> List[str]:
    """
    Finds JavaScript/TypeScript imports in code content.
    """
    imports = []
    matches = JS_IMPORT_RE.findall(content)
    for match in matches:
        group1, group2 = match
        imported = group1 or group2
        if imported:
            # Clean up paths (e.g. "./utils" or "lodash")
            # If it starts with . or .., it is local, otherwise it's a library/module
            imports.append(imported)
    return list(set(imports))

def build_initial_graph(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Statically analyzes files to generate nodes (files) and edges (imports/references).
    """
    nodes = []
    edges = []
    
    # 1. Add file nodes
    for f in files:
        path = f["path"]
        _, ext = os.path.splitext(path.lower())
        
        # Determine node type based on extension
        node_type = "file"
        if ext in [".js", ".ts", ".jsx", ".tsx", ".py", ".go", ".rs", ".java"]:
            node_type = "module"
        elif ext in [".json", ".yaml", ".yml"]:
            node_type = "config"
        elif ext in [".html", ".css", ".scss"]:
            node_type = "ui"
            
        nodes.append({
            "id": path,
            "label": os.path.basename(path),
            "type": node_type,
            "properties": {
                "path": path,
                "size": f["size"]
            }
        })
        
    # 2. Extract dependencies (edges)
    for f in files:
        path = f["path"]
        content = f.get("content", "")
        _, ext = os.path.splitext(path.lower())
        
        imports = []
        if ext == ".py":
            imports = extract_python_imports(content)
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            imports = extract_js_imports(content)
            
        for imp in imports:
            # Check if this import resolves to a local file in the scanned repository
            # Simple matching: see if the import string is in any file path or matches file basenames
            target_path = None
            
            # Case 1: Import matches local file name directly or path-wise
            for other_f in files:
                other_path = other_f["path"]
                other_base, _ = os.path.splitext(os.path.basename(other_path))
                
                # Check relative match or direct name match
                if imp == other_base or imp.endswith(other_base) or other_path.endswith(imp):
                    target_path = other_path
                    break
                    
            if target_path and target_path != path:
                edges.append({
                    "source": path,
                    "target": target_path,
                    "type": "imports",
                    "label": "imports"
                })
            else:
                # Case 2: Package/Library import (not in local files)
                # We can add a node for the external library if it's important,
                # but for Phase 1 skeleton we just skip external imports or let LLM do the mapping.
                pass
                
    return {
        "nodes": nodes,
        "edges": edges
    }
