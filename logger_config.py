import logging
import os
import sys

# Define the log file path
# If running as a PyInstaller executable, log to a file next to the executable.
# Otherwise, log to a file in the script's directory.
if hasattr(sys, '_MEIPASS'):
    # Running from a PyInstaller bundle
    LOG_FILE_PATH = os.path.join(os.path.dirname(sys.executable), 'app_log.log')
else:
    # Running as a script
    LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_log.log')

# Configure the logger
logger = logging.getLogger('WarThunderRPC')
logger.setLevel(logging.DEBUG) # Set overall logger level to DEBUG to capture all messages

# Create handlers (if not already created)
# This ensures we don't add duplicate handlers on subsequent imports/reloads
if not logger.handlers:
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    # File handler (always detailed)
    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG) # File should always capture DEBUG for detailed logs
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

# Optional: Disable propagation to avoid duplicate messages if root logger is also configured
logger.propagate = False

def set_console_logging_level(level):
    """
    Sets the logging level for the console output handler.
    Args:
        level: The logging level (e.g., logging.INFO, logging.DEBUG).
    """
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(level)
            break # Assuming only one StreamHandler for console output

# Initial default level for console output (can be overridden by GUI)
set_console_logging_level(logging.INFO)
