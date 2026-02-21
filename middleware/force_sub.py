"""
Force Subscribe Middleware
===========================
Ensure users join required channels/groups before using the bot.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import bot_config
from utils.logger import get_logger

logger = get_logger(__name__)


async def check_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user has joined required channels.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        True if user has joined all required channels
    """
    user = update.effective_user
    
    # Skip for admins
    if user.id in bot_config.ADMIN_IDS:
        return True
    
    # Check force subscribe channel
    if bot_config.FORCE_SUB_CHANNEL:
        try:
            member = await context.bot.get_chat_member(
                chat_id=bot_config.FORCE_SUB_CHANNEL,
                user_id=user.id
            )
            
            if member.status in ['left', 'kicked']:
                # User not subscribed
                channel_name = bot_config.FORCE_SUB_CHANNEL.replace('@', '')
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📢 Join Channel",
                            url=f"https://t.me/{channel_name}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔄 Try Again",
                            callback_data="check_sub"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"👋 **Welcome {user.first_name}!**\n\n"
                    f"To use this bot, please join our channel first:\n"
                    f"📢 {bot_config.FORCE_SUB_CHANNEL}\n\n"
                    f"After joining, click **Try Again**!",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return False
                
        except Exception as e:
            logger.error(f"Force sub check failed: {e}")
            # Allow if we can't check
            return True
    
    # Check force subscribe group
    if bot_config.FORCE_SUB_GROUP:
        try:
            member = await context.bot.get_chat_member(
                chat_id=bot_config.FORCE_SUB_GROUP,
                user_id=user.id
            )
            
            if member.status in ['left', 'kicked']:
                group_name = bot_config.FORCE_SUB_GROUP.replace('@', '')
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "👥 Join Group",
                            url=f"https://t.me/{group_name}"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"👋 **Welcome {user.first_name}!**\n\n"
                    f"To use this bot, please join our group:\n"
                    f"👥 {bot_config.FORCE_SUB_GROUP}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return False
                
        except Exception as e:
            logger.error(f"Force sub check failed: {e}")
            return True
    
    return True
