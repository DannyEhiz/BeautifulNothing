import asyncio
import logging

from fastapi.concurrency import run_in_threadpool

from . import config, db

log = logging.getLogger(__name__)


async def keepalive_loop() -> None:
    while True:
        try:
            if await run_in_threadpool(db.ping):
                log.info("keep-alive: database pinged")
        except Exception:
            log.exception("keep-alive: ping failed")
        await asyncio.sleep(config.KEEPALIVE_INTERVAL_SECONDS)
