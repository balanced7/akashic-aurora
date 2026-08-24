"""
Cache Update Checker - Verify and Update Cached Items
================================================
Checks if cached items are current, downloads updates if needed.

Usage:
    python cache_update_checker.py --check-all
    python cache_update_checker.py --check-source rocm
    python cache_update_checker.py --update chromedriver
"""

import sys
import os
import json
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, r'E:\AI-Setup')
from assets_manager import AssetsManager, SourceType


class CacheUpdateChecker:
    """
    Checks if cached items are current and can update them.
    """
    
    # Known latest versions for various artifacts
    KNOWN_LATEST = {
        SourceType.CHROMEDRIVER.value: {
            "url_template": "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json",
            "version_key": "chromedriver",
        },
        SourceType.HUGGINGFACE.value: {
            # Hugging Face uses git clone, handled differently
        },
        SourceType.OLLAMA.value: {
            # Ollama has ollama CLI for management
        }
    }
    
    def __init__(self):
        self.cache = CacheManager()
    
    def check_chromedriver_versions(self) -> Dict:
        """Check available ChromeDriver versions"""
        try:
            url = self.KNOWN_LATEST[SourceType.CHROMEDRIVER.value]["url_template"]
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read())
            
            versions = []
            for item in data.get('versions', []):
                ver = item['version']
                downloads = item.get('downloads', {}).get('chromedriver', [])
                for d in downloads:
                    if 'win64' in d['url']:
                        versions.append({
                            'version': ver,
                            'url': d['url']
                        })
                        break
            
            return {'status': 'ok', 'versions': versions[-10:]}  # Last 10
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def check_item_current(self, name: str) -> Dict:
        """
        Check if a cached item is current.
        
        Returns:
            Dict with 'current' (bool), 'latest_version', 'message'
        """
        entry = self.cache.get(name)
        if not entry:
            return {'current': False, 'message': 'Not in cache'}
        
        if not entry.exists():
            return {'current': False, 'message': 'File missing'}
        
        # For chromedriver, check version
        if entry.source_type == SourceType.CHROMEDRIVER.value:
            result = self.check_chromedriver_versions()
            if result['status'] == 'ok':
                latest = result['versions'][-1]['version'] if result['versions'] else None
                if latest and entry.version != latest:
                    return {
                        'current': False,
                        'latest_version': latest,
                        'cached_version': entry.version,
                        'message': f'Newer version available: {latest}'
                    }
                return {'current': True, 'version': entry.version, 'message': 'Current'}
        
        return {'current': True, 'message': 'Cache is current'}
    
    def check_all(self) -> Dict:
        """Check all cached items for updates"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'items': {},
            'summary': {'current': 0, 'needs_update': 0, 'errors': 0}
        }
        
        for name in self.cache.entries:
            result = self.check_item_current(name)
            results['items'][name] = result
            
            if result.get('current'):
                results['summary']['current'] += 1
            elif 'error' in result:
                results['summary']['errors'] += 1
            else:
                results['summary']['needs_update'] += 1
        
        return results
    
    def check_source(self, source_type: str) -> List[str]:
        """Check items by source type"""
        items = self.cache.list_by_source(source_type)
        results = []
        
        for item in items:
            status = self.check_item_current(item.name)
            results.append({
                'name': item.name,
                'version': item.version,
                'status': status
            })
        
        return results
    
    def download_update(self, name: str) -> Optional[str]:
        """Download an update for a cached item"""
        entry = self.cache.get(name)
        if not entry:
            print(f"[updater] Not in cache: {name}")
            return None
        
        if entry.source_type == SourceType.CHROMEDRIVER.value:
            # Get latest version
            result = self.check_chromedriver_versions()
            if result['status'] == 'ok' and result['versions']:
                latest = result['versions'][-1]
                print(f"[updater] Latest ChromeDriver: {latest['version']}")
                
                # Download
                return self.cache.download(latest['url'], f"chromedriver-{latest['version']}.zip")
        
        print(f"[updater] Don't know how to update: {name}")
        return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Cache Update Checker")
    parser.add_argument("--check-all", action="store_true", help="Check all cached items")
    parser.add_argument("--check-source", type=str, help="Check items by source (e.g., chromedriver)")
    parser.add_argument("--update", type=str, help="Update a specific item")
    parser.add_argument("--check-chromedriver", action="store_true", help="Check ChromeDriver versions")
    
    args = parser.parse_args()
    
    checker = CacheUpdateChecker()
    
    if args.check_all:
        print("=" * 60)
        print("CACHE UPDATE CHECK")
        print("=" * 60)
        
        results = checker.check_all()
        
        print(f"\nTimestamp: {results['timestamp']}")
        print(f"\nSummary:")
        print(f"  Current:      {results['summary']['current']}")
        print(f"  Needs Update: {results['summary']['needs_update']}")
        print(f"  Errors:       {results['summary']['errors']}")
        
        print("\nItems:")
        for name, result in results['items'].items():
            if result.get('current'):
                print(f"  [OK]  {name}")
            elif 'error' in result:
                print(f"  [ERR] {name}: {result.get('message')}")
            else:
                print(f"  [!!]  {name}: {result.get('message')}")
    
    elif args.check_source:
        print(f"Checking source: {args.check_source}")
        results = checker.check_source(args.check_source)
        for r in results:
            print(f"  {r['name']}: {r['status']}")
    
    elif args.update:
        print(f"Updating: {args.update}")
        result = checker.download_update(args.update)
        if result:
            print(f"Updated: {result}")
    
    elif args.check_chromedriver:
        print("Checking ChromeDriver versions...")
        result = checker.check_chromedriver_versions()
        if result['status'] == 'ok':
            print("Latest versions:")
            for v in result['versions'][-5:]:
                print(f"  {v['version']}")
        else:
            print(f"Error: {result.get('message')}")
    
    else:
        # Default: show quick status
        checker.cache.inventory()
        print("\nRun with --check-all to verify updates")


if __name__ == "__main__":
    main()
