import asyncio
import logging

from app import config, db

log = logging.getLogger(__name__)


async def keepalive_loop() -> None:
    while True:
        try:
            if await db.ping():
                log.info("keep-alive: database pinged")
        except Exception:
            log.exception("keep-alive: ping failed")
        await asyncio.sleep(config.KEEPALIVE_INTERVAL_SECONDS)
