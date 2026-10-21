"""Formatting and display helper utilities."""

from datetime import datetime


def format_timestamp(dt_str: str) -> str:
    """Formats an ISO timestamp into a readable date-time string."""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y - %I:%M %p")
    except Exception:
        return str(dt_str)


def format_file_size(size_bytes: int) -> str:
    """Converts bytes to readable KB/MB format."""
    if not size_bytes:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
