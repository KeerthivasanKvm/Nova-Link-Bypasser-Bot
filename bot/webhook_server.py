"""
Webhook Server
==============
Flask server for handling Telegram webhook updates.
Designed for Render deployment.
"""

import asyncio
import json
import logging
from flask import Flask, request, jsonify, Response
from threading import Thread
from typing import Optional


def _run_async(coro):
    """Helper to run async code from sync Flask routes."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

from config import webhook_config, bot_config
from utils.logger import get_logger

logger = get_logger(__name__)


def create_webhook_app(bot_instance) -> Flask:
    """
    Create Flask app for webhook handling.
    
    Args:
        bot_instance: UltimateBypassBot instance
        
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        """Root endpoint - bot status"""
        return jsonify({
            'status': 'online',
            'bot': 'Ultimate Link Bypass Bot',
            'version': '2.0.0',
            'mode': 'webhook' if webhook_config.WEBHOOK_ENABLED else 'polling',
            'webhook_url': webhook_config.WEBHOOK_URL
        })
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'bot_initialized': bot_instance._initialized if bot_instance else False
        })
    
    @app.route(webhook_config.WEBHOOK_PATH, methods=['POST'])
    def webhook():
        """Telegram webhook endpoint"""
        if request.method == 'POST':
            try:
                # Get update data
                update_data = request.get_json(force=True)
                logger.debug(f"Received webhook update: {update_data.get('update_id')}")
                
                # Process update asynchronously
                _run_async(bot_instance.process_webhook_update(update_data))
                
                return Response('OK', status=200)
                
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                return Response('Error', status=500)
        
        return Response('Method not allowed', status=405)
    
    @app.route('/stats')
    def stats():
        """Get bot statistics (admin only)"""
        # Simple authentication check
        auth_header = request.headers.get('Authorization')
        if auth_header != f"Bearer {bot_config.BOT_TOKEN}":
            return Response('Unauthorized', status=401)
        
        try:
            db = bot_instance.get_db()
            stats_data = {
                'total_users': db.get_total_users(),
                'premium_users': db.get_premium_users_count(),
                'total_bypasses': db.get_total_bypasses(),
                'today_bypasses': db.get_today_bypasses(),
            }
            return jsonify(stats_data)
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/set-webhook', methods=['POST'])
    def set_webhook():
        """Set webhook manually (admin only)"""
        auth_header = request.headers.get('Authorization')
        if auth_header != f"Bearer {bot_config.BOT_TOKEN}":
            return Response('Unauthorized', status=401)
        
        try:
            url = request.json.get('url', webhook_config.WEBHOOK_URL)
            success = _run_async(bot_instance.setup_webhook(url))
            return jsonify({'success': success})
        except Exception as e:
            logger.error(f"Set webhook error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/delete-webhook', methods=['POST'])
    def delete_webhook():
        """Delete webhook (admin only)"""
        auth_header = request.headers.get('Authorization')
        if auth_header != f"Bearer {bot_config.BOT_TOKEN}":
            return Response('Unauthorized', status=401)
        
        try:
            _run_async(bot_instance.delete_webhook())
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Delete webhook error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """404 handler"""
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500 handler"""
        logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500
    
    return app


class WebhookServer:
    """Webhook server manager"""
    
    def __init__(self, bot_instance, host: str = '0.0.0.0', port: int = None):
        """
        Initialize webhook server.
        
        Args:
            bot_instance: UltimateBypassBot instance
            host: Host to bind to
            port: Port to listen on
        """
        self.bot = bot_instance
        self.host = host
        self.port = port or webhook_config.WEBHOOK_PORT
        self.app = create_webhook_app(bot_instance)
        self.server_thread: Optional[Thread] = None
        self._running = False
    
    def start(self) -> None:
        """Start webhook server in a separate thread"""
        if self._running:
            logger.warning("Webhook server already running")
            return
        
        logger.info(f"🌐 Starting webhook server on {self.host}:{self.port}")
        
        def run_server():
            self.app.run(
                host=self.host,
                port=self.port,
                threaded=True,
                debug=False,
                use_reloader=False
            )
        
        self.server_thread = Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self._running = True
        
        logger.info("✅ Webhook server started")
    
    def stop(self) -> None:
        """Stop webhook server"""
        if not self._running:
            return
        
        logger.info("🛑 Stopping webhook server...")
        self._running = False
        # Note: Flask server doesn't have a clean shutdown mechanism
        # The thread will be terminated when the main process exits
        logger.info("✅ Webhook server stopped")


async def run_webhook_mode(bot_instance) -> None:
    """
    Run bot in webhook mode.
    
    Args:
        bot_instance: UltimateBypassBot instance
    """
    # Initialize bot
    success = await bot_instance.initialize()
    if not success:
        logger.error("❌ Bot initialization failed!")
        return
    
    # Setup webhook
    webhook_url = f"{webhook_config.WEBHOOK_URL}{webhook_config.WEBHOOK_PATH}"
    success = await bot_instance.setup_webhook(webhook_url)
    if not success:
        logger.error("❌ Webhook setup failed!")
        return
    
    # Start webhook server
    server = WebhookServer(bot_instance)
    server.start()
    
    logger.info("🤖 Bot is running in webhook mode!")
    logger.info(f"🔗 Webhook URL: {webhook_url}")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Stopping bot...")


async def run_polling_mode(bot_instance) -> None:
    """
    Run bot in polling mode.
    
    Args:
        bot_instance: UltimateBypassBot instance
    """
    # Initialize bot
    success = await bot_instance.initialize()
    if not success:
        logger.error("❌ Bot initialization failed!")
        return
    
    # Delete any existing webhook
    await bot_instance.delete_webhook()
    
    # Start polling
    await bot_instance.start_polling()
    
    logger.info("🤖 Bot is running in polling mode!")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Stopping bot...")
        await bot_instance.stop_polling()
