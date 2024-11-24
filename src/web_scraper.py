import requests
from collections import deque
from urllib.parse import urljoin
from pathlib import Path
import logging
from typing import Set, Dict
from src.content_processor import ContentProcessor
from src.downloader import Downloader
from src.utils.path_helpers import get_page_filepath
from src.config import DEFAULT_CONFIG
from urllib.parse import urlparse


logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, base_url: str = DEFAULT_CONFIG['TARGET_URL'],
                 output_dir: str = DEFAULT_CONFIG['OUTPUT_DIR']):
        self.base_url = base_url.rstrip('/')
        self.base_domain = urlparse(base_url).netloc
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.processed_urls: Set[str] = set()
        self.processed_resources: Set[str] = set()
        self.page_queue: deque = deque()
        self.url_to_filepath: Dict[str, Path] = {}
        
        # Initialize components
        self.downloader = Downloader(self.session)
        self.content_processor = ContentProcessor(self.base_domain, self.output_dir)

    def process_page(self, url_path: str) -> None:
        """Process a single page and its resources with error handling."""
        full_url = urljoin(self.base_url, url_path)
        if full_url in self.processed_urls:
            return
            
        logger.info(f"Processing page: {full_url}")
        
        try:
            content = self.downloader.fetch_content(full_url)
            if not content:
                logger.info(f"Skipping {full_url} due to fetch error")
                self.processed_urls.add(full_url)
                return

            self.processed_urls.add(full_url)
            
            resources, page_links, _ = self.content_processor.analyze_page(content, full_url)
            
            for resource in resources:
                try:
                    resource_url = urljoin(self.base_url, resource)
                    resource_path = self.output_dir / resource
                    self.downloader.download_file(resource_url, resource_path, self.processed_resources)
                except Exception as e:
                    logger.warning(f"Failed to process resource {resource}: {e}")
                    continue

            for link in page_links:
                if urljoin(self.base_url, link) not in self.processed_urls:
                    self.page_queue.append(link)

            page_path = get_page_filepath(url_path, self.output_dir)
            self.url_to_filepath[url_path] = page_path
            
            adjusted_content = self.content_processor.adjust_resource_paths(
                content, page_path, self.url_to_filepath)
            
            try:
                page_path.parent.mkdir(parents=True, exist_ok=True)
                page_path.write_text(adjusted_content, encoding='utf-8')
                logger.info(f"Saved page to {page_path}")
            except OSError as e:
                logger.error(f"Failed to save page {page_path}: {e}")
                
        except Exception as e:
            logger.error(f"Unexpected error processing {full_url}: {e}")
            self.processed_urls.add(full_url)

    def run(self) -> None:
        """Main execution method."""
        logger.info(f"Starting multi-page scraping from {self.base_url}")
        
        self.page_queue.append('')
        
        while self.page_queue:
            url_path = self.page_queue.popleft()
            self.process_page(url_path)

        logger.info("Scraping completed")
        logger.info(f"Processed {len(self.processed_urls)} pages and {len(self.processed_resources)} resources")
