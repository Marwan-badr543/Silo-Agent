import os

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from agent.silo_agent import SiloAgent

TELEGRAM_MAX_LENGTH = 4096


def build_telegram_bot(agent: SiloAgent) -> Application | None:
    """Telegram bot that answers every text message with the agent. None if no token."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return None

    async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
        answer = await agent.ask(update.message.text, thread_id=f"telegram-{update.effective_chat.id}")
        await update.message.reply_text(answer[:TELEGRAM_MAX_LENGTH])

    bot = Application.builder().token(token).build()
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    return bot
