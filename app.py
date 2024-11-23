import requests
import re
import os
from typing import Optional, List, Set, Tuple, Dict
from urllib.parse import urljoin, urlparse, unquote
from pathlib import Path
import logging
from bs4 import BeautifulSoup
from collections import deque

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, base_url: str, output_dir: str = "downloaded_site"):
        self.base_url = base_url.rstrip('/')
        self.base_domain = urlparse(base_url).netloc
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.processed_urls: Set[str] = set()
        self.processed_resources: Set[str] = set()
        self.page_queue: deque = deque()
        self.url_to_filepath: Dict[str, Path] = {}

    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain as base_url."""
        return urlparse(url).netloc == self.base_domain

    def convert_to_relative_path(self, url: str) -> Optional[str]:
        """Convert absolute URL to relative path if it's from the same domain."""
        if url.startswith(('data:', 'blob:', '#', 'mailto:', 'tel:')):
            return None
            
        parsed_url = urlparse(url)
        if parsed_url.scheme in ('http', 'https'):
            if not self.is_same_domain(url):
                return None
            # Extract path from absolute URL
            path = parsed_url.path
        else:
            path = url

        # Remove leading slashes and normalize
        return unquote(path.lstrip('/'))

    def fetch_content(self, url: str) -> Optional[str]:
        """Fetch content from URL with enhanced error handling."""
        try:
            response = self.session.get(url, timeout=30)  # Added timeout
            
            # Log common HTTP errors but don't raise exception
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
            
        except requests.exceptions.Timeout:
            logger.warning(f"Request timed out for {url}")
            return None
        except requests.exceptions.SSLError:
            logger.warning(f"SSL verification failed for {url}")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection failed for {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch content from {url}: {e}")
            return None

    def download_file(self, url: str, filepath: Path) -> bool:
        """Download file from URL to specified path."""
        resource_key = str(filepath.relative_to(self.output_dir))
        
        if resource_key in self.processed_resources:
            return True
            
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_bytes(response.content)
            
            self.processed_resources.add(resource_key)
            logger.info(f"Successfully downloaded: {filepath}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            return False
        except OSError as e:
            logger.error(f"Failed to save file {filepath}: {e}")
            return False

    def analyze_page(self, content: str, url: str) -> Tuple[List[str], List[str], int]:
        """
        Analyze HTML content to find all relative paths, page links, and determine the deepest path level.
        """
        soup = BeautifulSoup(content, 'html.parser')
        resources = []
        page_links = []
        max_depth = 0

        def process_path(path: str, is_page: bool = False) -> None:
            nonlocal max_depth
            if not path:
                return
                
            relative_path = self.convert_to_relative_path(path)
            if relative_path:
                if is_page:
                    page_links.append(relative_path)
                else:
                    resources.append(relative_path)
                
                # Calculate depth for relative paths
                depth = len(Path(relative_path).parts)
                max_depth = max(max_depth, depth)

        # Find all resources with src attribute
        for tag in soup.find_all(src=True):
            process_path(tag['src'])

        # Find all links and resources
        for tag in soup.find_all(href=True):
            href = tag['href']
            if href.endswith(('.css', '.js', '.ico', '.png', '.jpg', '.jpeg', '.gif')):
                process_path(href)
            elif href.endswith(('.html', '.htm')) or not href.endswith(('/', '.php', '.asp')):
                process_path(href, True)

        return resources, page_links, max_depth

    def get_page_filepath(self, url_path: str) -> Path:
        """Determine the appropriate filepath for a page."""
        if not url_path or url_path == '/':
            return self.output_dir / 'index.html'
            
        # Clean the path and ensure it ends with .html
        clean_path = re.sub(r'\.\./', '', url_path)
        if not clean_path.endswith(('.html', '.htm')):
            clean_path = f"{clean_path.rstrip('/')}/index.html"
            
        return self.output_dir / clean_path

    def adjust_resource_paths(self, content: str, current_page_path: Path) -> str:
        """Adjust resource and link paths in HTML content based on the current page location."""
        soup = BeautifulSoup(content, 'html.parser')
        
        def fix_path(original_path: str) -> str:
            relative_path = self.convert_to_relative_path(original_path)
            if not relative_path:
                return original_path
                
            # For resources, use the path relative to current page
            target_path = self.output_dir / relative_path
            if relative_path in self.url_to_filepath:
                target_path = self.url_to_filepath[relative_path]
                
            try:
                rel_path = os.path.relpath(target_path, current_page_path.parent)
                return rel_path.replace(os.sep, '/')
            except ValueError:
                return original_path

        # Update src attributes
        for tag in soup.find_all(src=True):
            tag['src'] = fix_path(tag['src'])

        # Update href attributes
        for tag in soup.find_all(href=True):
            href = tag['href']
            if href.endswith(('.css', '.js', '.ico', '.png', '.jpg', '.jpeg', '.gif', '.html', '.htm')):
                tag['href'] = fix_path(href)

        return str(soup)

    def process_page(self, url_path: str) -> None:
        """Process a single page and its resources with error handling."""
        full_url = urljoin(self.base_url, url_path)
        if full_url in self.processed_urls:
            return
            
        logger.info(f"Processing page: {full_url}")
        
        try:
            content = self.fetch_content(full_url)
            if not content:
                logger.info(f"Skipping {full_url} due to fetch error")
                self.processed_urls.add(full_url)  # Mark as processed to avoid retries
                return

            # Mark URL as processed
            self.processed_urls.add(full_url)
            
            # Analyze page content
            resources, page_links, _ = self.analyze_page(content, full_url)
            
            # Download resources with error handling
            for resource in resources:
                try:
                    resource_url = urljoin(self.base_url, resource)
                    resource_path = self.output_dir / resource
                    self.download_file(resource_url, resource_path)
                except Exception as e:
                    logger.warning(f"Failed to process resource {resource}: {e}")
                    continue

            # Queue new pages
            for link in page_links:
                if urljoin(self.base_url, link) not in self.processed_urls:
                    self.page_queue.append(link)

            # Save the page
            page_path = self.get_page_filepath(url_path)
            self.url_to_filepath[url_path] = page_path
            
            # Adjust paths and save
            adjusted_content = self.adjust_resource_paths(content, page_path)
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
        
        # Start with the base URL
        self.page_queue.append('')  # Empty string represents the base URL
        
        # Process pages breadth-first
        while self.page_queue:
            url_path = self.page_queue.popleft()
            self.process_page(url_path)

        logger.info("Scraping completed")
        logger.info(f"Processed {len(self.processed_urls)} pages and {len(self.processed_resources)} resources")

def main():
    # Configuration
    TARGET_URL = 'https://swastikcollege.edu.np/'
    OUTPUT_DIR = 'downloaded_site'
    
    # Initialize and run scraper
    scraper = WebScraper(TARGET_URL, OUTPUT_DIR)
    scraper.run()

if __name__ == '__main__':
    main()