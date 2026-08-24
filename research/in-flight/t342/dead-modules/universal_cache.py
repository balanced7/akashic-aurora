"""
Universal Cache Manager - Central Download Cache
============================================
All downloads go through this system:
1. Check cache first
2. If cached item exists, use it
3. If newer version available (and compatible), download and cache it
4. Return cached path

Usage:
    from universal_cache import AssetsManager, download_chromedriver, download_huggingface_model
    
    cache = AssetsManager()
    
    # Always uses cache first
    path = cache.get_or_download(
        name="chromedriver",
        version="146.0.7680.165",
        source_type="chromedriver",
        url="https://...",
        check_updates=True
    )
"""

import os
import sys
import json
import hashlib
import shutil
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from functools import wraps

# Assets base directory
ASSETS_BASE = r"E:\AI-Setup\assets"
ASSETS_DB = os.path.join(ASSETS_BASE, "assets_manifest.json")


class SourceType:
    """Source types for cached artifacts"""
    DOCKER = "docker"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    CHROMEDRIVER = "chromedriver"
    ROCM = "rocm"
    PIP = "pip"
    TRANSFORMERS = "transformers"
    MANUAL = "manual"


class CacheEntry:
    """Represents a cached artifact"""
    
    def __init__(
        self,
        name: str,
        source_type: str,
        local_path: str,
        url: str = None,
        version: str = None,
        size_mb: float = 0,
        checksum: str = None,
        last_checked: str = None,
        last_updated: str = None,
        tags: List[str] = None,
        metadata: Dict = None
    ):
        self.name = name
        self.source_type = source_type
        self.local_path = local_path
        self.url = url
        self.version = version
        self.size_mb = size_mb
        self.checksum = checksum
        self.last_checked = last_checked or datetime.now().isoformat()
        self.last_updated = last_updated or datetime.now().isoformat()
        self.tags = tags or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "source_type": self.source_type,
            "local_path": self.local_path,
            "url": self.url,
            "version": self.version,
            "size_mb": self.size_mb,
            "checksum": self.checksum,
            "last_checked": self.last_checked,
            "last_updated": self.last_updated,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CacheEntry':
        return cls(**data)
    
    def exists(self) -> bool:
        return os.path.exists(self.local_path)
    
    def update_size(self):
        """Update file size"""
        if self.exists():
            self.size_mb = os.path.getsize(self.local_path) / (1024 * 1024)
    
    def __repr__(self):
        status = "[OK]" if self.exists() else "[MISSING]"
        return f"<CacheEntry {status} {self.name} v{self.version} ({self.size_mb:.1f}MB)>"


class AssetsManager:
    """
    Central repository for ALL downloaded assets.
    
    Flow:
    1. get_or_download() - Check repo, download if needed
    2. Always returns local path
    3. Tracks all artifacts with metadata
    """
    
    def __init__(self, assets_base: str = ASSETS_BASE):
        self.assets_base = assets_base
        self.manifest_path = ASSETS_DB
        self.entries: Dict[str, CacheEntry] = {}
        self._ensure_dirs()
        self._load_manifest()
    
    def _ensure_dirs(self):
        """Create all cache subdirectories"""
        dirs = [
            self.assets_base,
            os.path.join(self.assets_base, "docker_images"),
            os.path.join(self.assets_base, "huggingface"),
            os.path.join(self.assets_base, "ollama"),
            os.path.join(self.assets_base, "chromedriver"),
            os.path.join(self.assets_base, "rocm"),
            os.path.join(self.assets_base, "pip"),
            os.path.join(self.assets_base, "transformers"),
            os.path.join(self.assets_base, "downloads"),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)
    
    def _load_manifest(self):
        """Load cache manifest from disk"""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r') as f:
                    data = json.load(f)
                    self.entries = {k: CacheEntry.from_dict(v) for k, v in data.items()}
            except Exception as e:
                print(f"[cache] Failed to load manifest: {e}")
                self.entries = {}
    
    def _save_manifest(self):
        """Save cache manifest to disk"""
        with open(self.manifest_path, 'w') as f:
            data = {k: v.to_dict() for k, v in self.entries.items()}
            json.dump(data, f, indent=2)
    
    def _get_cache_key(self, name: str, version: str = None) -> str:
        """Get cache key"""
        if version:
            return f"{name}:{version}"
        return name
    
    def _get_dir(self, source_type: str) -> str:
        """Get cache directory for source type"""
        return os.path.join(self.assets_base, source_type)
    
    # === CACHE OPERATIONS ===
    
    def has(self, name: str, version: str = None) -> bool:
        """Check if item is in cache"""
        key = self._get_cache_key(name, version)
        entry = self.entries.get(key)
        return entry is not None and entry.exists()
    
    def get(self, name: str, version: str = None) -> Optional[str]:
        """Get cached path if exists"""
        key = self._get_cache_key(name, version)
        entry = self.entries.get(key)
        if entry and entry.exists():
            entry.last_checked = datetime.now().isoformat()
            self._save_manifest()
            return entry.local_path
        return None
    
    def add(
        self,
        name: str,
        source_type: str,
        local_path: str,
        url: str = None,
        version: str = None,
        tags: List[str] = None,
        metadata: Dict = None
    ) -> CacheEntry:
        """Add item to cache"""
        key = self._get_cache_key(name, version)
        
        entry = CacheEntry(
            name=name,
            source_type=source_type,
            local_path=local_path,
            url=url,
            version=version,
            tags=tags,
            metadata=metadata
        )
        entry.update_size()
        
        self.entries[key] = entry
        self._save_manifest()
        return entry
    
    def remove(self, name: str, version: str = None) -> bool:
        """Remove item from cache"""
        key = self._get_cache_key(name, version)
        if key in self.entries:
            entry = self.entries[key]
            if entry.exists():
                try:
                    os.remove(entry.local_path)
                except:
                    pass
            del self.entries[key]
            self._save_manifest()
            return True
        return False
    
    # === DOWNLOAD OPERATIONS ===
    
    def download(
        self,
        url: str,
        name: str,
        source_type: str,
        version: str = None,
        filename: str = None,
        tags: List[str] = None,
        metadata: Dict = None
    ) -> Optional[str]:
        """
        Download a file and add to cache.
        
        Returns local path or None on failure.
        """
        # Determine filename
        if not filename:
            filename = os.path.basename(url)
        
        # Destination path
        dest_dir = self._get_dir(source_type)
        dest_path = os.path.join(dest_dir, filename)
        
        try:
            print(f"[cache] Downloading {url}...")
            print(f"[cache] -> {dest_path}")
            
            # Download with progress
            urllib.request.urlretrieve(url, dest_path)
            
            # Verify download
            if not os.path.exists(dest_path):
                print(f"[cache] Download failed: file not created")
                return None
            
            size_mb = os.path.getsize(dest_path) / (1024 * 1024)
            print(f"[cache] Downloaded: {size_mb:.1f} MB")
            
            # Add to cache
            entry = self.add(
                name=name,
                source_type=source_type,
                local_path=dest_path,
                url=url,
                version=version,
                tags=tags,
                metadata=metadata
            )
            
            return dest_path
            
        except Exception as e:
            print(f"[cache] Download failed: {e}")
            # Clean up partial download
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except:
                    pass
            return None
    
    # === GET OR DOWNLOAD (MAIN API) ===
    
    def get_or_download(
        self,
        name: str,
        source_type: str,
        url: str = None,
        version: str = None,
        filename: str = None,
        tags: List[str] = None,
        metadata: Dict = None,
        check_updates: bool = False,
        update_checker: Callable = None
    ) -> Optional[str]:
        """
        Get from cache or download if not present.
        
        This is the MAIN entry point for all downloads.
        
        Args:
            name: Artifact name
            source_type: Type (chromedriver, huggingface, etc.)
            url: Download URL
            version: Version string
            filename: Optional filename override
            tags: Tags for the entry
            metadata: Additional metadata
            check_updates: If True, check for newer version
            update_checker: Function to check for updates
        
        Returns:
            Local path or None on failure
        """
        # Check cache first
        cached = self.get(name, version)
        if cached:
            print(f"[cache] Using cached: {name}:{version or 'latest'}")
            
            # Check for updates if requested
            if check_updates and update_checker:
                update_result = update_checker(name, version)
                if update_result and update_result.get('update_available'):
                    print(f"[cache] New version available: {update_result['latest_version']}")
                    # Download new version
                    new_url = update_result.get('url', url)
                    if new_url:
                        return self.download(
                            url=new_url,
                            name=name,
                            source_type=source_type,
                            version=update_result['latest_version'],
                            filename=filename,
                            tags=tags,
                            metadata=metadata
                        )
            
            return cached
        
        # Need to download
        if not url:
            print(f"[cache] Not in cache and no URL provided: {name}")
            return None
        
        return self.download(
            url=url,
            name=name,
            source_type=source_type,
            version=version,
            filename=filename,
            tags=tags,
            metadata=metadata
        )
    
    # === HELPER METHODS ===
    
    def list_by_source(self, source_type: str) -> List[CacheEntry]:
        """List entries by source type"""
        return [e for e in self.entries.values() if e.source_type == source_type]
    
    def list_all(self) -> List[CacheEntry]:
        """List all entries"""
        return list(self.entries.values())
    
    def inventory(self) -> Dict:
        """Get cache inventory"""
        present = [e for e in self.entries.values() if e.exists()]
        missing = [e for e in self.entries.values() if not e.exists()]
        total_size = sum(e.size_mb for e in present)
        
        by_source = {}
        for e in self.entries.values():
            if e.source_type not in by_source:
                by_source[e.source_type] = {'present': 0, 'missing': 0, 'size_mb': 0}
            if e.exists():
                by_source[e.source_type]['present'] += 1
                by_source[e.source_type]['size_mb'] += e.size_mb
            else:
                by_source[e.source_type]['missing'] += 1
        
        return {
            'cache_dir': self.assets_base,
            'total': len(self.entries),
            'present': len(present),
            'missing': len(missing),
            'size_mb': round(total_size, 2),
            'by_source': by_source,
            'timestamp': datetime.now().isoformat()
        }


# === CONVENIENCE DOWNLOAD FUNCTIONS ===

# Global cache instance
_cache = None

def get_cache() -> AssetsManager:
    """Get global cache instance"""
    global _cache
    if _cache is None:
        _cache = AssetsManager()
    return _cache


def download_chromedriver(version: str = None) -> Optional[str]:
    """
    Download ChromeDriver (version-matched to Brave).
    
    Args:
        version: ChromeDriver version (e.g., "146.0.7680.165")
    
    Returns:
        Path to chromedriver.exe or None
    """
    cache = get_cache()
    
    # Known ChromeDriver URL template
    base_url = "https://storage.googleapis.com/chrome-for-testing-public"
    
    # Get version if not specified
    if not version:
        # Try to find Brave version
        version = "146.0.7680.165"  # Default
    
    url = f"{base_url}/{version}/win64/chromedriver-win64.zip"
    
    return cache.get_or_download(
        name="chromedriver",
        source_type=SourceType.CHROMEDRIVER,
        url=url,
        version=version,
        filename=f"chromedriver-{version}.zip",
        tags=["driver", "selenium"]
    )


def download_huggingface_model(model_name: str, base_path: str = None) -> Optional[str]:
    """
    Get Hugging Face model path (downloads if not cached).
    
    Note: For HF models, we cache the directory path.
    Actual download happens via transformers library.
    """
    cache = get_cache()
    
    cache_dir = base_path or os.path.join(cache.cache_base, "huggingface")
    model_path = os.path.join(cache_dir, model_name.replace("/", "--"))
    
    # Add to cache tracking
    cache.add(
        name=f"hf:{model_name}",
        source_type=SourceType.HUGGINGFACE,
        local_path=model_path,
        tags=["model", "huggingface"],
        metadata={"model_name": model_name}
    )
    
    return model_path


def download_ollama_model(model_name: str, tag: str = "latest") -> Optional[str]:
    """Get Ollama model path (downloads if not cached)"""
    cache = get_cache()
    
    cache_dir = os.path.join(cache.cache_base, "ollama")
    model_path = os.path.join(cache_dir, model_name, tag)
    
    cache.add(
        name=f"ollama:{model_name}",
        source_type=SourceType.OLLAMA,
        local_path=model_path,
        version=tag,
        tags=["model", "ollama"],
        metadata={"model_name": model_name, "tag": tag}
    )
    
    return model_path


# === DECORATOR FOR AUTOMATIC CACHING ===

def cached_download(source_type: str, version_arg: int = None):
    """
    Decorator to make any download function use the cache.
    
    Usage:
        @cached_download(source_type="chromedriver", version_arg=1)
        def download_chromedriver(version="146.0.7680.165"):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Get version from args/kwargs
            version = None
            if version_arg and len(args) >= version_arg:
                version = args[version_arg - 1]
            version = kwargs.get('version', version)
            
            # Check cache
            cached = cache.get(func.__name__, version)
            if cached:
                return cached
            
            # Download
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# === MAIN ===

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Universal Cache Manager")
    parser.add_argument("--inventory", "-i", action="store_true", help="Show inventory")
    parser.add_argument("--download-chromedriver", type=str, help="Download ChromeDriver")
    parser.add_argument("--has", type=str, help="Check if cached")
    parser.add_argument("--get", type=str, help="Get cached path")
    
    args = parser.parse_args()
    
    cache = get_cache()
    
    if args.inventory:
        inv = cache.inventory()
        print("=" * 60)
        print("UNIVERSAL CACHE INVENTORY")
        print("=" * 60)
        print(f"Cache Dir: {inv['cache_dir']}")
        print(f"Total:     {inv['total']} | Present: {inv['present']} | Missing: {inv['missing']}")
        print(f"Size:      {inv['size_mb']:.2f} MB")
        print()
        print("By Source:")
        for src, stats in inv['by_source'].items():
            print(f"  {src:15} | Present: {stats['present']:2} | Missing: {stats['missing']:2} | {stats['size_mb']:8.2f} MB")
        print()
        print("Entries:")
        for e in cache.list_all():
            print(f"  {e}")
        print("=" * 60)
    
    elif args.download_chromedriver:
        path = download_chromedriver(args.download_chromedriver)
        if path:
            print(f"ChromeDriver: {path}")
    
    elif args.has:
        has = cache.has(args.has)
        print(f"Has {args.has}: {has}")
    
    elif args.get:
        path = cache.get(args.get)
        print(f"Path: {path}")
    
    else:
        # Default: show inventory
        inv = cache.inventory()
        print(f"Cache: {inv['present']}/{inv['total']} items, {inv['size_mb']:.1f} MB")
