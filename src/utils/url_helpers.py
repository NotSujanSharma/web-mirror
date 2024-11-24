from urllib.parse import urljoin, urlparse, unquote
from pathlib import Path
from typing import Optional

def is_same_domain(url: str, base_domain: str) -> bool:
    """Check if URL belongs to the same domain as base_url."""
    return urlparse(url).netloc == base_domain

def convert_to_relative_path(url: str, base_domain: str) -> Optional[str]:
    """Convert absolute URL to relative path if it's from the same domain."""
    if url.startswith(('data:', 'blob:', '#', 'mailto:', 'tel:')):
        return None
        
    parsed_url = urlparse(url)
    if parsed_url.scheme in ('http', 'https'):
        if not is_same_domain(url, base_domain):
            return None
        path = parsed_url.path
    else:
        path = url

    return unquote(path.lstrip('/'))

def should_process_href(href: str) -> bool:
    """Determine if an href link should be processed for relative path conversion."""
    if not href:
        return False
        
    if href.startswith(('data:', 'blob:', '#', 'mailto:', 'tel:', 'javascript:')):
        return False
        
    return True