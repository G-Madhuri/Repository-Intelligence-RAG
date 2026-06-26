import os
import stat
import shutil
import tempfile
import zipfile
import subprocess
import urllib.parse
import httpx
from typing import Dict, List, Tuple, Any

# Directories to completely ignore during scanning
IGNORED_DIRS = {
    "node_modules", "venv", ".git", "dist", "build", "__pycache__", 
    ".venv", "env", ".env", "bin", "obj", "target", "out"
}

# File extensions to ignore (binary and build artifacts)
IGNORED_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", 
    ".gz", ".db", ".sqlite", ".exe", ".dll", ".so", ".dylib", ".class", 
    ".pyc", ".pyd", ".woff", ".woff2", ".ttf", ".eot", ".svg", ".mp4",
    ".mp3", ".wav", ".avi", ".mov", ".zip", ".rar", ".7z", ".tar.gz",
    ".DS_Store", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"
}

# Maximum size for a single file to be read for LLM analysis (100 KB)
MAX_FILE_SIZE_BYTES = 100 * 1024

def handle_remove_readonly(func, path, excinfo):
    """
    Error handler for shutil.rmtree on Windows to remove read-only attributes.
    """
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def parse_github_url(url: str) -> Tuple[str, str]:
    """
    Parses owner and repository name from a GitHub URL.
    Supports formats like:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - git@github.com:owner/repo.git
    """
    url = url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    
    if url.startswith("git@github.com:"):
        path = url.split("git@github.com:")[1]
    elif "github.com/" in url:
        path = url.split("github.com/")[1]
    else:
        # Fallback if it is just "owner/repo"
        path = url

    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2:
        return parts[0], parts[1]
    raise ValueError("Invalid GitHub URL format. Expected 'https://github.com/owner/repo'")

async def check_repository_privacy(url: str, token: str = None) -> Dict[str, Any]:
    """
    Checks if a GitHub repository is public or private.
    Returns a dict with 'status' (public/private/invalid), 'message', and 'owner_repo'.
    """
    try:
        owner, repo = parse_github_url(url)
        owner_repo = f"{owner}/{repo}"
    except Exception as e:
        return {
            "status": "invalid",
            "message": f"Could not parse GitHub URL: {str(e)}",
            "owner_repo": None
        }

    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Repository-Intelligence-App"
    }
    
    # Check without token first
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, headers=headers)
            if response.status_code == 200:
                return {
                    "status": "public",
                    "message": "Repository is public.",
                    "owner_repo": owner_repo
                }
            elif response.status_code == 404:
                # If a token is provided, verify access with the token
                if token:
                    headers["Authorization"] = f"token {token}"
                    token_response = await client.get(api_url, headers=headers)
                    if token_response.status_code == 200:
                        return {
                            "status": "private",
                            "message": "Private repository access validated successfully.",
                            "owner_repo": owner_repo
                        }
                    else:
                        return {
                            "status": "private_denied",
                            "message": "Access denied. Please check your GitHub Personal Access Token.",
                            "owner_repo": owner_repo
                        }
                return {
                    "status": "private_requires_auth",
                    "message": "Repository is private or does not exist. A GitHub Personal Access Token is required.",
                    "owner_repo": owner_repo
                }
            else:
                return {
                    "status": "error",
                    "message": f"GitHub API returned HTTP {response.status_code}",
                    "owner_repo": owner_repo
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to connect to GitHub: {str(e)}",
                "owner_repo": owner_repo
            }

def sanitize_git_error(error_msg: str, token: str) -> str:
    """
    Removes Personal Access Tokens from git output logs and errors.
    """
    if not token:
        return error_msg
    return error_msg.replace(token, "[REDACTED]")

def clone_repository(url: str, dest_dir: str, token: str = None) -> None:
    """
    Clones a repository into a destination directory. Sanitizes token output.
    """
    try:
        owner, repo = parse_github_url(url)
    except Exception as e:
        raise Exception(f"Failed to parse repository URL: {str(e)}")

    if token:
        # Build authenticated URL
        # Format: https://x-access-token:<token>@github.com/owner/repo.git
        encoded_token = urllib.parse.quote(token)
        clone_url = f"https://x-access-token:{encoded_token}@github.com/{owner}/{repo}.git"
    else:
        clone_url = f"https://github.com/{owner}/{repo}.git"

    # git clone requires the destination to be empty. Since tempfile.mkdtemp
    # creates the directory, we clone into it using '.' which works when empty.
    cmd = ["git", "clone", "--depth", "1", clone_url, "."]
    
    try:
        # Run clone command inside dest_dir. Divert stderr to capture execution errors.
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=dest_dir)
    except subprocess.CalledProcessError as e:
        stderr_sanitized = sanitize_git_error(e.stderr, token)
        raise Exception(f"Git clone failed: {stderr_sanitized}")
    except Exception as e:
        raise Exception(f"Git execution error: {str(e)}")

def extract_zip(zip_path: str, dest_dir: str) -> None:
    """
    Extracts an uploaded zip file into a target directory.
    Includes security protection against path traversal.
    """
    target_dir = os.path.abspath(dest_dir)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.infolist():
            # Resolve target path and verify it remains within target directory bounds
            target_path = os.path.abspath(os.path.join(target_dir, member.filename))
            if not target_path.startswith(target_dir + os.sep) and target_path != target_dir:
                raise Exception(f"Security Warning: Path traversal attempt detected in zip file: {member.filename}")
        
        # Safe to extract
        zip_ref.extractall(target_dir)

def is_text_file(file_path: str) -> bool:
    """
    Heuristically checks if a file is a text file by scanning its initial bytes.
    Also respects files that are purely empty as text files.
    """
    # Check extension first
    _, ext = os.path.splitext(file_path)
    if ext.lower() in IGNORED_EXTS:
        return False
        
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\x00' in chunk:  # Binary files typically contain null bytes
                return False
            # Check if it can be decoded as utf-8 or ascii
            try:
                chunk.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    chunk.decode('latin-1')
                except UnicodeDecodeError:
                    return False
        return True
    except Exception:
        return False

def scan_directory(dir_path: str) -> Dict[str, Any]:
    """
    Recursively scans the directory and returns:
    1. A nested file tree structure for visualization.
    2. A flat list of code files with their relative path and partial text contents (if key).
    """
    file_tree = {}
    flat_files = []
    
    # Resolve the absolute path
    abs_dir_path = os.path.abspath(dir_path)

    # Let's check if the unzipped repository structure has a single root folder wrapping the project
    # (common in GitHub source code ZIPs like repo-name-main/)
    scan_root = abs_dir_path
    subdirs = os.listdir(abs_dir_path)
    # If the folder contains only a single directory and no other files, we dive in
    if len(subdirs) == 1:
        single_path = os.path.join(abs_dir_path, subdirs[0])
        if os.path.isdir(single_path) and subdirs[0] not in IGNORED_DIRS:
            scan_root = single_path

    # Helper to recursively build tree
    def build_tree(current_dir: str, tree_node: Dict[str, Any]) -> None:
        try:
            entries = os.listdir(current_dir)
        except Exception:
            return

        for entry in entries:
            if entry in IGNORED_DIRS:
                continue

            full_path = os.path.join(current_dir, entry)
            rel_path = os.path.relpath(full_path, scan_root).replace("\\", "/")

            if os.path.isdir(full_path):
                tree_node[entry] = {
                    "type": "directory",
                    "path": rel_path,
                    "children": {}
                }
                build_tree(full_path, tree_node[entry]["children"])
                # If directory has no children, we still keep it
            else:
                _, ext = os.path.splitext(entry)
                if ext.lower() in IGNORED_EXTS:
                    continue
                
                size = os.path.getsize(full_path)
                tree_node[entry] = {
                    "type": "file",
                    "path": rel_path,
                    "size": size
                }
                
                # Check if it is a text file and size is within limits
                if size <= MAX_FILE_SIZE_BYTES and is_text_file(full_path):
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        flat_files.append({
                            "path": rel_path,
                            "size": size,
                            "content": content
                        })
                    except Exception:
                        pass

    root_tree = {}
    build_tree(scan_root, root_tree)
    
    return {
        "tree": root_tree,
        "files": flat_files,
        "scan_root": scan_root
    }
