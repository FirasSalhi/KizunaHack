import logging
import sys

logger = logging.getLogger("farmlink")


def setup_logging(debug: bool = True) -> None:
    """Configure structured logging for the application."""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-7s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
