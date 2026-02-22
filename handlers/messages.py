"""
Message Handlers
================
Handle non-command messages.
"""

from telegram import Update
from telegram.ext import ContextTypes

from middleware.force_sub import check_force_sub
from middleware.group_check import check_group_permission
from utils.validators import is_valid_url, extract_url
from utils.logger import get_logger

logger = get_logger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages"""
    # Check if message contains a URL
    text = update.message.text
    
    if is_valid_url(text):
        # User sent just a URL, treat as bypass request
        from handlers.commands import _process_bypass
        await _process_bypass(update, context, text)
    else:
        # Unknown message
        await update.message.reply_text(
            "🤔 **I didn't understand that.**\n\n"
            "Send me a link to bypass, or use `/help` for available commands.",
            parse_mode='Markdown'
        )


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
    
    from handlers.commands import _process_bypass
    await _process_bypass(update, context, url)
