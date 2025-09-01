from loguru import logger
import sys

logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    colorize=True,
    enqueue=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)
