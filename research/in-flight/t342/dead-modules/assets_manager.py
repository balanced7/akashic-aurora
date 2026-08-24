"""
Assets Manager - Local Downloaded Assets Repository
==============================================
Central repository for ALL downloaded resources: models, images, drivers, packages.

Before downloading anything:
1. Check if it's in the assets repo
2. If yes, use the cached version
3. If newer version available (and compatible), download and cache
4. Sync to target systems

Usage:
    from assets_manager import AssetsManager, SourceType
    
    assets = AssetsManager()
    assets.inventory()  # Check what's cached
    assets.add_huggingface_model("deepseek-ai/deepseek-coder-v2-16b")
    assets.add_ollama_model("deepseek-coder-v2:16b")
    assets.add_chromedriver("146.0.7680.165")
    assets.sync_all()

Architecture:
    E:\AI-Setup\assets\
    ├── docker_images\      # Saved Docker tar files
    ├── huggingface\       # Hugging Face model cache
    ├── ollama\           # Ollama model files
    ├── chromedriver\     # Version-matched ChromeDriver
    ├── rocm\            # ROCm libraries (librocdxg, etc.)
    ├── pip\              # pip package wheels
    ├── transformers\     # Hugging Face transformers cache
    └── assets_manifest.json
"""

import os
import json
import hashlib
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

# Assets base directory
ASSETS_BASE = r"E:\AI-Setup\assets"
ASSETS_DB = os.path.join(ASSETS_BASE, "assets_manifest.json")


class SourceType(Enum):
    """Source of downloaded asset"""
    DOCKER = "docker"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    CHROMEDRIVER = "chromedriver"
    ROCM = "rocm"
    PIP = "pip"
    TRANSFORMERS = "transformers"
    MANUAL = "manual"
    DOWNLOAD = "download"


class AssetEntry:
    """Represents a downloaded asset"""
    
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
    def from_dict(cls, data: dict) -> 'AssetEntry':
        return cls(**data)
    
    def exists(self) -> bool:
        return os.path.exists(self.local_path)
    
    def update_size(self):
        """Update file size"""
        if self.exists():
            self.size_mb = os.path.getsize(self.local_path) / (1024 * 1024)
    
    def __repr__(self):
        status = "[OK]" if self.exists() else "[MISSING]"
        return f"<AssetEntry {status} {self.name} v{self.version} ({self.size_mb:.1f}MB)>"


class AssetsManager:
    """
    Manages local downloaded assets repository.
    
    Architecture:
    1. All artifacts downloaded to E:\AI-Setup\assets
    2. Manifest tracks all assets with metadata
    3. Check inventory to see what's present/outdated
    4. Sync updates target systems from local repo
    """
    
    def __init__(self):
        self.assets_base = ASSETS_BASE
        self.manifest_path = ASSETS_DB
        self.entries: Dict[str, AssetEntry] = {}
        self._ensure_dirs()
        self._load_manifest()
    
    def _ensure_dirs(self):
        """Create all asset subdirectories"""
        dirs = [
            self.assets_base,
            os.path.join(self.assets_base, "docker_images"),
            os.path.join(self.assets_base, "huggingface"),
            os.path.join(self.assets_base, "ollama"),
            os.path.join(self.assets_base, "chromedriver"),
            os.path.join(self.assets_base, "rocm"),
            os.path.join(self.assets_base, "pip"),
            os.path.join(self.assets_base, "transformers"),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)
    
    def _load_manifest(self):
        """Load assets manifest from disk"""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r') as f:
                    data = json.load(f)
                    self.entries = {
                        k: AssetEntry.from_dict(v) 
                        for k, v in data.items()
                    }
            except Exception as e:
                print(f"[assets] Failed to load manifest: {e}")
                self.entries = {}
    
    def _save_manifest(self):
        """Save assets manifest to disk"""
        with open(self.manifest_path, 'w') as f:
            data = {k: v.to_dict() for k, v in self.entries.items()}
            json.dump(data, f, indent=2)
    
    def _update_size(self, entry: AssetEntry):
        """Update size of asset"""
        if entry.exists():
            entry.size_mb = os.path.getsize(entry.local_path) / (1024 * 1024)
    
    def _get_dir(self, source_type: str) -> str:
        """Get assets directory for source type"""
        return os.path.join(self.assets_base, source_type)
    
    # === ASSET OPERATIONS ===
    
    def has(self, name: str, version: str = None) -> bool:
        """Check if asset is in repo"""
        key = f"{name}:{version}" if version else name
        entry = self.entries.get(key)
        return entry is not None and entry.exists()
    
    def get(self, name: str, version: str = None) -> Optional[str]:
        """Get asset path if exists"""
        key = f"{name}:{version}" if version else name
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
    ) -> AssetEntry:
        """Add asset to repo"""
        entry = AssetEntry(
            name=name,
            source_type=source_type,
            local_path=local_path,
            url=url,
            version=version,
            tags=tags,
            metadata=metadata
        )
        self._update_size(entry)
        
        key = f"{name}:{version}" if version else name
        self.entries[key] = entry
        self._save_manifest()
        return entry
    
    def remove(self, name: str, version: str = None) -> bool:
        """Remove asset from repo"""
        key = f"{name}:{version}" if version else name
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
        """Download and add to repo"""
        if not filename:
            filename = os.path.basename(url)
        
        dest_dir = self._get_dir(source_type)
        dest_path = os.path.join(dest_dir, filename)
        
        try:
            print(f"[assets] Downloading {url}...")
            print(f"[assets] -> {dest_path}")
            
            import urllib.request
            urllib.request.urlretrieve(url, dest_path)
            
            if not os.path.exists(dest_path):
                print(f"[assets] Download failed: file not created")
                return None
            
            size_mb = os.path.getsize(dest_path) / (1024 * 1024)
            print(f"[assets] Downloaded: {size_mb:.1f} MB")
            
            return self.add(
                name=name,
                source_type=source_type,
                local_path=dest_path,
                url=url,
                version=version,
                tags=tags,
                metadata=metadata
            ).local_path
            
        except Exception as e:
            print(f"[assets] Download failed: {e}")
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except:
                    pass
            return None
    
    def get_or_download(
        self,
        name: str,
        source_type: str,
        url: str = None,
        version: str = None,
        filename: str = None,
        tags: List[str] = None,
        metadata: Dict = None,
        check_updates: bool = False
    ) -> Optional[str]:
        """
        Get from repo or download if not present.
        
        This is the MAIN entry point for all downloads.
        """
        # Check repo first
        cached = self.get(name, version)
        if cached:
            print(f"[assets] Using cached: {name}:{version or 'latest'}")
            return cached
        
        # Need to download
        if not url:
            print(f"[assets] Not in repo and no URL provided: {name}")
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
    
    def list_by_source(self, source_type: str) -> List[AssetEntry]:
        """List assets by source type"""
        return [e for e in self.entries.values() if e.source_type == source_type]
    
    def list_all(self) -> List[AssetEntry]:
        """List all assets"""
        return list(self.entries.values())
    
    def list_present(self) -> List[AssetEntry]:
        """List assets that exist"""
        return [e for e in self.entries.values() if e.exists()]
    
    def list_missing(self) -> List[AssetEntry]:
        """List assets that don't exist"""
        return [e for e in self.entries.values() if not e.exists()]
    
    def inventory(self) -> Dict:
        """Get assets inventory"""
        present = self.list_present()
        missing = self.list_missing()
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
            'assets_dir': self.assets_base,
            'manifest': self.manifest_path,
            'total': len(self.entries),
            'present': len(present),
            'missing': len(missing),
            'size_mb': round(total_size, 2),
            'by_source': by_source,
            'timestamp': datetime.now().isoformat()
        }
    
    def sync_docker_image(self, image_name: str, tag: str = "latest") -> bool:
        """Load cached Docker image into Docker"""
        cache_file = os.path.join(self.assets_base, "docker_images", f"{image_name}:{tag}.tar")
        
        if not os.path.exists(cache_file):
            print(f"[assets] Image not in repo: {cache_file}")
            return False
        
        try:
            subprocess.run(['docker', 'load', '-i', cache_file], check=True, timeout=300)
            print(f"[assets] Loaded: {image_name}:{tag}")
            return True
        except Exception as e:
            print(f"[assets] Failed to load {image_name}: {e}")
            return False
    
    def save_docker_image(self, image_name: str, tag: str = "latest") -> Optional[str]:
        """Save Docker image to repo"""
        cache_file = os.path.join(self.assets_base, "docker_images", f"{image_name}:{tag}.tar")
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        
        try:
            subprocess.run(['docker', 'save', '-o', cache_file, f"{image_name}:{tag}"], check=True, timeout=600)
            
            self.add(
                name=f"{image_name}:{tag}",
                source_type=SourceType.DOCKER.value,
                local_path=cache_file,
                tags=["docker", "image"],
                metadata={"image": image_name, "tag": tag}
            )
            
            print(f"[assets] Saved: {cache_file}")
            return cache_file
        except Exception as e:
            print(f"[assets] Failed to save {image_name}: {e}")
            return None


# === GLOBAL INSTANCE ===

_assets = None

def get_assets() -> AssetsManager:
    """Get global AssetsManager instance"""
    global _assets
    if _assets is None:
        _assets = AssetsManager()
    return _assets


# === CONVENIENCE FUNCTIONS ===

def download_chromedriver(version: str = "146.0.7680.165") -> Optional[str]:
    """Download ChromeDriver (version-matched to Brave)"""
    assets = get_assets()
    
    base_url = "https://storage.googleapis.com/chrome-for-testing-public"
    url = f"{base_url}/{version}/win64/chromedriver-win64.zip"
    
    return assets.get_or_download(
        name="chromedriver",
        source_type=SourceType.CHROMEDRIVER.value,
        url=url,
        version=version,
        filename=f"chromedriver-{version}.zip",
        tags=["driver", "selenium"]
    )


# === MAIN ===

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Assets Manager")
    parser.add_argument("--inventory", "-i", action="store_true", help="Show inventory")
    parser.add_argument("--download-chromedriver", type=str, help="Download ChromeDriver")
    parser.add_argument("--has", type=str, help="Check if asset exists")
    parser.add_argument("--get", type=str, help="Get asset path")
    
    args = parser.parse_args()
    
    assets = get_assets()
    
    if args.inventory:
        inv = assets.inventory()
        print("=" * 60)
        print("ASSETS INVENTORY")
        print("=" * 60)
        print(f"Assets Dir: {inv['assets_dir']}")
        print(f"Total:      {inv['total']} | Present: {inv['present']} | Missing: {inv['missing']}")
        print(f"Size:       {inv['size_mb']:.2f} MB")
        print()
        print("By Source:")
        for src, stats in inv['by_source'].items():
            print(f"  {src:15} | Present: {stats['present']:2} | Missing: {stats['missing']:2} | {stats['size_mb']:8.2f} MB")
        print()
        print("Entries:")
        for e in assets.list_all():
            print(f"  {e}")
        print("=" * 60)
    
    elif args.download_chromedriver:
        path = download_chromedriver(args.download_chromedriver)
        if path:
            print(f"ChromeDriver: {path}")
    
    elif args.has:
        has = assets.has(args.has)
        print(f"Has {args.has}: {has}")
    
    elif args.get:
        path = assets.get(args.get)
        print(f"Path: {path}")
    
    else:
        inv = assets.inventory()
        print(f"Assets: {inv['present']}/{inv['total']} items, {inv['size_mb']:.1f} MB")
