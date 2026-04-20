"""
Entry point to start the bot.
Usage: python -m bot
"""

import logging
import os
import sys

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot.config import config
from bot.handlers import register_handlers
from bot.models.database import init_db
from bot.tasks.scheduler import setup_scheduler


def main():
    logger.info("Starting King Maker Bot...")
    logger.info(f"Version: 1.1.0-fixed")

    # Initialize database
    init_db()
    logger.info("Database initialized.")

    # Check bot token
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN missing in config!")
        sys.exit(1)

    from telegram.ext import Application

    application = Application.builder().token(config.BOT_TOKEN).build()

    # Register all handlers
    register_handlers(application)
    logger.info("Handlers registered.")

    # Setup scheduler
    setup_scheduler(application)
    logger.info("Scheduler started.")

    logger.info("Bot is running!")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
