"""
Ultimate Link Bypass Bot - Configuration
======================================
Centralized configuration management for the Telegram Bot.
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
    ])
    OWNER_ID: int = field(default_factory=lambda: int(os.getenv("OWNER_ID", "0")))
    FORCE_SUB_CHANNEL: str = field(default_factory=lambda: os.getenv("FORCE_SUB_CHANNEL", ""))
    FORCE_SUB_GROUP: str = field(default_factory=lambda: os.getenv("FORCE_SUB_GROUP", ""))
    LOG_CHANNEL: str = field(default_factory=lambda: os.getenv("LOG_CHANNEL", ""))


@dataclass
class FirebaseConfig:
    FIREBASE_PROJECT_ID: str = field(default_factory=lambda: os.getenv("FIREBASE_PROJECT_ID", ""))
    FIREBASE_PRIVATE_KEY: str = field(default_factory=lambda: os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"))
    FIREBASE_CLIENT_EMAIL: str = field(default_factory=lambda: os.getenv("FIREBASE_CLIENT_EMAIL", ""))
    FIREBASE_DATABASE_URL: str = field(default_factory=lambda: os.getenv("FIREBASE_DATABASE_URL", ""))
    FIREBASE_CREDENTIALS_PATH: str = field(default_factory=lambda: os.getenv("FIREBASE_CREDENTIALS_PATH", ""))


@dataclass
class PremiumConfig:
    FREE_DAILY_LIMIT: int = field(default_factory=lambda: int(os.getenv("FREE_DAILY_LIMIT", "5")))
    FREE_HOURLY_LIMIT: int = field(default_factory=lambda: int(os.getenv("FREE_HOURLY_LIMIT", "2")))
    PREMIUM_UNLIMITED: bool = True
    TOKEN_1H_VALIDITY: float = 1/24
    TOKEN_1D_VALIDITY: int = 1
    TOKEN_7D_VALIDITY: int = 7
    TOKEN_1M_VALIDITY: int = 30
    REFERRAL_REWARD_DAYS: int = 3
    REFERRAL_MAX_REWARD: int = 30
    REFERRAL_ENABLED: bool = True


@dataclass
class ProxyConfig:
    """
    Proxy configuration for bypass requests.
    
    Set these in Render environment variables:
    
    Option 1 — Manual proxy list (recommended for paid proxies):
        PROXY_LIST = "http://user:pass@host1:port,http://user:pass@host2:port"
    
    Option 2 — Webshare.io (cheap rotating proxies ~$2/month):
        WEBSHARE_API_KEY = "your_api_key_here"
        Get key from: https://proxy.webshare.io/
    
    Option 3 — ProxyScrape (free tier available):
        PROXYSCRAPE_API = "your_api_key_here"
        Get key from: https://proxyscrape.com/
    
    If none set → falls back to free public proxies (less reliable).
    """
    # Manual comma-separated proxy list
    PROXY_LIST: str = field(default_factory=lambda: os.getenv("PROXY_LIST", ""))

    # Webshare.io API key
    WEBSHARE_API_KEY: str = field(default_factory=lambda: os.getenv("WEBSHARE_API_KEY", ""))

    # ProxyScrape API key
    PROXYSCRAPE_API: str = field(default_factory=lambda: os.getenv("PROXYSCRAPE_API", ""))

    # How often to rotate to a new proxy (seconds)
    ROTATE_EVERY: int = field(default_factory=lambda: int(os.getenv("PROXY_ROTATE_EVERY", "10")))

    # Max failures before marking proxy dead
    MAX_FAILURES: int = field(default_factory=lambda: int(os.getenv("PROXY_MAX_FAILURES", "3")))

    # Whether proxies are enabled at all
    ENABLED: bool = field(default_factory=lambda: os.getenv("PROXY_ENABLED", "true").lower() == "true")

    @property
    def is_configured(self) -> bool:
        return bool(self.PROXY_LIST or self.WEBSHARE_API_KEY or self.PROXYSCRAPE_API)


@dataclass
class BypassConfig:
    REQUEST_TIMEOUT: int = 30
    BROWSER_TIMEOUT: int = 60
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2
    ALLOWED_SHORTENERS: List[str] = field(default_factory=lambda: [
        "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly",
        "short.link", "is.gd", "v.gd", "cutt.ly", "rebrand.ly",
        "short.io", "bl.ink", "buff.ly", "dlvr.it", "fb.me",
        "lnkd.in", "pin.it", "amzn.to", "ebay.to", "walmart.to",
        "linkvertise.com", "adf.ly", "ouo.io", "sh.st", "shorte.st",
        "clk.sh", "za.gl", "vivads.net", "ySense.com", "cpmlink.net",
        "payskip.org", "srt.am", "coinurl.com", "cur.lv", "ity.im",
        "q.gs", "ay.gy", "j.gs", "ur.ly", "ity.im",
        "linkshrink.net", "ad7.biz", "l2s.pet", "shrtfly.com",
        "gplinks.co", "droplink.co", "earn4link.in", "tnlink.in",
        "try2link.com", "ez4short.com", "adrinolinks.in", "mdiskshort.link",
        "rocklinks.net", "shortingly.me", "linksly.co", "ouo.press",
        "exee.io", "exe.io", "fc.lc", "shrinkearn.com", "short.pe",
        "tmearn.com", "linkrex.net", "uiz.io", "uii.io", "oko.sh",
        "traffic1s.com", "short2url.in", "urlshortx.com", "shrtco.de",
        "9qr.de", "short.gy", "t.ly", "rb.gy", "shorturl.at",
        "soo.gd", "s.id", "po.st", "bc.vc", "smsh.me",
        "clck.ru", "chng.it", "n9.cl", "0x.co", "1b.yt",
        "short.fyi", "kutt.it", "yourls.org", "polr.me", "shlink.io",
        "yaso.su", "v.ht", "zii.bz", "smarturl.it", "song.link",
        "show.co", "fanlink.to", "tone.den", "distrokid.com",
        "hypeddit.com", "push.fm", "lnk.to", "orcd.co", "ampl.ink",
        "bio.link", "linktr.ee", "beacons.ai", "stan.store", "koji.to",
        "solo.to", "liinks.co", "hoo.be", "snipfeed.co", "milkshake.app",
        "campsite.bio", "shor.by", "taplink.cc", "linkin.bio", "lnk.bio",
    ])
    BLOCKED_DOMAINS: List[str] = field(default_factory=lambda: [
        "malware.com", "phishing.com", "virus.com"
    ])
    BYPASS_METHODS_PRIORITY: List[str] = field(default_factory=lambda: [
        "html_forms", "css_hidden", "javascript",
        "cloudflare", "browser_auto", "ai_powered",
    ])


@dataclass
class AIConfig:
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    OPENAI_MODEL: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    AI_MAX_TOKENS: int = 2000
    AI_TEMPERATURE: float = 0.3
    AI_AGENT_MAX_ITERATIONS: int = 5
    AI_AGENT_TIMEOUT: int = 120


@dataclass
class WebhookConfig:
    WEBHOOK_ENABLED: bool = field(default_factory=lambda: os.getenv("WEBHOOK_ENABLED", "False").lower() == "true")
    WEBHOOK_URL: str = field(default_factory=lambda: os.getenv("WEBHOOK_URL", ""))
    WEBHOOK_PORT: int = field(default_factory=lambda: int(os.getenv("PORT", "10000")))
    WEBHOOK_PATH: str = "/webhook"
    POLLING_ENABLED: bool = field(default_factory=lambda: os.getenv("POLLING_ENABLED", "True").lower() == "true")
    POLLING_INTERVAL: float = 1.0


@dataclass
class NotificationConfig:
    REMINDER_DAYS: List[int] = field(default_factory=lambda: [7, 3, 1])
    CHECK_INTERVAL: int = 60
    BROADCAST_BATCH_SIZE: int = 25
    BROADCAST_DELAY: float = 1.5


# Initialize configurations
bot_config          = BotConfig()
firebase_config     = FirebaseConfig()
premium_config      = PremiumConfig()
proxy_config        = ProxyConfig()
bypass_config       = BypassConfig()
ai_config           = AIConfig()
webhook_config      = WebhookConfig()
notification_config = NotificationConfig()


def validate_config() -> Dict[str, bool]:
    return {
        "bot_token":  bool(bot_config.BOT_TOKEN),
        "admin_ids":  len(bot_config.ADMIN_IDS) > 0,
        "owner_id":   bot_config.OWNER_ID != 0,
        "firebase":   bool(firebase_config.FIREBASE_PROJECT_ID or firebase_config.FIREBASE_CREDENTIALS_PATH),
        "force_sub":  bool(bot_config.FORCE_SUB_CHANNEL),
    }


def get_config_summary() -> str:
    validation = validate_config()
    status = "✅" if all(validation.values()) else "❌"

    proxy_status = "✅ Configured" if proxy_config.is_configured else "⚠️ Using free proxies"
    if not proxy_config.ENABLED:
        proxy_status = "❌ Disabled"

    return f"""
{status} **Bot Configuration Summary**

**Core Settings:**
• Bot Token: {'✅ Set' if validation['bot_token'] else '❌ Missing'}
• Admin IDs: {len(bot_config.ADMIN_IDS)} admins
• Owner ID: {bot_config.OWNER_ID if bot_config.OWNER_ID else '❌ Not set'}
• Force Sub Channel: {bot_config.FORCE_SUB_CHANNEL or '❌ Not set'}

**Firebase:**
• {'✅ Configured' if validation['firebase'] else '❌ Not configured'}

**Proxy Settings:**
• Status: {proxy_status}
• Webshare: {'✅ Set' if proxy_config.WEBSHARE_API_KEY else '❌ Not set'}
• ProxyScrape: {'✅ Set' if proxy_config.PROXYSCRAPE_API else '❌ Not set'}
• Manual List: {'✅ ' + str(len(proxy_config.PROXY_LIST.split(','))) + ' proxies' if proxy_config.PROXY_LIST else '❌ Not set'}

**Premium Settings:**
• Free Daily Limit: {premium_config.FREE_DAILY_LIMIT}
• Free Hourly Limit: {premium_config.FREE_HOURLY_LIMIT}
• Referral System: {'✅ Enabled' if premium_config.REFERRAL_ENABLED else '❌ Disabled'}

**Bypass Settings:**
• Allowed Shorteners: {len(bypass_config.ALLOWED_SHORTENERS)} domains
• Bypass Methods: {len(bypass_config.BYPASS_METHODS_PRIORITY)} methods

**Webhook:**
• Mode: {'Webhook' if webhook_config.WEBHOOK_ENABLED else 'Polling'}
• Port: {webhook_config.WEBHOOK_PORT}
"""
