"""
Helper Functions
================
General utility functions.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional


def format_time_remaining(target_time: datetime) -> str:
    """
    Format time remaining until target time.
    
    Args:
        target_time: Target datetime
        
    Returns:
        Formatted string
    """
    now = datetime.utcnow()
    
    if target_time <= now:
        return "0s"
    
    diff = target_time - now
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if diff.days > 0:
        return f"{diff.days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def create_progress_bar(current: int, total: int, length: int = 10) -> str:
    """
    Create a text progress bar.
    
    Args:
        current: Current value
        total: Total value
        length: Bar length
        
    Returns:
        Progress bar string
    """
    if total == 0:
        return "◯" * length
    
    filled = int(length * current / total)
    filled = min(filled, length)  # Cap at length
    
    bar = "●" * filled + "○" * (length - filled)
    return f"[{bar}] {current}/{total}"


def generate_id(length: int = 8) -> str:
    """
    Generate random ID.
    
    Args:
        length: ID length
        
    Returns:
        Random ID string
    """
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes to human readable string.
    
    Args:
        bytes_value: Bytes value
        
    Returns:
        Formatted string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024
    
    return f"{bytes_value:.2f} PB"


def escape_markdown(text: str) -> str:
    """
    Escape Markdown special characters.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text
    """
    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def mask_sensitive(text: str, visible: int = 4) -> str:
    """
    Mask sensitive information.
    
    Args:
        text: Text to mask
        visible: Number of visible characters at end
        
    Returns:
        Masked text
    """
    if len(text) <= visible:
        return '*' * len(text)
    
    return '*' * (len(text) - visible) + text[-visible:]
