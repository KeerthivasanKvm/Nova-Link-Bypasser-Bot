"""
Constants
=========
Bot constants and messages.
"""


class EMOJI:
    """Emoji constants"""
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"
    LOCK = "🔒"
    UNLOCK = "🔓"
    STAR = "⭐"
    TROPHY = "🏆"
    FIRE = "🔥"
    ROCKET = "🚀"
    GIFT = "🎁"
    BELL = "🔔"
    CHART = "📊"
    GEAR = "⚙️"
    LINK = "🔗"
    USER = "👤"
    USERS = "👥"
    BOT = "🤖"
    TIME = "⏰"
    CALENDAR = "📅"
    MONEY = "💰"
    CREDIT_CARD = "💳"
    DIAMOND = "💎"
    CROWN = "👑"
    CHECK = "✓"
    CROSS = "✗"
    ARROW_RIGHT = "→"
    ARROW_LEFT = "←"
    ARROW_UP = "↑"
    ARROW_DOWN = "↓"


class MESSAGES:
    """Message templates"""
    
    WELCOME = """
👋 **Welcome to Ultimate Link Bypass Bot!**

Hello {name}! I'm your personal link bypass assistant.

**What I can do:**
🔓 Bypass link shorteners instantly
⚡ Support 100+ shortener sites
🤖 AI-powered bypass technology
💎 Premium features available

**Get Started:**
• Send `/bypass <link>` or just `B <link>`
• Check your stats with `/stats`
• View premium info with `/premium`

Need help? Use `/help` for all commands.
"""
    
    HELP = """
📚 **Ultimate Link Bypass Bot - Help**

**User Commands:**
`/start` - Start the bot
`/bypass <link>` or `B <link>` - Bypass a link
`/premium` - View premium information
`/stats` - View your statistics
`/referral` - Get your referral link
`/redeem <token>` - Redeem access token
`/reset <key>` - Reset limits with key
`/report <issue>` - Report broken link
`/request <site>` - Request new site support
`/feedback <message>` - Send feedback
`/help` - Show this help

**Premium Benefits:**
✅ Unlimited daily bypasses
✅ Priority processing
✅ Access to all bypass methods
✅ No waiting time
"""
    
    BYPASS_SUCCESS = """
🎉 **Link Bypassed Successfully!**

🔗 **Original:** `{original}`
✨ **Bypassed:** `{bypassed}`

✅ **Method:** `{method}`
⏱️ **Time:** {time:.2f}s

**Your Stats:**
📊 Today: {today}/{limit}
📈 Total: {total}
"""
    
    BYPASS_FAILED = """
❌ **Bypass Failed!**

🔗 **URL:** `{url}`

**Error:**
{error}

**What you can do:**
• Check if the link is valid
• Try again later
• Report with `/report {url}`
"""
    
    PREMIUM_ACTIVE = """
💎 **Premium Status: Active** ✅

**Time Remaining:**
{days} days, {hours} hours

**Your Benefits:**
✅ Unlimited daily bypasses
✅ Priority processing
✅ All bypass methods
✅ No waiting time
✅ Premium support

**Thank you for being premium!** 🌟
"""
    
    PREMIUM_INACTIVE = """
💎 **Upgrade to Premium!**

**Current Plan:** Free
**Daily Limit:** {limit} bypasses

**Premium Benefits:**
✅ Unlimited daily bypasses
✅ Priority processing
✅ Access to all bypass methods
✅ No waiting time
✅ Premium support

**How to upgrade:**
1. Get an access token from admin
2. Use `/redeem <token>` to activate

**Or earn free premium:**
• Use your referral link (`/referral`)
• Each referral = {reward_days} days premium!
"""
    
    LIMIT_REACHED = """
⏳ **Limit Reached!**

You've used all your daily bypasses.
Limit resets in: {time_remaining}

💎 **Upgrade to Premium** for unlimited bypasses!
Use `/premium` to learn more.
"""
    
    TOKEN_REDEEMED = """
🎉 **Token Redeemed Successfully!**

✅ Premium activated for {duration}
💎 Premium status: Active

Thank you for upgrading! Enjoy unlimited bypasses! 🚀
"""
    
    REFERRAL_INFO = """
👥 **Referral Program**

**Your Referral Link:**
`{link}`

**Share this link with friends!**

**Rewards:**
🎁 Each friend who joins = **{reward_days} days premium**
📊 Your Referrals: {count}
💰 Total Earned: {earned} days

**How it works:**
1. Share your link
2. Friends click and start bot
3. You get premium days automatically!

**Maximum:** {max_reward} days from referrals
"""
