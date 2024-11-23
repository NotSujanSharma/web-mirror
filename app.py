import requests
import re
import os
from typing import Optional, List, Tuple
from urllib.parse import urljoin, urlparse
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, base_url: str, output_dir: str = "webpages/level1/level2/level3"):
        self.base_url = base_url.rstrip('/')
        self.output_dir = Path(output_dir)
        self.session = requests.Session()

    def fetch_content(self, url: str) -> Optional[str]:
        """Fetch content from URL with error handling."""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch content from {url}: {e}")
            return None

    def download_file(self, url: str, filepath: Path) -> bool:
        """Download file from URL to specified path."""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_bytes(response.content)
            logger.info(f"Successfully downloaded: {filepath}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            return False
        except OSError as e:
            logger.error(f"Failed to save file {filepath}: {e}")
            return False

    def extract_resources(self, content: str) -> List[str]:
        """Extract all resource URLs from content."""
        # combine src and href patterns into one regex
        pattern = r'(?:src|href)="([^"]+\.(?:css|js|png|jpg|jpeg|gif|svg))"'
        resources = re.findall(pattern, content)
        return [res for res in resources if res.startswith(('.', '/'))]

    def get_file_path(self, resource_url: str) -> Path:
        """Generate local file path for resource URL."""
        # remove query parameters and fragments
        clean_url = resource_url.split('?')[0].split('#')[0]
        # create path relative to output directory
        relative_path = clean_url.lstrip('/.') 
        return self.output_dir / relative_path

    def process_resource(self, resource_url: str) -> None:
        """Process a single resource URL."""
        full_url = urljoin(self.base_url, resource_url)
        local_path = self.get_file_path(resource_url)
        self.download_file(full_url, local_path)

    def run(self) -> None:
        """Main execution method."""
        logger.info(f"Starting scraping from {self.base_url}")
        
        # fetch main content
        content = self.fetch_content(self.base_url)
        if not content:
            logger.error("Failed to fetch main content. Exiting.")
            return

        # extract and process resources
        resources = self.extract_resources(content)
        logger.info(f"Found {len(resources)} resources to download")

        for resource in resources:
            self.process_resource(resource)

        logger.info("Scraping completed")

def main():
    # configuration
    TARGET_URL = 'https://ableproadmin.com/dashboard/'
    
    # initialize and run scraper
    scraper = WebScraper(TARGET_URL)
    scraper.run()

if __name__ == '__main__':
    main()