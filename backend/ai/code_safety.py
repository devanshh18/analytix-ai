"""
Analytix AI — Code Safety Validator.
Uses AST to validate generated code before execution.
"""
import ast
import re


# Blocked modules and builtins
BLOCKED_MODULES = {
    "os", "sys", "subprocess", "shutil", "pathlib",
    "socket", "http", "urllib", "requests", "smtplib",
    "ftplib", "telnetlib", "pickle", "shelve",
    "importlib", "ctypes", "multiprocessing",
    "__builtin__", "builtins", "code", "codeop",
    "compile", "compileall", "exec", "eval",
}

BLOCKED_BUILTINS = {
    "exec", "eval", "compile", "__import__",
    "open", "input", "breakpoint", "exit", "quit",
    "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr",
}

ALLOWED_MODULES = {
    "pandas", "pd", "numpy", "np", "math",
    "statistics", "datetime", "collections",
    "itertools", "functools", "operator",
    "json", "re", "string",
}


class CodeSafetyError(Exception):
    """Raised when unsafe code patterns are detected."""
    pass


def validate_code(code: str) -> bool:
    """Validate Python code for safety. Returns True if safe, raises CodeSafetyError otherwise."""

    # Basic pattern checks before AST parsing
    dangerous_patterns = [
        r'\bos\.\w+',
        r'\bsys\.\w+',
        r'\bsubprocess\b',
        r'\b__import__\b',
        r'\bexec\s*\(',
        r'\beval\s*\(',
        r'\bopen\s*\(',
        r'\bcompile\s*\(',
        r'\bbreakpoint\s*\(',
        r'\.system\s*\(',
        r'\.popen\s*\(',
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, code):
            raise CodeSafetyError(f"Potentially unsafe code pattern detected: {pattern}")

    # Parse AST
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise CodeSafetyError(f"Invalid Python syntax: {e}")

    # Walk AST nodes
    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in BLOCKED_MODULES:
                    raise CodeSafetyError(f"Import of blocked module: {mod}")
                if mod not in ALLOWED_MODULES:
                    raise CodeSafetyError(f"Import of unrecognized module: {mod}")

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.split(".")[0]
                if mod in BLOCKED_MODULES:
                    raise CodeSafetyError(f"Import from blocked module: {mod}")
                if mod not in ALLOWED_MODULES:
                    raise CodeSafetyError(f"Import from unrecognized module: {mod}")

        # Check function calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in BLOCKED_BUILTINS:
                    raise CodeSafetyError(f"Call to blocked builtin: {node.func.id}")

            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ("system", "popen", "exec", "eval"):
                    raise CodeSafetyError(f"Call to dangerous method: {node.func.attr}")

    return True


def safe_exec(code: str, context: dict) -> dict:
    """Execute validated code in a restricted context. Returns resulting variables."""
    validate_code(code)

    # Create a restricted globals/locals
    safe_globals = {"__builtins__": {}}

    # Add allowed modules
    import pandas as pd
    import numpy as np
    import math
    import statistics

    safe_globals.update({
        "pd": pd, "pandas": pd,
        "np": np, "numpy": np,
        "math": math,
        "statistics": statistics,
        "len": len, "range": range, "enumerate": enumerate,
        "zip": zip, "map": map, "filter": filter,
        "sorted": sorted, "reversed": reversed,
        "min": min, "max": max, "sum": sum,
        "abs": abs, "round": round,
        "int": int, "float": float, "str": str, "bool": bool,
        "list": list, "dict": dict, "tuple": tuple, "set": set,
        "isinstance": isinstance, "type": type,
        "print": lambda *a, **kw: None,  # Suppress print
    })

    safe_globals.update(context)
    safe_locals = {}

    try:
        exec(code, safe_globals, safe_locals)
    except Exception as e:
        raise CodeSafetyError(f"Code execution error: {type(e).__name__}: {str(e)}")

    return safe_locals
