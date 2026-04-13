"""Entry point for AI Intel Hub."""

import logging
import sys
from pathlib import Path


def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("ai_intel_hub")

    try:
        from .ui.app import AIIntelHub
        app = AIIntelHub()
        logger.info("AI Intel Hub started")
        app.mainloop()
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
