"""Allowlisted JSON logs: no URLs, query strings, payloads, headers or secrets."""
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger('astrasynq')
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

def log(event, **fields):
    logger.info(json.dumps({'time': datetime.now(timezone.utc).isoformat(), 'event': event, **fields}, default=str))
