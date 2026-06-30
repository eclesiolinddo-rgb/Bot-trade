"""Signals engine stub.

Adapt the existing technical indicators (RSI/EMA/MACD/Bollinger) from
your other bots into this module. For now this is a minimal placeholder
that exposes an async API to detect signals.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


async def detect_signals_once():
    """Run one pass of detection and return list of signals (dicts)
    Each signal should contain: symbol, direction, score, meta
    """
    logger.debug("Detecting signals (stub)")
    # TODO: integrate real logic
    await asyncio.sleep(0.1)
    return []


async def run_continuous(publish_callback):
    """Continuously run the engine and call publish_callback(signal) for each new signal."""
    while True:
        signals = await detect_signals_once()
        for s in signals:
            await publish_callback(s)
        await asyncio.sleep(30)  # tune interval
