import logging
import logging.handlers
import sys
import yaml

def setup_logging():
    """Sets up logging based on the configuration file."""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: config.yaml not found. Please ensure the configuration file exists.")
        # Create a basic logger that only prints to console
        logger = logging.getLogger('wompus')
        logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.warning("config.yaml not found. Using basic console logging.")
        return logger


    log_config = config.get('LOGGING', {})
    enabled = log_config.get('ENABLED', False)
    
    logger = logging.getLogger('wompus')
    
    # Prevent duplicate handlers if this function is called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    if not enabled:
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
        # Set level higher than any standard level to effectively disable it
        logger.setLevel(logging.CRITICAL + 1)
        return logger

    log_level_str = log_config.get('LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if log_config.get('TO_CONSOLE', True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    log_file = log_config.get('FILE')
    if log_file:
        try:
            max_size = int(log_config.get('MAX_SIZE', 10000000))
            # Ensure max_size is a reasonable number
            if max_size <= 0:
                max_size = 10000000 # Default to 10MB if invalid
                logger.warning(f"Invalid MAX_SIZE in config.yaml. Defaulting to {max_size} bytes.")

            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_size, backupCount=5, encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid 'MAX_SIZE' in config.yaml. Must be an integer. File logging disabled. Error: {e}")
        except Exception as e:
            logger.error(f"Failed to create file handler for {log_file}. File logging disabled. Error: {e}")
        
    return logger

logger = setup_logging() 