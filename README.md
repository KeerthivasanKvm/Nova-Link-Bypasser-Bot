# 🔗 Ultimate Link Bypass Bot

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore-orange.svg)](https://firebase.google.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> The most powerful Telegram bot for bypassing link shorteners with AI-powered scraping, premium features, and comprehensive admin controls.

## ✨ Features

### 🔓 Bypass Capabilities
- ✅ **Pure HTML sites** (forms, meta tags)
- ✅ **CSS-only protection** (hidden elements)
- ✅ **JavaScript sites** (any complexity)
- ✅ **Mixed protection** (HTML + CSS + JS)
- ✅ **Countdown timers**
- ✅ **Dynamic content loading**
- ✅ **Cloudflare protection**
- ✅ **Multiple redirect chains**
- ✅ **Base64/URL encoding**
- ✅ **Complex multi-step bypasses**
- ✅ **AI-powered adaptive bypassing**

### 👑 Premium System
- **Free Users**: Limited daily/hourly bypasses
- **Premium Users**: Unlimited bypasses
- **Access Tokens**: One-time use tokens for temporary premium access
- **Referral System**: Earn premium days by inviting friends

### 🛡️ Admin Controls
- Generate access tokens (1h, 1d, 7d, 30d)
- Set free user limits
- Add/Restrict link shortener domains
- Create universal reset keys
- Enable/disable referral system
- Grant group/PM permissions
- Broadcast messages
- View error reports & feedback

### 🔧 Advanced Features
- **Force Subscribe**: Users must join channel/group before using
- **Group-only mode**: Bot works only in authorized groups
- **Cloudflare bypass**: Advanced scraping techniques
- **Smart caching**: Firebase-optimized for performance
- **Notification system**: Premium expiry reminders
- **Error reporting**: Direct PM to admin

## 🚀 Deployment

### Quick Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Manual Deployment

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ultimate-link-bypass-bot.git
cd ultimate-link-bypass-bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
playwright install
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Set up Firebase**
- Create a Firebase project
- Download service account credentials
- Save as `firebase-credentials.json` or use env variables

5. **Run the bot**
```bash
# Webhook mode (recommended for production)
python main.py

# Or polling mode (for development)
python main.py --polling
```

## 📁 Project Structure

```
telegram_bypass_bot/
├── bot/                    # Core bot functionality
│   ├── __init__.py
│   ├── bot.py             # Main bot instance
│   └── webhook_server.py  # Flask webhook server
├── database/              # Firebase integration
│   ├── __init__.py
│   ├── firebase_db.py     # Firebase connection
│   ├── models.py          # Data models
│   └── cache_manager.py   # Caching system
├── bypass/                # Bypass methods
│   ├── __init__.py
│   ├── base_bypass.py     # Base class
│   ├── html_bypass.py     # HTML forms
│   ├── css_bypass.py      # CSS hidden elements
│   ├── js_bypass.py       # JavaScript execution
│   ├── cloudflare.py      # Cloudflare bypass
│   ├── browser_bypass.py  # Browser automation
│   └── ai_bypass.py       # AI-powered bypass
├── handlers/              # Telegram handlers
│   ├── __init__.py
│   ├── commands.py        # Command handlers
│   ├── messages.py        # Message handlers
│   └── callbacks.py       # Callback handlers
├── admin/                 # Admin features
│   ├── __init__.py
│   ├── admin_commands.py  # Admin commands
│   ├── token_manager.py   # Token management
│   └── broadcast.py       # Broadcast system
├── services/              # Business logic
│   ├── __init__.py
│   ├── premium_service.py # Premium management
│   ├── referral_system.py # Referral logic
│   └── notifications.py   # Notification system
├── middleware/            # Middleware
│   ├── __init__.py
│   ├── force_sub.py       # Force subscribe check
│   ├── group_check.py     # Group validation
│   └── rate_limiter.py    # Rate limiting
├── ai_agent/              # AI integration
│   ├── __init__.py
│   └── scraper_agent.py   # Web scraping AI agent
├── utils/                 # Utilities
│   ├── __init__.py
│   ├── helpers.py         # Helper functions
│   ├── validators.py      # Input validation
│   ├── decorators.py      # Custom decorators
│   └── constants.py       # Constants
├── config.py              # Configuration
├── main.py                # Entry point
├── requirements.txt       # Dependencies
├── render.yaml            # Render config
├── start.sh               # Start script
└── README.md              # This file
```

## 📝 Commands

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/bypass <link>` or `B <link>` | Bypass a link |
| `/premium` | View premium info |
| `/referral` | Get referral link |
| `/stats` | View your stats |
| `/redeem <token>` | Redeem access token |
| `/reset <key>` | Reset limits with key |
| `/report <issue>` | Report broken link |
| `/request <site>` | Request new site support |
| `/feedback <message>` | Send feedback |
| `/help` | Show help |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/admin` | Admin panel |
| `/generate_token <duration>` | Generate token (1h/1d/7d/30d) |
| `/revoke_token <token>` | Revoke a token |
| `/add_domain <domain>` | Add allowed domain |
| `/remove_domain <domain>` | Remove domain |
| `/block_domain <domain>` | Block domain |
| `/generate_reset_key` | Generate universal reset key |
| `/set_limit <number>` | Set free user daily limit |
| `/toggle_referral` | Toggle referral system |
| `/grant_access <group_id>` | Grant group access |
| `/revoke_access <group_id>` | Revoke group access |
| `/broadcast <message>` | Broadcast to all users |
| `/stats_all` | View all stats |
| `/config` | View configuration |
| `/logs` | View error reports |

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | ✅ | Telegram bot token |
| `ADMIN_IDS` | ✅ | Comma-separated admin IDs |
| `OWNER_ID` | ✅ | Super admin ID |
| `FORCE_SUB_CHANNEL` | ✅ | Force subscribe channel |
| `FIREBASE_PROJECT_ID` | ✅ | Firebase project ID |
| `FIREBASE_PRIVATE_KEY` | ✅ | Firebase private key |
| `FIREBASE_CLIENT_EMAIL` | ✅ | Firebase client email |
| `WEBHOOK_URL` | ⚠️ | Required for webhook mode |
| `OPENAI_API_KEY` | ❌ | For AI-powered bypass |

## 🛡️ Security Features

- ✅ Rate limiting per user
- ✅ Input validation and sanitization
- ✅ Admin-only sensitive commands
- ✅ Group permission system
- ✅ Domain whitelist/blacklist
- ✅ Secure token generation
- ✅ Firebase security rules

## 🔄 Bypass Methods

The bot uses a cascading approach:

```
User sends link
      ↓
Method 1: HTML Forms → Success? Return link
      ↓ No
Method 2: CSS Hidden → Success? Return link
      ↓ No
Method 3: JavaScript → Success? Return link
      ↓ No
Method 4: Cloudflare → Success? Return link
      ↓ No
Method 5: Browser Auto → Success? Return link
      ↓ No
Method 6: AI-Powered → Success? Return link
      ↓ No
Return "Cannot bypass"
```

## 📊 Performance

- **Smart Caching**: Same links bypassed once for all users
- **Firebase Optimization**: Efficient database queries
- **Async Processing**: Non-blocking operations
- **Batch Operations**: Efficient broadcast system

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
- [Cloudscraper](https://github.com/VeNoMouS/cloudscraper)
- [Playwright](https://playwright.dev/python/)

## 📞 Support

For support, join our Telegram channel: [@YourSupportChannel]

---

<p align="center">
  Made with ❤️ for the Telegram community
</p>
