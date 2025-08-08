#!/usr/bin/env python3
"""
Cleanup Script for Rush Royale Bot
Removes temporary files and old implementations that are no longer needed
"""

import os
import shutil
from pathlib import Path

def cleanup_files():
    """Remove temporary and obsolete files"""
    print("🧹 CLEANUP: Removing temporary and obsolete files...")
    
    project_root = Path.cwd()
    files_to_remove = [
        # Test screenshots
        'sync_screenshot.png',
        'modern_screenshot.png',
        'test_screenshot.png',
        
        # Test logs
        'scrcpy_manager_test.log',
        
        # Other temporary files
        'bot_feed_emulator-5554.png',
    ]
    
    removed_count = 0
    for file_name in files_to_remove:
        file_path = project_root / file_name
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"   ✅ Removed: {file_name}")
                removed_count += 1
            except Exception as e:
                print(f"   ❌ Failed to remove {file_name}: {e}")
    
    print(f"🧹 Cleanup completed: {removed_count} files removed")

def cleanup_pycache():
    """Remove __pycache__ directories"""
    print("\n🧹 CLEANUP: Removing __pycache__ directories...")
    
    project_root = Path.cwd()
    removed_count = 0
    
    for pycache_dir in project_root.rglob('__pycache__'):
        if pycache_dir.is_dir():
            try:
                shutil.rmtree(pycache_dir)
                print(f"   ✅ Removed: {pycache_dir.relative_to(project_root)}")
                removed_count += 1
            except Exception as e:
                print(f"   ❌ Failed to remove {pycache_dir.relative_to(project_root)}: {e}")
    
    print(f"🧹 Cache cleanup completed: {removed_count} directories removed")

def main():
    """Run cleanup operations"""
    print("🎯 RUSH ROYALE BOT CLEANUP")
    print("=" * 50)
    print("Cleaning up temporary files and caches...")
    print("=" * 50)
    
    cleanup_files()
    cleanup_pycache()
    
    print("\n🎉 All cleanup operations completed!")
    print("\nThe bot is now clean and ready for production use.")

if __name__ == "__main__":
    main()
