import os
import json
import re
from typing import Dict, List, Any

# Map extension to programming languages
EXTENSION_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".go": "Go",
    ".java": "Java",
    ".kt": "Kotlin",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".sh": "Shell Script",
    ".bat": "Batch Script",
    ".ps1": "PowerShell Script",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".yaml": "YAML Config",
    ".yml": "YAML Config",
    ".json": "JSON Config",
    ".md": "Markdown",
    ".tf": "Terraform",
    ".dockerfile": "Dockerfile"
}

def detect_languages_from_files(files: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Counts frequency of detected languages based on file extensions.
    """
    lang_counts = {}
    for f in files:
        path = f["path"]
        _, ext = os.path.splitext(path.lower()) if 'os' in globals() else (None, "." + path.split(".")[-1] if "." in path else "")
        lang = EXTENSION_MAP.get(ext)
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
    return lang_counts

def parse_package_json(content: str) -> Dict[str, Any]:
    """
    Parses Node.js dependencies and frameworks from package.json.
    """
    result = {
        "frameworks": [],
        "libraries": [],
        "databases": [],
        "package_manager": "npm"
    }
    try:
        data = json.loads(content)
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        
        # Detect Frameworks & key libraries
        framework_signatures = {
            "react": "React",
            "vue": "Vue",
            "angular": "Angular",
            "@angular/core": "Angular",
            "next": "Next.js",
            "nuxt": "Nuxt.js",
            "express": "Express",
            "koa": "Koa",
            "nest": "NestJS",
            "@nestjs/core": "NestJS",
            "svelte": "Svelte",
            "gatsby": "Gatsby",
            "fastify": "Fastify"
        }
        
        db_signatures = {
            "mongoose": "MongoDB (Mongoose)",
            "mongodb": "MongoDB",
            "pg": "PostgreSQL (pg)",
            "mysql": "MySQL",
            "mysql2": "MySQL (mysql2)",
            "sequelize": "Sequelize ORM",
            "prisma": "Prisma ORM",
            "redis": "Redis",
            "ioredis": "Redis (ioredis)",
            "sqlite3": "SQLite"
        }

        for dep_name in deps:
            for sig, label in framework_signatures.items():
                if sig == dep_name or dep_name.startswith(sig + "/"):
                    if label not in result["frameworks"]:
                        result["frameworks"].append(label)
            
            for sig, label in db_signatures.items():
                if sig == dep_name:
                    if label not in result["databases"]:
                        result["databases"].append(label)
                        
            # Standard dependencies of interest
            if dep_name in ["axios", "lodash", "rxjs", "dotenv", "webpack", "vite", "typescript"]:
                result["libraries"].append(dep_name)
                
    except Exception:
        pass
    return result

def parse_requirements_txt(content: str) -> Dict[str, Any]:
    """
    Parses Python dependencies and frameworks from requirements.txt.
    """
    result = {
        "frameworks": [],
        "libraries": [],
        "databases": [],
        "package_manager": "pip"
    }
    
    # Simple regex to split lines and strip versions
    lines = content.splitlines()
    deps = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Remove version requirements e.g. fastapi>=0.100.0 or django==4.0
        parts = re.split(r'[=<>~]', line)
        if parts:
            dep_name = parts[0].strip().lower()
            deps.append(dep_name)
            
    framework_signatures = {
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
        "tornado": "Tornado",
        "pyramid": "Pyramid",
        "sanic": "Sanic"
    }
    
    db_signatures = {
        "psycopg2": "PostgreSQL (psycopg2)",
        "psycopg2-binary": "PostgreSQL",
        "pymongo": "MongoDB",
        "redis": "Redis",
        "sqlalchemy": "SQLAlchemy ORM",
        "tortoise-orm": "Tortoise ORM",
        "peewee": "Peewee ORM",
        "mysqlclient": "MySQL",
        "pymysql": "MySQL (PyMySQL)"
    }
    
    for dep in deps:
        for sig, label in framework_signatures.items():
            if sig == dep:
                if label not in result["frameworks"]:
                    result["frameworks"].append(label)
        
        for sig, label in db_signatures.items():
            if sig == dep:
                if label not in result["databases"]:
                    result["databases"].append(label)
                    
        if dep in ["requests", "numpy", "pandas", "scipy", "celery", "pydantic", "jinja2", "cryptography"]:
            result["libraries"].append(dep)
            
    return result

def profile_repository(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Orchestrates scan file inspection and compiles framework, database, language, 
    and build metadata profiles.
    """
    profile = {
        "languages": {},
        "frameworks": [],
        "libraries": [],
        "databases": [],
        "package_managers": [],
        "infrastructure": []
    }
    
    # Calculate languages
    for f in files:
        path = f["path"]
        # Extract extension
        ext = "." + path.split(".")[-1] if "." in path else ""
        lang = EXTENSION_MAP.get(ext.lower())
        if lang:
            profile["languages"][lang] = profile["languages"].get(lang, 0) + 1
            
    # Normalize language frequencies to sorted list
    sorted_langs = sorted(profile["languages"].items(), key=lambda x: x[1], reverse=True)
    profile["languages"] = [l[0] for l in sorted_langs]

    # Look for files of interest
    for f in files:
        path = f["path"].lower()
        content = f.get("content", "")
        
        # package.json (Node)
        if path.endswith("package.json"):
            js_profile = parse_package_json(content)
            for fw in js_profile["frameworks"]:
                if fw not in profile["frameworks"]:
                    profile["frameworks"].append(fw)
            for lib in js_profile["libraries"]:
                if lib not in profile["libraries"]:
                    profile["libraries"].append(lib)
            for db in js_profile["databases"]:
                if db not in profile["databases"]:
                    profile["databases"].append(db)
            if "npm" not in profile["package_managers"]:
                profile["package_managers"].append("npm")
                
        # requirements.txt (Python)
        elif path.endswith("requirements.txt") or path.endswith("pipfile"):
            py_profile = parse_requirements_txt(content)
            for fw in py_profile["frameworks"]:
                if fw not in profile["frameworks"]:
                    profile["frameworks"].append(fw)
            for lib in py_profile["libraries"]:
                if lib not in profile["libraries"]:
                    profile["libraries"].append(lib)
            for db in py_profile["databases"]:
                if db not in profile["databases"]:
                    profile["databases"].append(db)
            if "pip" not in profile["package_managers"]:
                profile["package_managers"].append("pip")
                
        # go.mod (Go)
        elif path.endswith("go.mod"):
            if "Go modules" not in profile["package_managers"]:
                profile["package_managers"].append("Go modules")
            # Basic static checks
            if "gin-gonic" in content or "github.com/gin-gonic/gin" in content:
                profile["frameworks"].append("Gin (Go)")
            if "gorm.io/gorm" in content:
                profile["databases"].append("GORM ORM")
            if "go.mongodb.org/mongo-driver" in content:
                profile["databases"].append("MongoDB")
                
        # Cargo.toml (Rust)
        elif path.endswith("cargo.toml"):
            if "Cargo" not in profile["package_managers"]:
                profile["package_managers"].append("Cargo")
            if "tokio" in content:
                profile["libraries"].append("tokio (async)")
            if "actix-web" in content:
                profile["frameworks"].append("Actix-web")
            if "axum" in content:
                profile["frameworks"].append("Axum")
                
        # Infrastructure files
        if "dockerfile" in path or path.endswith("/dockerfile"):
            if "Docker" not in profile["infrastructure"]:
                profile["infrastructure"].append("Docker")
        elif path.endswith("docker-compose.yml") or path.endswith("docker-compose.yaml"):
            if "Docker Compose" not in profile["infrastructure"]:
                profile["infrastructure"].append("Docker Compose")
        elif ".github/workflows" in path:
            if "GitHub Actions CI/CD" not in profile["infrastructure"]:
                profile["infrastructure"].append("GitHub Actions CI/CD")
        elif "kubernetes" in path or path.endswith(".k8s.yml") or path.endswith(".k8s.yaml"):
            if "Kubernetes" not in profile["infrastructure"]:
                profile["infrastructure"].append("Kubernetes")
        elif path.endswith("serverless.yml") or path.endswith("serverless.yaml"):
            if "Serverless Framework" not in profile["infrastructure"]:
                profile["infrastructure"].append("Serverless Framework")

    return profile
