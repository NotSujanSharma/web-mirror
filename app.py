import requests
import re
import os
from typing import Optional, List, Set, Tuple
from urllib.parse import urljoin, urlparse, unquote
from pathlib import Path
import logging
from bs4 import BeautifulSoup

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

    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain as base_url."""
        return urlparse(url).netloc == self.base_domain

    def convert_to_relative_path(self, url: str) -> Optional[str]:
        """Convert absolute URL to relative path if it's from the same domain."""
        if url.startswith(('data:', 'blob:', '#')):
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
        if url in self.processed_urls:
            return True
            
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_bytes(response.content)
            
            self.processed_urls.add(url)
            logger.info(f"Successfully downloaded: {filepath}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            return False
        except OSError as e:
            logger.error(f"Failed to save file {filepath}: {e}")
            return False

    def analyze_paths(self, content: str) -> Tuple[List[str], int]:
        """
        Analyze HTML content to find all relative paths and determine the deepest path level.
        """
        soup = BeautifulSoup(content, 'html.parser')
        resources = []
        max_depth = 0

        def process_path(path: str) -> None:
            nonlocal max_depth
            if not path:
                return
                
            relative_path = self.convert_to_relative_path(path)
            if relative_path:
                resources.append(relative_path)
                
                # Calculate depth for relative paths
                depth = 0
                parts = path.split('/')
                for part in parts:
                    if part == '..':
                        depth += 1
                max_depth = max(max_depth, depth)

        # Find all resources with src attribute
        for tag in soup.find_all(src=True):
            process_path(tag['src'])

        # Find all stylesheet and other resource links
        for tag in soup.find_all(href=True):
            href = tag['href']
            if href.endswith(('.css', '.js', '.ico', '.png', '.jpg', '.jpeg', '.gif')):
                process_path(href)

        return resources, max_depth

    def calculate_html_location(self, max_depth: int) -> Path:
        """Calculate the appropriate location for index.html based on the maximum path depth."""
        html_dir = self.output_dir
        if max_depth > 0:
            for _ in range(max_depth):
                html_dir = html_dir / "level"
        return html_dir

    def adjust_resource_paths(self, content: str, resource_base: Path, html_location: Path) -> str:
        """Adjust resource paths in HTML content based on the HTML file's location."""
        soup = BeautifulSoup(content, 'html.parser')
        
        def fix_path(original_path: str) -> str:
            relative_path = self.convert_to_relative_path(original_path)
            if not relative_path:
                return original_path
                
            # Convert the resource path to absolute path
            abs_resource_path = resource_base / relative_path
            
            # Calculate relative path from HTML location to resource
            try:
                # Get the relative path and ensure it doesn't start with '/'
                rel_path = os.path.relpath(abs_resource_path, html_location)
                # Make sure path uses forward slashes for web compatibility
                return rel_path.replace(os.sep, '/')
            except ValueError:
                return original_path

        # Update src attributes
        for tag in soup.find_all(src=True):
            src = tag['src']
            new_path = fix_path(src)
            if new_path != src:
                tag['src'] = new_path

        # Update href attributes
        for tag in soup.find_all(href=True):
            href = tag['href']
            if href.endswith(('.css', '.js', '.ico', '.png', '.jpg', '.jpeg', '.gif')):
                new_path = fix_path(href)
                if new_path != href:
                    tag['href'] = new_path

        return str(soup)

    def process_resource(self, resource_path: str) -> None:
        """Process a single resource path."""
        # Construct full URL for downloading
        full_url = urljoin(self.base_url, resource_path)
        
        # Clean path for local storage
        clean_path = re.sub(r'\.\./', '', resource_path)
        local_path = self.output_dir / clean_path
        
        self.download_file(full_url, local_path)

    def run(self) -> None:
        """Main execution method."""
        logger.info(f"Starting scraping from {self.base_url}")
        
        # Fetch main content
        content = self.fetch_content(self.base_url)
        if not content:
            logger.error("Failed to fetch main content. Exiting.")
            return

        # Analyze paths and determine HTML location
        resources, max_depth = self.analyze_paths(content)
        logger.info(f"Found {len(resources)} resources with maximum depth of {max_depth}")

        # Calculate appropriate HTML location
        html_location = self.calculate_html_location(max_depth)
        html_location.mkdir(parents=True, exist_ok=True)

        # Process all resources first (store them in base directory)
        for resource in resources:
            self.process_resource(resource)

        # Adjust paths in HTML content based on its location
        adjusted_content = self.adjust_resource_paths(
            content,
            self.output_dir,
            html_location
        )
        
        # Save main HTML file
        index_path = html_location / 'index.html'
        try:
            index_path.write_text(adjusted_content, encoding='utf-8')
            logger.info(f"Successfully saved main HTML file to {index_path}")
        except OSError as e:
            logger.error(f"Failed to save main HTML file: {e}")

        logger.info("Scraping completed")

def main():
    # Configuration
    TARGET_URL = 'https://swastikcollege.edu.np/'
    OUTPUT_DIR = 'downloaded_site'
    
    # Initialize and run scraper
    scraper = WebScraper(TARGET_URL, OUTPUT_DIR)
    scraper.run()

if __name__ == '__main__':
    main()