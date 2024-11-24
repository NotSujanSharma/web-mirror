import requests
from pathlib import Path
import logging
from typing import Optional
from src.config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

class Downloader:
    def __init__(self, session: requests.Session):
        self.session = session
        self.timeout = DEFAULT_CONFIG['REQUEST_TIMEOUT']

    def fetch_content(self, url: str) -> Optional[str]:
        """Fetch content from URL with enhanced error handling."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 404:
                logger.warning(f"Page not found (404): {url}")
                return None
            elif response.status_code == 500:
                logger.warning(f"Server error (500): {url}")
                return None
            elif response.status_code >= 400:
                logger.warning(f"HTTP error {response.status_code}: {url}")
                return None
                
            response.raise_for_status()
            return response.text
            
        except (requests.exceptions.Timeout,
                requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
                requests.exceptions.RequestException) as e:
            logger.warning(f"Failed to fetch content from {url}: {e}")
            return None

    def download_file(self, url: str, filepath: Path, processed_resources: set) -> bool:
        """Download file from URL to specified path."""
        resource_key = str(filepath.relative_to(filepath.parent.parent))
        
        if resource_key in processed_resources:
            return True
            
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_bytes(response.content)
            
            processed_resources.add(resource_key)
            logger.info(f"Successfully downloaded: {filepath}")
            return True
            
        except (requests.exceptions.RequestException, OSError) as e:
            logger.error(f"Failed to download/save {url} to {filepath}: {e}")
            return False
