# backend/logging_config.py
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime


# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Log file path with date
log_filename = logs_dir / f"chama_wallet_{datetime.now().strftime('%Y%m%d')}.log"


class CustomFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[94m',      # Blue
        'INFO': '\033[92m',       # Green
        'WARNING': '\033[93m',    # Yellow
        'ERROR': '\033[91m',      # Red
        'CRITICAL': '\033[95m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        # Add color to console logging
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"

        return super().format(record)


def get_request_correlation_id():
    """Generate or get correlation ID for request tracing"""
    import uuid
    return str(uuid.uuid4())


def setup_logging(log_level: str = "INFO", enable_file_logging: bool = True):
    """
    Configure comprehensive logging for the application
    """

    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set root logger level
    root_logger.setLevel(numeric_level)

    # Console handler with custom formatter
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)

    # File handler (if enabled)
    file_handler = None
    if enable_file_logging:
        file_handler = logging.handlers.RotatingFileHandler(
            log_filename,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)  # Log everything to file

    # Formatters
    console_formatter = CustomFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(process)d - %(thread)d - '
            '[%(filename)s:%(lineno)d] - %(correlation_id)s - %(tenant_id)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S.%f'
    )

    # Set formatters
    console_handler.setFormatter(console_formatter)
    if file_handler:
        file_handler.setFormatter(file_formatter)

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    if file_handler:
        root_logger.addHandler(file_handler)

    # Create logger for this application
    logger = logging.getLogger("chama_wallet")

    # Apply tenant correlation filter immediately for startup logs
    tenant_correlation_filter = TenantCorrelationFilter()
    for handler in root_logger.handlers:
        handler.addFilter(tenant_correlation_filter)

    # Log application startup
    logger.info("=" * 80)
    logger.info("Chama Wallet API starting up")
    logger.info(f"Log level: {log_level}")
    logger.info(f"File logging: {'enabled' if enable_file_logging else 'disabled'}")
    if enable_file_logging:
        logger.info(f"Log file: {log_filename}")
    logger.info("=" * 80)

    return logger


# Create a filter to add correlation ID and tenant ID to log records
class TenantCorrelationFilter(logging.Filter):
    """Filter that adds correlation ID and tenant information to all log records"""

    def filter(self, record):
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = get_request_correlation_id()

        # Try to get tenant ID from context vars or thread local storage
        if not hasattr(record, 'tenant_id'):
            try:
                # Import here to avoid circular imports
                from backend.database import current_tenant
                tenant_id = current_tenant.get()
                if tenant_id:
                    record.tenant_id = f"TENANT:{tenant_id}"
                else:
                    record.tenant_id = "GLOBAL"
            except (ImportError, AttributeError):
                # Fallback if context not available
                record.tenant_id = "UNKNOWN"

        return True


# Apply tenant and correlation filters to all loggers
tenant_filter = TenantCorrelationFilter()
logging.getLogger().addFilter(tenant_filter)
