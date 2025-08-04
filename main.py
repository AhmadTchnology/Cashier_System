# main.py
import os
import sys
import logging
import argparse
import json
from pathlib import Path
from database import Database
from ui import CashierUI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pos_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("POS_System")

# Default configuration
DEFAULT_CONFIG = {
    "database": "pos.db",
    "receipt_dir": "receipts",
    "export_dir": "exports",
    "theme": "default"
}

def load_config(config_path="config.json"):
    """Load configuration from JSON file or create default if not exists"""
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Configuration loaded from {config_path}")
                return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    # Create default config if not exists
    with open(config_path, 'w') as f:
        json.dump(DEFAULT_CONFIG, f, indent=4)
        logger.info(f"Created default configuration at {config_path}")
    
    return DEFAULT_CONFIG

def setup_directories(config):
    """Create required directories if they don't exist."""
    # Define directory mappings with nested config support
    dir_mappings = {
        'receipt_dir': config.get('receipt', {}).get('receipt_dir', 'receipts'),
        'export_dir': config.get('export', {}).get('default_dir', 'exports'),
        'backup_dir': config.get('database', {}).get('backup_dir', 'backups'),
        'log_dir': os.path.dirname(config.get('logging', {}).get('file', 'logs/pos.log'))
    }
    
    for dir_key, dir_path in dir_mappings.items():
        path = Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path}")
        else:
            logger.debug(f"Directory already exists: {path}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Python POS System")
    parser.add_argument("--config", help="Path to configuration file", default="config.json")
    parser.add_argument("--debug", help="Enable debug mode", action="store_true")
    return parser.parse_args()

def main():
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Set debug level if requested
        if args.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug("Debug mode enabled")
        
        # Load configuration
        config = load_config(args.config)
        
        # Setup required directories
        setup_directories(config)
        
        # Initialize database
        db_path = config["database"].get("name", "pos.db")
        db = Database(db_path)
        logger.info(f"Database initialized: {db_path}")
        
        # Start UI
        app = CashierUI(db, config)
        logger.info("Starting POS application")
        app.run()
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
