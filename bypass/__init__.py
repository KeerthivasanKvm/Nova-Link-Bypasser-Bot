"""
Bypass Module
=============
Link bypass methods for various protection types.
"""

from .base_bypass import BaseBypass, BypassResult
from .proxy_manager import ProxyManager, proxy_manager
from .html_bypass import HTMLBypass
from .css_bypass import CSSBypass
from .js_bypass import JavaScriptBypass
from .cloudflare import CloudflareBypass
from .gplinks_bypass import GPLinksbypass
from .universal_bypass import UniversalBypass
from .bypass_manager import BypassManager

# Optional — fail gracefully if dependencies missing
try:
    from .browser_bypass import BrowserBypass
except ImportError:
    BrowserBypass = None

try:
    from .ai_bypass import AIBypass
except ImportError:
    AIBypass = None

__all__ = [
    'BaseBypass',
    'BypassResult',
    'ProxyManager',
    'proxy_manager',
    'HTMLBypass',
    'CSSBypass',
    'JavaScriptBypass',
    'CloudflareBypass',
    'GPLinksbypass',
    'UniversalBypass',
    'BrowserBypass',
    'AIBypass',
    'BypassManager',
]
