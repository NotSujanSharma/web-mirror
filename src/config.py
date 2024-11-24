import logging
from pathlib import Path

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    'TARGET_URL': 'https://theuselessweb.com/',
    'OUTPUT_DIR': 'downloaded_site/site1',
    'REQUEST_TIMEOUT': 30,
    'ALLOWED_EXTENSIONS': {
        'resources': ('.css', '.js', '.ico', '.png', '.jpg', '.jpeg', '.gif'),
        'pages': ('.html', '.htm')
    }
}