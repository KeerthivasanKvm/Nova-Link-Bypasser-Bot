"""
Validators
==========
Input validation functions.
"""

import re
from urllib.parse import urlparse
from typing import Optional

from config import bypass_config


def is_valid_url(url: str) -> bool:
    """
    Check if string is a valid URL.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL pattern
    pattern = r'^https?://[^\s<>"\']+$'
    if not re.match(pattern, url):
        return False
    
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def extract_url(text: str) -> Optional[str]:
    """
    Extract URL from text.
    
    Args:
        text: Text to search
        
    Returns:
        First URL found or None
    """
    # URL pattern
    pattern = r'https?://[^\s<>"\']+'
    match = re.search(pattern, text)
    
    if match:
        return match.group(0)
    
    return None


def is_supported_domain(url: str) -> bool:
    """
    Check if URL domain is supported.
    
    Args:
        url: URL to check
        
    Returns:
        True if supported
    """
    try:
        domain = urlparse(url).netloc.lower()
        
        # Check blocked domains first
        for blocked in bypass_config.BLOCKED_DOMAINS:
            if blocked in domain:
                return False
        
        # Check allowed domains
        for allowed in bypass_config.ALLOWED_SHORTENERS:
            if allowed in domain:
                return True
        
        # If no specific match, allow all (configurable)
        return True
        
    except Exception:
        return False


def is_valid_token(token: str) -> bool:
    """
    Check if token format is valid.
    
    Args:
        token: Token to validate
        
    Returns:
        True if valid format
    """
    if not token:
        return False
    
    # Token should be alphanumeric, 12 characters
    pattern = r'^[A-Z0-9]{12}$'
    return bool(re.match(pattern, token))


def is_valid_reset_key(key: str) -> bool:
    """
    Check if reset key format is valid.
    
    Args:
        key: Key to validate
        
    Returns:
        True if valid format
    """
    if not key:
        return False
    
    # Key should start with RESET_ followed by alphanumeric
    pattern = r'^RESET_[A-Z0-9]{10}$'
    return bool(re.match(pattern, key))


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input.
    
    Args:
        text: Input text
        max_length: Maximum length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
    
    # Limit length
    text = text[:max_length]
    
    # Strip whitespace
    text = text.strip()
    
    return text
