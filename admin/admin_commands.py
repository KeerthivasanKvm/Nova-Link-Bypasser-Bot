"""
Admin Commands
==============
All admin-only commands for bot management.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import bot_config, premium_config, bypass_config, get_config_summary
from database.models import AccessToken, ResetKey
from utils.decorators import admin_required, owner_required
from utils.logger import get_logger

logger = get_logger(__name__)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin panel"""
    user = update.effective_user
    
    # Check if user is admin
    if user.id not in bot_config.ADMIN_IDS:
        await update.message.reply_text(
            "❌ **Access Denied!**\n\n"
            "You are not authorized to use this command.",
            parse_mode='Markdown'
        )
        return
    
    admin_text = f"""
🔐 **Admin Panel**

Welcome, {user.first_name}!

**Admin Commands:**
• `/generate_token <duration>` - Generate token
• `/revoke_token <token>` - Revoke token
• `/generate_reset_key` - Generate reset key
• `/add_domain <domain>` - Add domain
• `/remove_domain <domain>` - Remove domain
• `/block_domain <domain>` - Block domain
• `/set_limit <number>` - Set free limit
• `/toggle_referral` - Toggle referral
• `/grant_access <group_id>` - Grant group access
• `/revoke_access <group_id>` - Revoke access
• `/broadcast <message>` - Broadcast
• `/stats_all` - View all stats
• `/config` - View config
• `/logs` - View logs

Use the buttons below for quick access:
"""
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton("🎟️ Tokens", callback_data="admin_tokens"),
            InlineKeyboardButton("🌐 Domains", callback_data="admin_domains")
        ],
        [
            InlineKeyboardButton("🔄 Reset Keys", callback_data="admin_reset_keys"),
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        admin_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


@admin_required
async def generate_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate access token"""
    user = update.effective_user
    db = context.bot_data['db']
    
    if not context.args:
        await update.message.reply_text(
            "❌ **Please specify duration!**\n\n"
            "Usage:\n"
            "• `/generate_token 1h` - 1 hour\n"
            "• `/generate_token 1d` - 1 day\n"
            "• `/generate_token 7d` - 7 days\n"
            "• `/generate_token 30d` - 30 days",
            parse_mode='Markdown'
        )
        return
    
    duration_str = context.args[0].lower()
    
    # Parse duration
    if duration_str.endswith('h'):
        duration_days = int(duration_str[:-1]) / 24
    elif duration_str.endswith('d'):
        duration_days = int(duration_str[:-1])
    elif duration_str.endswith('m'):
        duration_days = int(duration_str[:-1]) * 30
    else:
        await update.message.reply_text(
            "❌ **Invalid duration format!**\n\n"
            "Use: `1h`, `1d`, `7d`, `30d`",
            parse_mode='Markdown'
        )
        return
    
    # Generate token
    token = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
    
    # Create token object
    token_obj = AccessToken(
        token=token,
        duration_days=duration_days,
        created_by=user.id
    )
    
    # Save to database
    await db.create_access_token(token_obj)
    
    await update.message.reply_text(
        f"🎟️ **Access Token Generated!**\n\n"
        f"**Token:** `{token}`\n"
        f"**Duration:** {token_obj.get_duration_text()}\n"
        f"**Created by:** {user.id}\n\n"
        f"**Usage:** `/redeem {token}`\n\n"
        f"⚠️ This is a one-time use token!",
        parse_mode='Markdown'
    )


@admin_required
async def revoke_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Revoke access token"""
    db = context.bot_data['db']
    
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide a token!**\n\n"
            "Usage: `/revoke_token <token>`",
            parse_mode='Markdown'
        )
        return
    
    token = context.args[0].strip().upper()
    
    # Delete token
    success = await db.delete_access_token(token)
    
    if success:
        await update.message.reply_text(
            f"✅ **Token revoked successfully!**\n\n"
            f"Token `{token}` has been revoked.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ **Token not found!**\n\n"
            "The token may have already been revoked or used.",
            parse_mode='Markdown'
        )


@admin_required
async def generate_reset_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate universal reset key"""
    user = update.effective_user
    db = context.bot_data['db']
    
    # Generate key
    key = 'RESET_' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    
    # Get optional max uses
    max_uses = 1  # Default: one-time use
    if context.args:
        try:
            max_uses = int(context.args[0])
        except ValueError:
            pass
    
    # Get optional expiry
    expires_hours = 24  # Default: 24 hours
    if len(context.args) > 1:
        try:
            expires_hours = int(context.args[1])
        except ValueError:
            pass
    
    # Create reset key
    reset_key = ResetKey(
        key=key,
        created_by=user.id,
        max_uses=max_uses,
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours)
    )
    
    # Save to database
    await db.create_reset_key(reset_key)
    
    await update.message.reply_text(
        f"🔄 **Reset Key Generated!**\n\n"
        f"**Key:** `{key}`\n"
        f"**Max Uses:** {max_uses}\n"
        f"**Expires:** {expires_hours} hours\n\n"
        f"**Usage:** `/reset {key}`\n\n"
        f"⚠️ This key is universal - anyone can use it!",
        parse_mode='Markdown'
    )


@admin_required
async def add_domain_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add allowed domain"""
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide a domain!**\n\n"
            "Usage: `/add_domain <domain>`\n"
            "Example: `/add_domain bit.ly`",
            parse_mode='Markdown'
        )
        return
    
    domain = context.args[0].lower()
    
    # Add to config
    if domain not in bypass_config.ALLOWED_SHORTENERS:
        bypass_config.ALLOWED_SHORTENERS.append(domain)
        await update.message.reply_text(
            f"✅ **Domain added!**\n\n"
            f"`{domain}` has been added to allowed domains.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"⚠️ **Domain already exists!**\n\n"
            f"`{domain}` is already in the allowed list.",
            parse_mode='Markdown'
        )


@admin_required
async def remove_domain_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove allowed domain"""
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide a domain!**\n\n"
            "Usage: `/remove_domain <domain>`",
            parse_mode='Markdown'
        )
        return
    
    domain = context.args[0].lower()
    
    # Remove from config
    if domain in bypass_config.ALLOWED_SHORTENERS:
        bypass_config.ALLOWED_SHORTENERS.remove(domain)
        await update.message.reply_text(
            f"✅ **Domain removed!**\n\n"
            f"`{domain}` has been removed from allowed domains.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"⚠️ **Domain not found!**\n\n"
            f"`{domain}` is not in the allowed list.",
            parse_mode='Markdown'
        )


@admin_required
async def block_domain_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Block domain"""
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide a domain!**\n\n"
            "Usage: `/block_domain <domain>`\n"
            "Example: `/block_domain malware.com`",
            parse_mode='Markdown'
        )
        return
    
    domain = context.args[0].lower()
    
    # Add to blocked list
    if domain not in bypass_config.BLOCKED_DOMAINS:
        bypass_config.BLOCKED_DOMAINS.append(domain)
        await update.message.reply_text(
            f"🚫 **Domain blocked!**\n\n"
            f"`{domain}` has been added to blocked domains.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"⚠️ **Domain already blocked!**\n\n"
            f"`{domain}` is already in the blocked list.",
            parse_mode='Markdown'
        )


@admin_required
async def set_limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set free user daily limit"""
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide a number!**\n\n"
            "Usage: `/set_limit <number>`\n"
            "Example: `/set_limit 10`",
            parse_mode='Markdown'
        )
        return
    
    try:
        limit = int(context.args[0])
        if limit < 1:
            raise ValueError("Limit must be at least 1")
        
        # Update config
        premium_config.FREE_DAILY_LIMIT = limit
        
        await update.message.reply_text(
            f"✅ **Limit updated!**\n\n"
            f"Free users can now bypass **{limit}** links per day.",
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid number!**\n\n"
            "Please provide a valid positive number.",
            parse_mode='Markdown'
        )


@owner_required
async def toggle_referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle referral system"""
    # Toggle
    premium_config.REFERRAL_ENABLED = not premium_config.REFERRAL_ENABLED
    
    status = "✅ Enabled" if premium_config.REFERRAL_ENABLED else "❌ Disabled"
    
    await update.message.reply_text(
        f"🔄 **Referral System**\n\n"
        f"Status: {status}",
        parse_mode='Markdown'
    )


@admin_required
async def grant_access_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Grant group access"""
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide a group ID!**\n\n"
            "Usage: `/grant_access <group_id>`\n"
            "Example: `/grant_access -1001234567890`",
            parse_mode='Markdown'
        )
        return
    
    try:
        group_id = int(context.args[0])
        
        # Store in database
        db = context.bot_data['db']
        await db.set_config(f'allowed_group_{group_id}', True)
        
        await update.message.reply_text(
            f"✅ **Access granted!**\n\n"
            f"Group `{group_id}` can now use the bot.",
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid group ID!**\n\n"
            "Please provide a valid numeric group ID.",
            parse_mode='Markdown'
        )


@admin_required
async def revoke_access_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Revoke group access"""
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide a group ID!**\n\n"
            "Usage: `/revoke_access <group_id>`",
            parse_mode='Markdown'
        )
        return
    
    try:
        group_id = int(context.args[0])
        
        # Remove from database
        db = context.bot_data['db']
        await db.set_config(f'allowed_group_{group_id}', False)
        
        await update.message.reply_text(
            f"✅ **Access revoked!**\n\n"
            f"Group `{group_id}` can no longer use the bot.",
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid group ID!**\n\n"
            "Please provide a valid numeric group ID.",
            parse_mode='Markdown'
        )


@admin_required
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast message to all users"""
    if not context.args:
        await update.message.reply_text(
            "❌ **Please provide a message!**\n\n"
            "Usage: `/broadcast <message>`\n"
            "Example: `/broadcast Hello everyone!`",
            parse_mode='Markdown'
        )
        return
    
    message = ' '.join(context.args)
    db = context.bot_data['db']
    
    # Get all users
    users = await db.get_all_users(limit=10000)
    
    # Send broadcast
    sent = 0
    failed = 0
    
    status_msg = await update.message.reply_text(
        f"📢 **Broadcast Started**\n\n"
        f"Message: {message[:100]}...\n"
        f"Target: {len(users)} users\n\n"
        f"Sending...",
        parse_mode='Markdown'
    )
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user.user_id,
                text=f"📢 **Broadcast Message**\n\n{message}",
                parse_mode='Markdown'
            )
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send to {user.user_id}: {e}")
            failed += 1
    
    await status_msg.edit_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"Message: {message[:100]}...\n"
        f"✓ Sent: {sent}\n"
        f"✗ Failed: {failed}",
        parse_mode='Markdown'
    )


@admin_required
async def stats_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all statistics"""
    db = context.bot_data['db']
    
    # Get stats
    total_users = await db.get_total_users()
    premium_users = await db.get_premium_users_count()
    total_bypasses = await db.get_total_bypasses()
    today_bypasses = await db.get_today_bypasses()
    
    stats_text = f"""
📊 **Complete Bot Statistics**

**Users:**
👥 Total Users: {total_users:,}
💎 Premium Users: {premium_users:,}
🆓 Free Users: {total_users - premium_users:,}

**Bypasses:**
🔓 Total: {total_bypasses:,}
📈 Today: {today_bypasses:,}

**Configuration:**
📊 Free Daily Limit: {premium_config.FREE_DAILY_LIMIT}
👥 Referral System: {'✅' if premium_config.REFERRAL_ENABLED else '❌'}
🌐 Allowed Domains: {len(bypass_config.ALLOWED_SHORTENERS)}
🚫 Blocked Domains: {len(bypass_config.BLOCKED_DOMAINS)}

**Server:**
✅ Status: Online
🔄 Mode: {'Webhook' if context.bot_data.get('webhook') else 'Polling'}
"""
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')


@admin_required
async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot configuration"""
    config_summary = get_config_summary()
    await update.message.reply_text(config_summary, parse_mode='Markdown')


@admin_required
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent error reports"""
    db = context.bot_data['db']
    
    # Get pending reports
    reports = await db.get_pending_error_reports()
    
    if not reports:
        await update.message.reply_text(
            "✅ **No pending error reports!**\n\n"
            "All caught up! 🎉",
            parse_mode='Markdown'
        )
        return
    
    # Show first 5 reports
    reports_text = "📋 **Pending Error Reports**\n\n"
    
    for i, report in enumerate(reports[:5], 1):
        reports_text += f"""
**{i}. Report #{report.report_id[:8]}**
👤 User: `{report.user_id}`
🔗 URL: `{report.url}`
📅 Date: {report.created_at.strftime('%Y-%m-%d %H:%M')}
"""
    
    if len(reports) > 5:
        reports_text += f"\n... and {len(reports) - 5} more reports"
    
    await update.message.reply_text(reports_text, parse_mode='Markdown')
