import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from main import app, get_current_user

print("==========================================================")
print("           FASTAPI ROUTE DEPENDENCY AUDIT                ")
print("==========================================================")
print(f"{'METHOD':<8} | {'PATH':<35} | {'PROTECTED WITH Depends(get_current_user)'}")
print("-" * 80)

for route in app.routes:
    if hasattr(route, "path"):
        methods = ", ".join(route.methods) if hasattr(route, "methods") else "GET"
        dependencies = getattr(route, "dependencies", [])
        
        # Check endpoint signature for Depends(get_current_user)
        is_protected = False
        if hasattr(route, "endpoint"):
            import inspect
            sig = inspect.signature(route.endpoint)
            for param in sig.parameters.values():
                if param.default and hasattr(param.default, "dependency"):
                    if param.default.dependency == get_current_user:
                        is_protected = True
                        break
                        
        status_str = "YES [PROTECTED]" if is_protected else "NO (PUBLIC ROUTE)"
        print(f"{methods:<8} | {route.path:<35} | {status_str}")

print("==========================================================")
