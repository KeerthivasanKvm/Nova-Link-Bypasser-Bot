"""
Decorators
==========
Custom decorators for handlers.
"""

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from config import bot_config
from utils.logger import get_logger

logger = get_logger(__name__)


def admin_required(func):
    """
    Decorator to require admin privileges.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        
        if user.id not in bot_config.ADMIN_IDS:
            await update.message.reply_text(
                "❌ **Access Denied!**\n\n"
                "You are not authorized to use this command.",
                parse_mode='Markdown'
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def owner_required(func):
    """
    Decorator to require owner privileges.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        
        if user.id != bot_config.OWNER_ID:
            await update.message.reply_text(
                "❌ **Access Denied!**\n\n"
                "Only the bot owner can use this command.",
                parse_mode='Markdown'
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def group_only(func):
    """
    Decorator to only allow command in groups.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        chat = update.effective_chat
        
        if chat.type == 'private':
            await update.message.reply_text(
                "❌ **This command only works in groups!**\n\n"
                "Please use this command in an authorized group.",
                parse_mode='Markdown'
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def private_only(func):
    """
    Decorator to only allow command in private chat.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        chat = update.effective_chat
        
        if chat.type != 'private':
            await update.message.reply_text(
                "❌ **This command only works in private chat!**\n\n"
                "Please message me directly to use this command.",
                parse_mode='Markdown'
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper
