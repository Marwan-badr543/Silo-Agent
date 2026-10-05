from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

load_dotenv()

from api.channels.telegram_bot import build_telegram_bot  # noqa: E402
from api.core.objects_factory import ObjectsFactory  # noqa: E402
from api.routers.chat import router as chat_router  # noqa: E402

CHECKPOINT_DB = "silo_state.db"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the state database, build the agent once, and start the Telegram bot if a token is set."""
    async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB) as checkpointer:
        ObjectsFactory.init(checkpointer)
        bot = build_telegram_bot(ObjectsFactory.get_agent())
        if bot:
            await bot.initialize()
            await bot.start()
            await bot.updater.start_polling()
        yield
        if bot:
            await bot.updater.stop()
            await bot.stop()
            await bot.shutdown()


app = FastAPI(title="Silo API", lifespan=lifespan)
app.include_router(chat_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=7000, reload=False)
