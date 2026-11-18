"""Pipeline logging."""

import logging
from typing import cast

import structlog


def configure_logging(*, run_id: str, job: str) -> structlog.stdlib.BoundLogger:
	"""Configure JSON logging and return a logger bound to this run and job."""
	structlog.configure(
		processors=[
			structlog.stdlib.add_log_level,
			structlog.processors.TimeStamper(fmt="iso", utc=True),
			structlog.processors.JSONRenderer(),
		],
		wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
		logger_factory=structlog.PrintLoggerFactory(),
		cache_logger_on_first_use=False,
	)
	logger = structlog.get_logger().bind(run_id=run_id, job=job)
	return cast(structlog.stdlib.BoundLogger, logger)
