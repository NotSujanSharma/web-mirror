from pathlib import Path
from typing import Set
import logging
from typing import Optional
from src.config import DEFAULT_CONFIG
import backoff 
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

class Downloader:
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=DEFAULT_CONFIG['REQUEST_TIMEOUT'])
        self.semaphore = asyncio.Semaphore(DEFAULT_CONFIG['MAX_CONCURRENT_REQUESTS'])
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=DEFAULT_CONFIG['MAX_RETRIES'],
        max_time=30
    )
    async def fetch_content(self, url: str) -> Optional[str]:
        """Fetch content from URL with retries and error handling."""
        async with self.semaphore:
            try:
                async with self.session.get(url) as response:
                    if response.status >= 400:
                        logger.warning(f"HTTP error {response.status}: {url}")
                        return None
                    return await response.text()
            except Exception as e:
                logger.warning(f"Failed to fetch content from {url}: {e}")
                return None

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=DEFAULT_CONFIG['MAX_RETRIES'],
        max_time=30
    )

    async def download_file(self, url: str, filepath: Path, processed_resources: Set[str]) -> bool:
        """Download file from URL with streaming and retry capability."""
        resource_key = str(filepath.relative_to(filepath.parent.parent))
        
        if resource_key in processed_resources:
            return True

        async with self.semaphore:
            try:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        return False

                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Stream the response content
                    with filepath.open('wb') as f:
                        async for chunk in response.content.iter_chunked(DEFAULT_CONFIG['CHUNK_SIZE']):
                            f.write(chunk)

                processed_resources.add(resource_key)
                logger.info(f"Successfully downloaded: {filepath}")
                return True

            except Exception as e:
                logger.error(f"Failed to download {url}: {e}")
                return False
