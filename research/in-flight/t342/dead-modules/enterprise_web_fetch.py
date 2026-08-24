"""
Enterprise Web Fetch with Retry Logic and Error Handling
E:\AI-Setup\enterprise_web_fetch.py
====================================================

ENTERPRISE PATTERNS FOR WEB SCRAPING:
1. Realistic Browser Headers - Look like a real browser
2. Retry with Exponential Backoff - Handle transient failures
3. Multiple User-Agents - Rotate to avoid detection
4. Proper Session Management - Maintain cookies
5. Timeout Handling - Don't hang forever
6. Fallback URLs - Try alternative sources
7. Rate Limiting - Be respectful

Author: Enterprise Systems
Version: 1.0
"""

import os
import time
import random
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

# ============================================================================
# CONFIGURATION
# ============================================================================

CACHE_DIR = r"E:\AI-Setup\blackboard_data\web_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Enterprise retry settings
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
MAX_BACKOFF = 30  # seconds
TIMEOUT = 15  # seconds

# Realistic browser user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# Common headers that make requests look legitimate
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# Alternative URLs for common documentation
FALLBACK_URLS = {
    "rocm": [
        "https://rocm.docs.amd.com/en/latest/",
        "https://github.com/ROCm/ROCm",
        "https://docs.amd.com/",
    ],
    "docker": [
        "https://docs.docker.com/",
        "https://github.com/docker",
    ],
    "wsl": [
        "https://learn.microsoft.com/en-us/windows/wsl/",
        "https://github.com/microsoft/WSL",
    ],
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class WebFetchResult:
    success: bool
    content: Optional[str]
    status_code: Optional[int]
    error: Optional[str]
    url_final: str
    cache_hit: bool
    attempts: int
    headers_sent: Dict
    headers_received: Dict

# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

def get_cache_path(url: str) -> str:
    """Get cache file path for URL."""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{url_hash}.cache")

def get_from_cache(url: str, max_age_hours: int = 24) -> Optional[str]:
    """Retrieve cached content if fresh enough."""
    cache_path = get_cache_path(url)
    if not os.path.exists(cache_path):
        return None
    
    # Check age
    age_hours = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))).total_seconds() / 3600
    if age_hours > max_age_hours:
        return None
    
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return None

def save_to_cache(url: str, content: str):
    """Save content to cache."""
    cache_path = get_cache_path(url)
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"Cache write failed: {e}")

# ============================================================================
# ENTERPRISE WEB FETCH
# ============================================================================

def enterprise_fetch(
    url: str,
    use_cache: bool = True,
    force_refresh: bool = False,
    fallback_urls: list = None
) -> WebFetchResult:
    """
    Enterprise web fetch with:
    - Retry logic
    - Exponential backoff
    - Realistic browser headers
    - Cache support
    - Fallback URLs
    """
    
    headers_sent = DEFAULT_HEADERS.copy()
    headers_sent["User-Agent"] = random.choice(USER_AGENTS)
    
    # Check cache first
    if use_cache and not force_refresh:
        cached = get_from_cache(url)
        if cached:
            return WebFetchResult(
                success=True,
                content=cached,
                status_code=200,
                error=None,
                url_final=url,
                cache_hit=True,
                attempts=0,
                headers_sent=headers_sent,
                headers_received={}
            )
    
    # Try main URL with retries
    urls_to_try = [url]
    if fallback_urls:
        urls_to_try.extend(fallback_urls)
    
    last_error = None
    for attempt in range(MAX_RETRIES):
        for current_url in urls_to_try:
            try:
                # Build request with headers
                request = urllib.request.Request(
                    current_url,
                    headers=headers_sent
                )
                
                # Execute with timeout
                response = urllib.request.urlopen(
                    request,
                    timeout=TIMEOUT
                )
                
                # Read content
                content = response.read()
                
                # Handle Content-Encoding (gzip, deflate, br)
                content_encoding = response.headers.get("Content-Encoding", "").lower()
                
                if content_encoding == "gzip":
                    import gzip
                    content = gzip.decompress(content)
                elif content_encoding == "deflate":
                    import zlib
                    try:
                        content = zlib.decompress(content)
                    except:
                        content = zlib.decompress(content, -zlib.MAX_WBITS)
                elif content_encoding == "br":
                    import brotli
                    content = brotli.decompress(content)
                
                # Decode properly
                if isinstance(content, bytes):
                    # Try UTF-8, fall back to latin-1
                    try:
                        content = content.decode("utf-8")
                    except UnicodeDecodeError:
                        content = content.decode("latin-1")
                
                # Cache successful response
                if use_cache:
                    save_to_cache(url, content)
                
                return WebFetchResult(
                    success=True,
                    content=content,
                    status_code=response.getcode(),
                    error=None,
                    url_final=current_url,
                    cache_hit=False,
                    attempts=attempt + 1,
                    headers_sent=headers_sent,
                    headers_received=dict(response.headers)
                )
                
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                if e.code == 404:
                    # 404 is permanent failure - don't retry
                    break
                elif e.code in (429, 503):
                    # Rate limited - retry with longer backoff
                    backoff = min(MAX_BACKOFF, INITIAL_BACKOFF * (2 ** attempt) * random.uniform(1, 1.5))
                    time.sleep(backoff)
                else:
                    # Other HTTP errors - brief backoff
                    time.sleep(INITIAL_BACKOFF * (2 ** attempt))
                    
            except urllib.error.URLError as e:
                last_error = f"URL Error: {e.reason}"
                time.sleep(INITIAL_BACKOFF * (2 ** attempt))
                
            except Exception as e:
                last_error = f"Error: {type(e).__name__}: {str(e)}"
                time.sleep(INITIAL_BACKOFF * (2 ** attempt))
    
    # All retries exhausted
    return WebFetchResult(
        success=False,
        content=None,
        status_code=None,
        error=last_error,
        url_final=url,
        cache_hit=False,
        attempts=MAX_RETRIES,
        headers_sent=headers_sent,
        headers_received={}
    )


def smart_fetch(url: str, category: str = None) -> WebFetchResult:
    """
    Smart fetch with category-specific fallback URLs.
    
    Categories: rocm, docker, wsl, github
    """
    fallback = FALLBACK_URLS.get(category, []) if category else []
    return enterprise_fetch(url, fallback_urls=fallback)


# ============================================================================
# GITHUB API FETCH (More reliable than web scraping)
# ============================================================================

def fetch_github_api(path: str) -> Optional[Dict]:
    """Fetch from GitHub API - most reliable for repo info."""
    url = f"https://api.github.com{path}"
    headers = DEFAULT_HEADERS.copy()
    headers["User-Agent"] = "Enterprise-Bot/1.0"
    headers["Accept"] = "application/vnd.github.v3+json"
    
    try:
        request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request, timeout=TIMEOUT)
        import json
        return json.loads(response.read())
    except Exception as e:
        print(f"GitHub API fetch failed: {e}")
        return None


def fetch_github_readme(repo: str) -> Optional[str]:
    """Fetch README from GitHub repo."""
    for branch in ["main", "master"]:
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
        result = enterprise_fetch(url)
        if result.success:
            return result.content
    return None


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enterprise Web Fetch")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache")
    parser.add_argument("--refresh", action="store_true", help="Force cache refresh")
    parser.add_argument("--category", "-c", help="Category for fallback URLs")
    
    args = parser.parse_args()
    
    result = smart_fetch(args.url, args.category)
    
    print(f"\n{'='*60}")
    print(f"Web Fetch Result")
    print(f"{'='*60}")
    print(f"Success:     {result.success}")
    print(f"Status:      {result.status_code or 'N/A'}")
    print(f"URL:         {result.url_final}")
    print(f"Cache Hit:   {result.cache_hit}")
    print(f"Attempts:    {result.attempts}")
    print(f"Error:       {result.error or 'None'}")
    
    if result.content:
        # Strip non-printable characters for display
        clean_content = ''.join(char for char in result.content if char.isprintable() or char in '\n\r\t')
        preview = clean_content[:500] + "..." if len(clean_content) > 500 else clean_content
        print(f"\nContent Preview:\n{preview}")
    
    print(f"{'='*60}\n")
