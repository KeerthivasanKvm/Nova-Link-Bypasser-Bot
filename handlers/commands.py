"""
Command Handlers
================
All user command handlers for the bot.
"""

import re
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import bot_config, premium_config
from database.models import User, BypassCache, AccessToken, ResetKey, SiteRequest, ErrorReport
from middleware.force_sub import check_force_sub
from middleware.group_check import check_group_permission
from middleware.rate_limiter import rate_limit
from utils.helpers import format_time_remaining, create_progress_bar
from utils.validators import is_valid_url, extract_url
from utils.logger import get_logger

logger = get_logger(__name__)


# ==================== BASIC COMMANDS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Check force subscribe
    force_sub_check = await check_force_sub(update, context)
    if not force_sub_check:
        return
    
    # Get or create user
    db = context.bot_data['db']
    user_data = await db.get_user(user.id)
    
    if not user_data:
        # Create new user
        referral_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        
        # Check if referred
        referred_by = None
        if context.args and len(context.args) > 0:
            try:
                referred_by = int(context.args[0])
            except ValueError:
                pass
        
        user_data = User(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            referral_code=referral_code,
            referred_by=referred_by,
            daily_limit=premium_config.FREE_DAILY_LIMIT,
            hourly_limit=premium_config.FREE_HOURLY_LIMIT
        )
        
        await db.create_user(user_data)
        
        # Handle referral
        if referred_by and premium_config.REFERRAL_ENABLED:
            referrer = await db.get_user(referred_by)
            if referrer:
                # Add reward to referrer
                if referrer.referral_earned_days < premium_config.REFERRAL_MAX_REWARD:
                    referrer.referral_count += 1
                    referrer.referral_earned_days += premium_config.REFERRAL_REWARD_DAYS
                    
                    # Add premium time if not already premium
                    if not referrer.is_premium:
                        referrer.is_premium = True
                        referrer.premium_start = datetime.utcnow()
                        referrer.premium_expiry = datetime.utcnow() + timedelta(days=premium_config.REFERRAL_REWARD_DAYS)
                    else:
                        referrer.premium_expiry += timedelta(days=premium_config.REFERRAL_REWARD_DAYS)
                    
                    await db.update_user(referrer)
                    
                    # Notify referrer
                    try:
                        await context.bot.send_message(
                            chat_id=referrer.user_id,
                            text=f"🎉 **New Referral!**\n\n"
                                 f"User {user.first_name} joined using your link!\n"
                                 f"You earned {premium_config.REFERRAL_REWARD_DAYS} days of premium!"
                        )
                    except Exception:
                        pass
        
        welcome_text = f"""
👋 **Welcome to Ultimate Link Bypass Bot!**

Hello {user.first_name}! I'm your personal link bypass assistant.

**What I can do:**
🔓 Bypass link shorteners instantly
⚡ Support 100+ shortener sites
🤖 AI-powered bypass technology
💎 Premium features available

**Get Started:**
• Send `/bypass <link>` or just `B <link>`
• Check your stats with `/stats`
• View premium info with `/premium`

**Your Referral Code:** `{referral_code}`
Invite friends and earn premium days!

Need help? Use `/help` for all commands.
"""
    else:
        welcome_text = f"""
👋 **Welcome back, {user.first_name}!**

Ready to bypass some links?

**Quick Commands:**
• `/bypass <link>` - Bypass a link
• `/stats` - Check your usage
• `/premium` - Premium info
• `/help` - All commands

Use your referral code to earn premium days!
"""
    
    # Create keyboard
    keyboard = [
        [
            InlineKeyboardButton("🔓 Bypass Link", callback_data="bypass"),
            InlineKeyboardButton("💎 Premium", callback_data="premium")
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ],
        [
            InlineKeyboardButton("🌐 Join Channel", url=f"https://t.me/{bot_config.FORCE_SUB_CHANNEL.replace('@', '')}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_text = """
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

**Examples:**
```
/bypass https://bit.ly/abc123
B https://tinyurl.com/xyz
/redeem ABC123XYZ
/reset RESET_KEY_123
```

**Premium Benefits:**
✅ Unlimited daily bypasses
✅ Priority processing
✅ Access to all bypass methods
✅ No waiting time

Need more help? Contact admin.
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


# ==================== BYPASS COMMANDS ====================

@rate_limit(calls=5, period=60)
async def bypass_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /bypass command"""
    user = update.effective_user
    
    # Check force subscribe
    force_sub_check = await check_force_sub(update, context)
    if not force_sub_check:
        return
    
    # Check group permission
    group_check = await check_group_permission(update, context)
    if not group_check:
        return
    
    # Get URL from command
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide a link!**\n\n"
            "Usage: `/bypass <link>`\n"
            "Example: `/bypass https://bit.ly/abc123`",
            parse_mode='Markdown'
        )
        return
    
    url = context.args[0]
    await _process_bypass(update, context, url)


async def handle_bypass_shortcut(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle B <link> shortcut"""
    # Check force subscribe
    force_sub_check = await check_force_sub(update, context)
    if not force_sub_check:
        return
    
    # Check group permission
    group_check = await check_group_permission(update, context)
    if not group_check:
        return
    
    # Extract URL from message
    text = update.message.text
    url = extract_url(text)
    
    if not url:
        await update.message.reply_text(
            "❌ **No valid link found!**\n\n"
            "Please send: `B <link>`",
            parse_mode='Markdown'
        )
        return
    
    await _process_bypass(update, context, url)


async def _process_bypass(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    url: str
) -> None:
    """Process bypass request"""
    user = update.effective_user
    db = context.bot_data['db']
    
    # Validate URL
    if not is_valid_url(url):
        await update.message.reply_text(
            "❌ **Invalid URL!**\n\n"
            "Please provide a valid link starting with http:// or https://",
            parse_mode='Markdown'
        )
        return
    
    # Get user data
    user_data = await db.get_user(user.id)
    if not user_data:
        await update.message.reply_text(
            "❌ **Please start the bot first!**\n\n"
            "Send `/start` to get started.",
            parse_mode='Markdown'
        )
        return
    
    # Check if user can bypass
    if not user_data.can_bypass():
        remaining_time = format_time_remaining(
            user_data.last_bypass_time + timedelta(hours=1)
            if user_data.last_bypass_time else datetime.utcnow()
        )
        
        await update.message.reply_text(
            f"⏳ **Limit Reached!**\n\n"
            f"You've used all your daily bypasses.\n"
            f"Limit resets in: {remaining_time}\n\n"
            f"💎 **Upgrade to Premium** for unlimited bypasses!\n"
            f"Use `/premium` to learn more.",
            parse_mode='Markdown'
        )
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "🔍 **Analyzing link...**\n"
        f"URL: `{url}`\n\n"
        "Please wait...",
        parse_mode='Markdown'
    )
    
    try:
        # Get bypass manager
        from bypass.bypass_manager import BypassManager
        bypass_manager = BypassManager(db)
        
        # Attempt bypass
        result = await bypass_manager.bypass(url)
        
        if result.success and result.url:
            # Update user stats
            user_data.increment_bypass()
            await db.update_user(user_data)
            
            # Update stats
            await db.increment_stat('total_bypasses')
            
            # Build success message
            methods_tried = result.metadata.get('attempts', [])
            method_info = f"✅ **Method:** `{result.method}`"
            
            if len(methods_tried) > 1:
                method_info += f"\n🔄 **Tried:** {len(methods_tried)} methods"
            
            bypass_text = f"""
🎉 **Link Bypassed Successfully!**

🔗 **Original:** `{url}`
✨ **Bypassed:** `{result.url}`

{method_info}
⏱️ **Time:** {result.execution_time:.2f}s

**Your Stats:**
📊 Today: {user_data.bypass_count_today}/{user_data.daily_limit}
📈 Total: {user_data.bypass_count_total}
"""
            
            # Add keyboard
            keyboard = [
                [
                    InlineKeyboardButton("🔗 Open Link", url=result.url),
                    InlineKeyboardButton("📋 Copy", callback_data=f"copy:{result.url}")
                ],
                [
                    InlineKeyboardButton("🔄 Bypass Another", callback_data="bypass")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                bypass_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        else:
            # Bypass failed
            error_text = f"""
❌ **Bypass Failed!**

🔗 **URL:** `{url}`

**Error:**
{result.error_message or 'Unknown error'}

**What you can do:**
• Check if the link is valid
• Try again later
• Report with `/report {url}`
• Request support with `/request {url}`
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("📢 Report Issue", callback_data=f"report:{url}"),
                    InlineKeyboardButton("🔄 Try Again", callback_data=f"retry:{url}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                error_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    except Exception as e:
        logger.error(f"Bypass error: {e}")
        await processing_msg.edit_text(
            f"❌ **Error processing link!**\n\n"
            f"Please try again later or report this issue.",
            parse_mode='Markdown'
        )


# ==================== PREMIUM COMMANDS ====================

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /premium command"""
    user = update.effective_user
    db = context.bot_data['db']
    
    user_data = await db.get_user(user.id)
    
    if user_data and user_data.is_premium_active():
        # User is premium
        time_remaining = user_data.premium_expiry - datetime.utcnow()
        days = time_remaining.days
        hours = time_remaining.seconds // 3600
        
        premium_text = f"""
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
    else:
        # User is not premium
        premium_text = f"""
💎 **Upgrade to Premium!**

**Current Plan:** Free
**Daily Limit:** {premium_config.FREE_DAILY_LIMIT} bypasses

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
• Each referral = {premium_config.REFERRAL_REWARD_DAYS} days premium!

Contact admin for more info.
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🎁 Get Access Token", url=f"https://t.me/{(await context.bot.get_me()).username}?start=premium")
        ],
        [
            InlineKeyboardButton("👥 Referral Program", callback_data="referral")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        premium_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command"""
    user = update.effective_user
    db = context.bot_data['db']
    
    user_data = await db.get_user(user.id)
    
    if not user_data:
        await update.message.reply_text(
            "❌ **Please start the bot first!**\n\n"
            "Send `/start` to get started.",
            parse_mode='Markdown'
        )
        return
    
    # Calculate remaining bypasses
    remaining = user_data.get_remaining_bypasses()
    remaining_text = "Unlimited" if remaining == float('inf') else str(remaining)
    
    # Premium status
    premium_status = "✅ Active" if user_data.is_premium_active() else "❌ Inactive"
    
    # Progress bar for daily limit
    if not user_data.is_premium_active():
        progress = create_progress_bar(
            user_data.bypass_count_today,
            user_data.daily_limit
        )
    else:
        progress = "✨ Unlimited"
    
    stats_text = f"""
📊 **Your Statistics**

**Account Info:**
👤 Name: {user_data.first_name or 'N/A'}
🆔 ID: `{user_data.user_id}`
💎 Premium: {premium_status}

**Usage Today:**
📈 Bypassed: {user_data.bypass_count_today}/{user_data.daily_limit}
{progress}
🔢 Remaining: {remaining_text}

**Total Stats:**
📊 Total Bypasses: {user_data.bypass_count_total}

**Referral:**
👥 Referrals: {user_data.referral_count}
🎁 Earned Days: {user_data.referral_earned_days}

**Your Referral Code:**
`{user_data.referral_code}`
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🔗 Get Referral Link", callback_data="referral")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /referral command"""
    user = update.effective_user
    db = context.bot_data['db']
    
    user_data = await db.get_user(user.id)
    
    if not user_data:
        await update.message.reply_text(
            "❌ **Please start the bot first!**\n\n"
            "Send `/start` to get started.",
            parse_mode='Markdown'
        )
        return
    
    # Generate referral link
    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user.id}"
    
    referral_text = f"""
👥 **Referral Program**

**Your Referral Link:**
`{referral_link}`

**Share this link with friends!**

**Rewards:**
🎁 Each friend who joins = **{premium_config.REFERRAL_REWARD_DAYS} days premium**
📊 Your Referrals: {user_data.referral_count}
💰 Total Earned: {user_data.referral_earned_days} days

**How it works:**
1. Share your link
2. Friends click and start bot
3. You get premium days automatically!

**Maximum:** {premium_config.REFERRAL_MAX_REWARD} days from referrals
"""
    
    keyboard = [
        [
            InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={referral_link}&text=Check%20out%20this%20awesome%20link%20bypass%20bot!")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        referral_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /redeem command"""
    user = update.effective_user
    db = context.bot_data['db']
    
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide a token!**\n\n"
            "Usage: `/redeem <token>`\n"
            "Example: `/redeem ABC123XYZ`",
            parse_mode='Markdown'
        )
        return
    
    token = context.args[0].strip().upper()
    
    # Get token from database
    token_data = await db.get_access_token(token)
    
    if not token_data:
        await update.message.reply_text(
            "❌ **Invalid or expired token!**\n\n"
            "Please check your token and try again.",
            parse_mode='Markdown'
        )
        return
    
    # Get user data
    user_data = await db.get_user(user.id)
    if not user_data:
        await update.message.reply_text(
            "❌ **Please start the bot first!**\n\n"
            "Send `/start` to get started.",
            parse_mode='Markdown'
        )
        return
    
    # Apply premium
    duration_days = token_data.duration_days
    
    if not user_data.is_premium:
        user_data.is_premium = True
        user_data.premium_start = datetime.utcnow()
        user_data.premium_expiry = datetime.utcnow() + timedelta(days=duration_days)
    else:
        # Extend existing premium
        user_data.premium_expiry += timedelta(days=duration_days)
    
    # Mark token as used
    await db.use_access_token(token, user.id)
    
    # Update user
    await db.update_user(user_data)
    
    await update.message.reply_text(
        f"🎉 **Token Redeemed Successfully!**\n\n"
        f"✅ Premium activated for {token_data.get_duration_text()}\n"
        f"💎 Premium status: Active\n\n"
        f"Thank you for upgrading! Enjoy unlimited bypasses! 🚀",
        parse_mode='Markdown'
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reset command"""
    user = update.effective_user
    db = context.bot_data['db']
    
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide a reset key!**\n\n"
            "Usage: `/reset <key>`\n"
            "Example: `/reset RESET_KEY_123`",
            parse_mode='Markdown'
        )
        return
    
    key = context.args[0].strip().upper()
    
    # Get reset key from database
    key_data = await db.get_reset_key(key)
    
    if not key_data:
        await update.message.reply_text(
            "❌ **Invalid or expired reset key!**\n\n"
            "Please check your key and try again.",
            parse_mode='Markdown'
        )
        return
    
    # Get user data
    user_data = await db.get_user(user.id)
    if not user_data:
        await update.message.reply_text(
            "❌ **Please start the bot first!**\n\n"
            "Send `/start` to get started.",
            parse_mode='Markdown'
        )
        return
    
    # Reset user limits
    user_data.bypass_count_today = 0
    user_data.last_reset_date = datetime.utcnow()
    
    # Mark key as used
    await db.use_reset_key(key, user.id)
    
    # Update user
    await db.update_user(user_data)
    
    await update.message.reply_text(
        f"🔄 **Limits Reset Successfully!**\n\n"
        f"✅ Your daily bypass limit has been reset!\n"
        f"📊 You now have {user_data.daily_limit} bypasses available.\n\n"
        f"Happy bypassing! 🚀",
        parse_mode='Markdown'
    )


# ==================== FEEDBACK COMMANDS ====================

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /report command"""
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide details!**\n\n"
            "Usage: `/report <link>`\n"
            "Example: `/report https://bit.ly/broken-link`",
            parse_mode='Markdown'
        )
        return
    
    url = context.args[0]
    
    # Send to admin
    report_text = f"""
🚨 **New Error Report**

**From:** {user.mention_html()}
**User ID:** `{user.id}`
**URL:** `{url}`
**Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
    
    # Send to log channel
    if bot_config.LOG_CHANNEL:
        try:
            await context.bot.send_message(
                chat_id=bot_config.LOG_CHANNEL,
                text=report_text,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send report to log channel: {e}")
    
    # Send to admin PM
    for admin_id in bot_config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=report_text,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send report to admin {admin_id}: {e}")
    
    await update.message.reply_text(
        "✅ **Report sent!**\n\n"
        "Thank you for helping us improve the bot!\n"
        "We'll look into this issue.",
        parse_mode='Markdown'
    )


async def request_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /request command"""
    user = update.effective_user
    db = context.bot_data['db']
    
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide a site URL!**\n\n"
            "Usage: `/request <site_url>`\n"
            "Example: `/request https://new-shortener.com`",
            parse_mode='Markdown'
        )
        return
    
    site_url = context.args[0]
    
    # Create site request
    request = SiteRequest(
        user_id=user.id,
        site_url=site_url,
        status='pending'
    )
    
    await db.create_site_request(request)
    
    # Notify admin
    request_text = f"""
📢 **New Site Request**

**From:** {user.mention_html()}
**User ID:** `{user.id}`
**Site:** `{site_url}`
**Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
    
    for admin_id in bot_config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=request_text,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send request to admin {admin_id}: {e}")
    
    await update.message.reply_text(
        "✅ **Request submitted!**\n\n"
        "Thank you for your suggestion!\n"
        "We'll review and add support for this site.",
        parse_mode='Markdown'
    )


async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /feedback command"""
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide your feedback!**\n\n"
            "Usage: `/feedback <message>`\n"
            "Example: `/feedback Great bot! Love the features.`",
            parse_mode='Markdown'
        )
        return
    
    feedback_text = ' '.join(context.args)
    
    # Send to admin
    feedback_msg = f"""
💬 **New Feedback**

**From:** {user.mention_html()}
**User ID:** `{user.id}`
**Message:**
{feedback_text}

**Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
    
    for admin_id in bot_config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=feedback_msg,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send feedback to admin {admin_id}: {e}")
    
    await update.message.reply_text(
        "✅ **Feedback sent!**\n\n"
        "Thank you for your feedback! We appreciate it! 🙏",
        parse_mode='Markdown'
    )


# ==================== MESSAGE HANDLER ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages"""
    # Check if message contains a URL
    text = update.message.text
    
    if is_valid_url(text):
        # User sent just a URL, treat as bypass request
        await _process_bypass(update, context, text)
    else:
        # Unknown message
        await update.message.reply_text(
            "🤔 **I didn't understand that.**\n\n"
            "Send me a link to bypass, or use `/help` for available commands.",
            parse_mode='Markdown'
        )
