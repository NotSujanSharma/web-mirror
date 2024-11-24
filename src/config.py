import logging
from pathlib import Path
import asyncio
import platform

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    'TARGET_URL': 'https://swastikcollege.edu.np/',
    'OUTPUT_DIR': 'downloaded_site',
    'REQUEST_TIMEOUT': 30,
    'MAX_CONCURRENT_REQUESTS': 10,  # Maximum number of concurrent requests
    'MAX_RETRIES': 3,              # Maximum number of retry attempts
    'RETRY_DELAY': 1,              # Delay between retries in seconds
    'CHUNK_SIZE': 8192,            # Chunk size for file downloads
    'ALLOWED_EXTENSIONS': {
        'resources': ('.css', '.js', '.ico', '.png', '.jpg', '.jpeg', '.gif'),
        'pages': ('.html', '.htm')
    }
}

# Set a higher limit for Windows
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
