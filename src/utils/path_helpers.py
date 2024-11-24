import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

def get_page_filepath(url_path: str, output_dir: Path) -> Path:
    """Determine the appropriate filepath for a page."""
    if not url_path or url_path == '/':
        return output_dir / 'index.html'
        
    clean_path = re.sub(r'\.\./', '', url_path)
    if not clean_path.endswith(('.html', '.htm')):
        clean_path = f"{clean_path.rstrip('/')}/index.html"
        
    return output_dir / clean_path

def get_relative_href(href: str, current_page_path: Path, url_to_filepath: dict) -> Optional[str]:
    """Convert an href to a relative path if it points to a downloaded page."""
    try:
        if href.startswith(('http://', 'https://')):
            parsed = urlparse(href)
            href = parsed.path
            if parsed.query:
                href = f"{href}?{parsed.query}"
            if parsed.fragment:
                href = f"{href}#{parsed.fragment}"
        elif href.startswith('/'):
            href = href.lstrip('/')
        
        path_part = href.split('?')[0].split('#')[0]
        query_part = href[len(path_part):] if len(href) > len(path_part) else ''
        
        clean_path = path_part.rstrip('/')
        
        if clean_path in url_to_filepath:
            target_path = url_to_filepath[clean_path]
        elif not clean_path.endswith(('.html', '.htm')):
            index_path = f"{clean_path}/index.html".lstrip('/')
            if index_path in url_to_filepath:
                target_path = url_to_filepath[index_path]
            else:
                html_path = f"{clean_path}.html"
                if html_path in url_to_filepath:
                    target_path = url_to_filepath[html_path]
                else:
                    return None
        else:
            return None
            
        rel_path = os.path.relpath(target_path, current_page_path.parent)
        return rel_path.replace(os.sep, '/') + query_part
        
    except ValueError:
        return None
