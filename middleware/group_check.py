"""
Group Check Middleware
======================
Ensure bot is only used in allowed groups.
"""

from telegram import Update
from telegram.ext import ContextTypes

from config import bot_config
from utils.logger import get_logger

logger = get_logger(__name__)


async def check_group_permission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if bot can be used in this chat.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        True if allowed
    """
    chat = update.effective_chat
    user = update.effective_user
    
    # Always allow in private chat for admins
    if chat.type == 'private':
        if user.id in bot_config.ADMIN_IDS:
            return True
        
        # Check if PM is allowed for this user
        db = context.bot_data.get('db')
        if db:
            user_data = await db.get_user(user.id)
            if user_data and user_data.is_premium_active():
                return True
        
        # PM not allowed for regular users
        await update.message.reply_text(
            "❌ **Private messages not allowed!**\n\n"
            "Please use this bot in an authorized group.\n"
            "Contact admin for access.",
            parse_mode='Markdown'
        )
        return False
    
    # Allow admins in any group
    if user.id in bot_config.ADMIN_IDS:
        return True
    
    # Check if group is allowed
    db = context.bot_data.get('db')
    if db:
        is_allowed = await db.get_config(f'allowed_group_{chat.id}')
        if is_allowed:
            return True
    
    # Group not allowed
    await update.message.reply_text(
        "❌ **This group is not authorized!**\n\n"
        "Please contact admin to authorize this group.",
        parse_mode='Markdown'
    )
    return False
