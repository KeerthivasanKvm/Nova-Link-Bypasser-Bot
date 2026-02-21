"""
Callback Handlers
=================
Handle inline keyboard callbacks.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.logger import get_logger

logger = get_logger(__name__)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "bypass":
        await query.edit_message_text(
            "🔓 **Bypass Link**\n\n"
            "Send me a link to bypass:\n"
            "• `/bypass <link>`\n"
            "• Or just `B <link>`",
            parse_mode='Markdown'
        )
    
    elif data == "premium":
        from handlers.commands import premium_command
        # Create fake update for premium command
        await premium_command(update, context)
    
    elif data == "stats":
        from handlers.commands import stats_command
        await stats_command(update, context)
    
    elif data == "help":
        from handlers.commands import help_command
        await help_command(update, context)
    
    elif data == "referral":
        from handlers.commands import referral_command
        await referral_command(update, context)
    
    elif data.startswith("copy:"):
        url = data.split(":", 1)[1]
        await query.edit_message_text(
            f"📋 **Copy this link:**\n\n"
            f"`{url}`\n\n"
            f"Tap to copy!",
            parse_mode='Markdown'
        )
    
    elif data.startswith("report:"):
        url = data.split(":", 1)[1]
        await query.edit_message_text(
            f"📢 **Report Issue**\n\n"
            f"URL: `{url}`\n\n"
            f"Use `/report {url}` to submit a report.",
            parse_mode='Markdown'
        )
    
    elif data.startswith("retry:"):
        url = data.split(":", 1)[1]
        from handlers.commands import _process_bypass
        await _process_bypass(update, context, url)
    
    elif data.startswith("admin_"):
        # Admin callbacks
        await handle_admin_callbacks(update, context)
    
    else:
        await query.edit_message_text(
            "❓ **Unknown action**\n\n"
            "Please use the menu commands.",
            parse_mode='Markdown'
        )


async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin-specific callbacks"""
    query = update.callback_query
    data = query.data
    user = update.effective_user
    
    from config import bot_config
    
    # Check if user is admin
    if user.id not in bot_config.ADMIN_IDS:
        await query.edit_message_text(
            "❌ **Access Denied!**\n\n"
            "You are not authorized to use this feature.",
            parse_mode='Markdown'
        )
        return
    
    if data == "admin_stats":
        db = context.bot_data['db']
        
        total_users = await db.get_total_users()
        premium_users = await db.get_premium_users_count()
        total_bypasses = await db.get_total_bypasses()
        today_bypasses = await db.get_today_bypasses()
        
        stats_text = f"""
📊 **Bot Statistics**

**Users:**
👥 Total Users: {total_users}
💎 Premium Users: {premium_users}

**Bypasses:**
🔓 Total: {total_bypasses}
📈 Today: {today_bypasses}

**Server:**
✅ Status: Online
🔄 Mode: {'Webhook' if context.bot_data.get('webhook', False) else 'Polling'}
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
            [InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif data == "admin_panel":
        from admin.admin_commands import admin_panel
        await admin_panel(update, context)
    
    elif data == "admin_broadcast":
        await query.edit_message_text(
            "📢 **Broadcast Message**\n\n"
            "Use the command:\n"
            "`/broadcast <message>`\n\n"
            "Example:\n"
            "`/broadcast Hello everyone!`",
            parse_mode='Markdown'
        )
    
    elif data == "admin_tokens":
        await query.edit_message_text(
            "🎟️ **Token Management**\n\n"
            "**Commands:**\n"
            "• `/generate_token 1h` - 1 hour\n"
            "• `/generate_token 1d` - 1 day\n"
            "• `/generate_token 7d` - 7 days\n"
            "• `/generate_token 30d` - 30 days\n"
            "• `/revoke_token <token>` - Revoke token",
            parse_mode='Markdown'
        )
    
    elif data == "admin_domains":
        await query.edit_message_text(
            "🌐 **Domain Management**\n\n"
            "**Commands:**\n"
            "• `/add_domain <domain>` - Add allowed domain\n"
            "• `/remove_domain <domain>` - Remove domain\n"
            "• `/block_domain <domain>` - Block domain",
            parse_mode='Markdown'
        )
    
    elif data == "admin_reset_keys":
        await query.edit_message_text(
            "🔄 **Reset Key Management**\n\n"
            "**Commands:**\n"
            "• `/generate_reset_key` - Generate universal reset key\n"
            "• `/set_limit <number>` - Set free user daily limit",
            parse_mode='Markdown'
        )
    
    elif data == "admin_settings":
        await query.edit_message_text(
            "⚙️ **Bot Settings**\n\n"
            "**Commands:**\n"
            "• `/toggle_referral` - Toggle referral system\n"
            "• `/grant_access <group_id>` - Grant group access\n"
            "• `/revoke_access <group_id>` - Revoke group access\n"
            "• `/config` - View configuration",
            parse_mode='Markdown'
        )
