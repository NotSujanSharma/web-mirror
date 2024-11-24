from bs4 import BeautifulSoup
from typing import List, Tuple
from pathlib import Path
from src.utils.url_helpers import convert_to_relative_path, should_process_href
from src.utils.path_helpers import get_relative_href
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import asyncio

class ContentProcessor:
    def __init__(self, base_domain: str, output_dir: Path):
        self.base_domain = base_domain
        self.output_dir = output_dir
        self.executor = ThreadPoolExecutor(max_workers=4)  # For CPU-bound tasks

    async def analyze_page(self, content: str, url: str) -> Tuple[List[str], List[str], int]:
        """Analyze HTML content asynchronously using ThreadPoolExecutor for CPU-bound parsing."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            partial(self._analyze_page_sync, content, url)
        )

    def _analyze_page_sync(self, content: str, url: str) -> Tuple[List[str], List[str], int]:
        """Analyze HTML content to find all relative paths, page links, and determine the deepest path level."""
        soup = BeautifulSoup(content, 'html.parser')
        resources = []
        page_links = []
        max_depth = 0

        def process_path(path: str, is_page: bool = False) -> None:
            nonlocal max_depth
            if not path:
                return
                
            relative_path = convert_to_relative_path(path, self.base_domain)
            if relative_path:
                if is_page:
                    page_links.append(relative_path)
                else:
                    resources.append(relative_path)
                
                depth = len(Path(relative_path).parts)
                max_depth = max(max_depth, depth)

        for tag in soup.find_all(src=True):
            process_path(tag['src'])

        for tag in soup.find_all(href=True):
            href = tag['href']
            if href.endswith(('.css', '.js', '.ico', '.png', '.jpg', '.jpeg', '.gif')):
                process_path(href)
            elif href.endswith(('.html', '.htm')) or not href.endswith(('/', '.php', '.asp')):
                process_path(href, True)

        return resources, page_links, max_depth

    async def adjust_resource_paths(self, content: str, current_page_path: Path, url_to_filepath: dict) -> str:
        """Adjust resource paths asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            partial(self._adjust_resource_paths_sync, content, current_page_path, url_to_filepath)
        )
        
    def _adjust_resource_paths_sync(self, content: str, current_page_path: Path, url_to_filepath: dict) -> str:
        """Adjust resource and link paths in HTML content based on the current page location."""
        soup = BeautifulSoup(content, 'html.parser')
        
        def fix_path(original_path: str) -> str:
            if original_path.startswith('/'):
                relative_path = original_path.lstrip('/')
            else:
                relative_path = convert_to_relative_path(original_path, self.base_domain)
                
            if not relative_path:
                return original_path
                
            target_path = self.output_dir / relative_path
            if relative_path in url_to_filepath:
                target_path = url_to_filepath[relative_path]
                
            try:
                rel_path = os.path.relpath(target_path, current_page_path.parent)
                return rel_path.replace(os.sep, '/')
            except ValueError:
                return original_path

        for tag in soup.find_all(src=True):
            tag['src'] = fix_path(tag['src'])

        for tag in soup.find_all(href=True):
            href = tag['href']
            if not should_process_href(href):
                continue
                
            if href.endswith(('.css', '.js', '.ico', '.png', '.jpg', '.jpeg', '.gif')):
                tag['href'] = fix_path(href)
            else:
                relative_href = get_relative_href(href, current_page_path, url_to_filepath)
                if relative_href:
                    tag['href'] = relative_href

        return str(soup)
