"""
Ultimate Link Bypass Bot - Main Entry Point
===========================================
Start the bot in webhook or polling mode.
"""

import os
import sys
import asyncio
import argparse
from loguru import logger

from config import webhook_config, bot_config, validate_config
from bot.bot import get_bot
from bot.webhook_server import run_webhook_mode, run_polling_mode


def print_banner():
    """Print startup banner"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║      🔗 Ultimate Link Bypass Bot v2.0                         ║
║                                                               ║
║      Features:                                                ║
║      • 100+ Supported Sites                                   ║
║      • AI-Powered Bypass                                      ║
║      • Premium System                                         ║
║      • Firebase Database                                      ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_environment():
    """Check if all required environment variables are set"""
    validation = validate_config()
    
    if not all(validation.values()):
        print("\n❌ **Configuration Error!**\n")
        print("Missing required configuration:")
        
        for key, value in validation.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}")
        
        print("\nPlease check your .env file and try again.")
        return False
    
    return True


async def main():
    """Main entry point"""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Ultimate Link Bypass Bot')
    parser.add_argument(
        '--polling',
        action='store_true',
        help='Run in polling mode (default: webhook if configured)'
    )
    parser.add_argument(
        '--webhook',
        action='store_true',
        help='Run in webhook mode'
    )
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Get bot instance
    bot = get_bot()
    
    # Determine mode
    use_webhook = webhook_config.WEBHOOK_ENABLED and webhook_config.WEBHOOK_URL
    
    if args.polling:
        use_webhook = False
    elif args.webhook:
        use_webhook = True
    
    try:
        if use_webhook:
            logger.info("🌐 Starting in Webhook mode...")
            run_webhook_mode(bot)
        else:
            logger.info("🔄 Starting in Polling mode...")
            run_polling_mode(bot)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
