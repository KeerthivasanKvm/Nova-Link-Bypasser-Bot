"""
Ultimate Bypass Bot - Main Bot Class
====================================
Core bot initialization and management.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from telegram import Update, Bot
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from config import bot_config, webhook_config
from database.firebase_db import FirebaseDB
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)


class UltimateBypassBot:
    """
    Main bot class for Ultimate Link Bypass Bot.
    Handles initialization, webhook/polling modes, and application lifecycle.
    """
    
    def __init__(self):
        """Initialize the bot"""
        self.application: Optional[Application] = None
        self.bot: Optional[Bot] = None
        self.db: Optional[FirebaseDB] = None
        self._initialized = False
        
    async def initialize(self) -> bool:
        """
        Initialize bot components.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info("🚀 Initializing Ultimate Bypass Bot...")
            
            # Validate configuration
            if not bot_config.BOT_TOKEN:
                logger.error("❌ BOT_TOKEN not configured!")
                return False
                
            # Initialize Firebase
            logger.info("📦 Initializing Firebase...")
            self.db = FirebaseDB()
            if not await self.db.initialize():
                logger.error("❌ Firebase initialization failed!")
                return False
            logger.info("✅ Firebase initialized")
            
            # Build application
            logger.info("🤖 Building Telegram application...")
            self.application = (
                ApplicationBuilder()
                .token(bot_config.BOT_TOKEN)
                .build()
            )
            self.bot = self.application.bot
            
            # Store db in bot_data for access in handlers
            self.application.bot_data['db'] = self.db
            self.application.bot_data['bot_instance'] = self
            
            # Register handlers
            await self._register_handlers()
            
            self._initialized = True
            logger.info("✅ Bot initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Bot initialization failed: {e}")
            return False
    
    async def _register_handlers(self) -> None:
        """Register all command and message handlers"""
        from handlers.commands import (
            start_command, help_command, bypass_command,
            premium_command, stats_command, referral_command,
            redeem_command, reset_command, report_command,
            request_command, feedback_command
        )
        from handlers.messages import handle_message, handle_bypass_shortcut
        from handlers.callbacks import button_callback
        from admin.admin_commands import (
            admin_panel, generate_token_command, revoke_token_command,
            add_domain_command, remove_domain_command, block_domain_command,
            generate_reset_key_command, set_limit_command, toggle_referral_command,
            grant_access_command, revoke_access_command, broadcast_command,
            stats_all_command, config_command, logs_command
        )
        
        logger.info("📝 Registering handlers...")
        
        # User commands
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("bypass", bypass_command))
        self.application.add_handler(CommandHandler("premium", premium_command))
        self.application.add_handler(CommandHandler("stats", stats_command))
        self.application.add_handler(CommandHandler("referral", referral_command))
        self.application.add_handler(CommandHandler("redeem", redeem_command))
        self.application.add_handler(CommandHandler("reset", reset_command))
        self.application.add_handler(CommandHandler("report", report_command))
        self.application.add_handler(CommandHandler("request", request_command))
        self.application.add_handler(CommandHandler("feedback", feedback_command))
        
        # Admin commands
        self.application.add_handler(CommandHandler("admin", admin_panel))
        self.application.add_handler(CommandHandler("generate_token", generate_token_command))
        self.application.add_handler(CommandHandler("revoke_token", revoke_token_command))
        self.application.add_handler(CommandHandler("add_domain", add_domain_command))
        self.application.add_handler(CommandHandler("remove_domain", remove_domain_command))
        self.application.add_handler(CommandHandler("block_domain", block_domain_command))
        self.application.add_handler(CommandHandler("generate_reset_key", generate_reset_key_command))
        self.application.add_handler(CommandHandler("set_limit", set_limit_command))
        self.application.add_handler(CommandHandler("toggle_referral", toggle_referral_command))
        self.application.add_handler(CommandHandler("grant_access", grant_access_command))
        self.application.add_handler(CommandHandler("revoke_access", revoke_access_command))
        self.application.add_handler(CommandHandler("broadcast", broadcast_command))
        self.application.add_handler(CommandHandler("stats_all", stats_all_command))
        self.application.add_handler(CommandHandler("config", config_command))
        self.application.add_handler(CommandHandler("logs", logs_command))
        
        # Callback queries
        self.application.add_handler(CallbackQueryHandler(button_callback))
        
        # Shortcut handlers (B <link>)
        self.application.add_handler(
            MessageHandler(
                filters.Regex(r'^[Bb]\s+https?://') & filters.TEXT & ~filters.COMMAND,
                handle_bypass_shortcut
            )
        )
        
        # General message handler
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                handle_message
            )
        )
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
        
        logger.info("✅ Handlers registered")
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
        logger.error(f"❌ Error occurred: {context.error}")
        
        # Log to admin
        try:
            error_message = f"""
❌ **Error Report**

**Error:** `{str(context.error)}`
**Update ID:** {update.update_id if update else 'N/A'}
**User:** {update.effective_user.id if update and update.effective_user else 'N/A'}
**Chat:** {update.effective_chat.id if update and update.effective_chat else 'N/A'}
"""
            if bot_config.LOG_CHANNEL:
                await context.bot.send_message(
                    chat_id=bot_config.LOG_CHANNEL,
                    text=error_message,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
    
    async def start_polling(self) -> None:
        """Start bot in polling mode"""
        if not self._initialized:
            logger.error("Bot not initialized!")
            return
            
        logger.info("🔄 Starting polling mode...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(
            drop_pending_updates=True,
            poll_interval=webhook_config.POLLING_INTERVAL
        )
        logger.info("✅ Bot is running in polling mode!")
    
    async def stop_polling(self) -> None:
        """Stop polling mode"""
        if self.application:
            logger.info("🛑 Stopping polling...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("✅ Polling stopped")
    
    async def setup_webhook(self, webhook_url: str) -> bool:
        """
        Setup webhook for the bot.
        
        Args:
            webhook_url: Full webhook URL
            
        Returns:
            bool: True if webhook set successfully
        """
        if not self._initialized:
            logger.error("Bot not initialized!")
            return False
            
        try:
            logger.info(f"🔗 Setting up webhook: {webhook_url}")
            await self.application.initialize()
            await self.application.start()
            
            # Set webhook
            await self.bot.set_webhook(
                url=webhook_url,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
            webhook_info = await self.bot.get_webhook_info()
            logger.info(f"✅ Webhook set: {webhook_info.url}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to set webhook: {e}")
            return False
    
    async def process_webhook_update(self, update_data: Dict[str, Any]) -> None:
        """
        Process webhook update.
        
        Args:
            update_data: Update data from Telegram
        """
        try:
            update = Update.de_json(update_data, self.bot)
            await self.application.process_update(update)
        except Exception as e:
            logger.error(f"❌ Failed to process webhook update: {e}")
    
    async def delete_webhook(self) -> None:
        """Delete webhook"""
        if self.bot:
            await self.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook deleted")
    
    def get_db(self) -> FirebaseDB:
        """Get database instance"""
        return self.db
    
    async def send_message(self, chat_id: int, text: str, **kwargs) -> None:
        """
        Send message wrapper.
        
        Args:
            chat_id: Target chat ID
            text: Message text
            **kwargs: Additional arguments
        """
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode='Markdown',
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to send message: {e}")


# Global bot instance
_bot_instance: Optional[UltimateBypassBot] = None


def get_bot() -> UltimateBypassBot:
    """Get or create bot instance"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = UltimateBypassBot()
    return _bot_instance
