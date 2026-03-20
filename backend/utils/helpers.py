"""
Analytix AI — Shared utility functions.
"""
import uuid
import os
from pathlib import Path


def generate_id() -> str:
    """Generate a unique short ID."""
    return uuid.uuid4().hex[:12]


def get_upload_dir() -> Path:
    """Get or create the upload directory."""
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def safe_filename(filename: str) -> str:
    """Sanitize a filename for safe storage."""
    # Remove path separators and null bytes
    name = filename.replace("/", "_").replace("\\", "_").replace("\0", "")
    # Keep only safe characters
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- ")
    return "".join(c for c in name if c in safe_chars).strip()


def format_number(value, format_type: str = "number") -> str:
    """Format a number for display."""
    if value is None:
        return "N/A"
    try:
        if format_type == "currency":
            return f"${value:,.2f}"
        elif format_type == "percent":
            return f"{value:.1f}%"
        elif format_type == "integer":
            return f"{int(value):,}"
        else:
            if isinstance(value, float):
                if abs(value) >= 1_000_000:
                    return f"{value / 1_000_000:.1f}M"
                elif abs(value) >= 1_000:
                    return f"{value / 1_000:.1f}K"
                return f"{value:,.2f}"
            return f"{value:,}"
    except (ValueError, TypeError):
        return str(value)
