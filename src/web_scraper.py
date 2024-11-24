import asyncio
from collections import deque
from urllib.parse import urljoin
from pathlib import Path
import logging
from typing import Set, Dict, List
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
        self.processed_urls: Set[str] = set()
        self.processed_resources: Set[str] = set()
        self.page_queue: deque = deque()
        self.url_to_filepath: Dict[str, Path] = {}
        
        # Initialize components
        self.content_processor = ContentProcessor(self.base_domain, self.output_dir)

    async def process_resources(self, resources: List[str], downloader: Downloader) -> None:
        """Process multiple resources concurrently."""
        tasks = []
        for resource in resources:
            resource_url = urljoin(self.base_url, resource)
            resource_path = self.output_dir / resource
            task = asyncio.create_task(
                downloader.download_file(resource_url, resource_path, self.processed_resources)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)

    async def process_page(self, url_path: str, downloader: Downloader) -> None:
        """Process a single page and its resources asynchronously."""
        full_url = urljoin(self.base_url, url_path)
        if full_url in self.processed_urls:
            return
            
        logger.info(f"Processing page: {full_url}")
        
        try:
            content = await downloader.fetch_content(full_url)
            if not content:
                logger.info(f"Skipping {full_url} due to fetch error")
                self.processed_urls.add(full_url)
                return

            self.processed_urls.add(full_url)
            
            # Analyze page content
            resources, page_links, _ = await self.content_processor.analyze_page(content, full_url)
            
            # Process resources concurrently
            await self.process_resources(resources, downloader)

            # Queue new pages
            for link in page_links:
                if urljoin(self.base_url, link) not in self.processed_urls:
                    self.page_queue.append(link)

            # Save the page
            page_path = get_page_filepath(url_path, self.output_dir)
            self.url_to_filepath[url_path] = page_path
            
            # Adjust paths and save
            adjusted_content = await self.content_processor.adjust_resource_paths(
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

    async def process_batch(self, batch: List[str], downloader: Downloader) -> None:
        """Process a batch of pages concurrently."""
        tasks = [self.process_page(url_path, downloader) for url_path in batch]
        await asyncio.gather(*tasks)

    async def run(self) -> None:
        """Main execution method with concurrent processing."""
        logger.info(f"Starting multi-page scraping from {self.base_url}")
        
        self.page_queue.append('')
        batch_size = DEFAULT_CONFIG['MAX_CONCURRENT_REQUESTS']

        async with Downloader() as downloader:
            while self.page_queue:
                # Process pages in batches
                batch = []
                while len(batch) < batch_size and self.page_queue:
                    batch.append(self.page_queue.popleft())
                
                await self.process_batch(batch, downloader)

        logger.info("Scraping completed")
        logger.info(f"Processed {len(self.processed_urls)} pages and {len(self.processed_resources)} resources")
