import logging
import os

# Configure structured enterprise logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ExampressSaaS")

def init_sentry(app):
    """
    Initializes Sentry error tracking for enterprise production monitoring.
    Requires SENTRY_DSN environment variable to be configured in production.
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FastApiIntegration()],
                traces_sample_rate=1.0,
                environment=os.getenv("ENVIRONMENT", "production")
            )
            logger.info("Sentry error tracking initialized successfully.")
        except ImportError:
            logger.warning("Sentry SDK not installed. Skipping error monitoring initialization.")
    else:
        logger.info("SENTRY_DSN not found in environment. Sentry monitoring is disabled in local mode.")