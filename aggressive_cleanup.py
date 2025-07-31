"""
Aggressive Workspace Cleanup - Removes .venv313 and other development artifacts
This will require recreating the virtual environment afterwards.
"""
import os
import shutil
import glob
from pathlib import Path

def count_files(directory):
    """Count total files in directory"""
    try:
        return sum(1 for _ in Path(directory).rglob('*') if _.is_file())
    except:
        return 0

def main():
    print("🧹 AGGRESSIVE WORKSPACE CLEANUP")
    print("=" * 50)
    
    # Count initial files
    initial_count = count_files('.')
    print(f"Initial file count: {initial_count:,}")
    
    removed_count = 0
    
    # 1. Remove .venv313 (Virtual Environment) - The main culprit
    if os.path.exists('.venv313'):
        venv_files = count_files('.venv313')
        print(f"\n🗑️  Removing .venv313/ ({venv_files:,} files)...")
        shutil.rmtree('.venv313', ignore_errors=True)
        removed_count += venv_files
        print("   ✅ .venv313/ removed")
    
    # 2. Remove .scrcpy cache
    if os.path.exists('.scrcpy'):
        scrcpy_files = count_files('.scrcpy')
        print(f"\n🗑️  Removing .scrcpy/ cache ({scrcpy_files} files)...")
        shutil.rmtree('.scrcpy', ignore_errors=True)
        removed_count += scrcpy_files
        print("   ✅ .scrcpy/ removed")
    
    # 3. Remove __pycache__ directories
    pycache_dirs = list(Path('.').rglob('__pycache__'))
    if pycache_dirs:
        print(f"\n🗑️  Removing {len(pycache_dirs)} __pycache__ directories...")
        for pycache_dir in pycache_dirs:
            cache_files = count_files(str(pycache_dir))
            shutil.rmtree(str(pycache_dir), ignore_errors=True)
            removed_count += cache_files
        print("   ✅ All __pycache__ directories removed")
    
    # 4. Remove temporary and log files
    temp_patterns = [
        '*.tmp', '*.temp', '*.log', '*.pyc', '*.pyo',
        'bot_feed_*.png', '.pytest_cache', '.coverage'
    ]
    
    print(f"\n🗑️  Removing temporary files...")
    for pattern in temp_patterns:
        files = list(Path('.').rglob(pattern))
        for file in files:
            if file.is_file():
                try:
                    file.unlink()
                    removed_count += 1
                except:
                    pass
        if files:
            print(f"   ✅ Removed {len(files)} {pattern} files")
    
    # 5. Remove duplicate tools from root (keep only in tools/)
    root_tools = [
        'device_manager.py', 'fix_multiple_devices.py', 'health_check.bat', 
        'fix_devices.bat'
    ]
    
    print(f"\n🗑️  Removing duplicate tool files from root...")
    for tool in root_tools:
        if os.path.exists(tool):
            os.remove(tool)
            removed_count += 1
            print(f"   ✅ Removed {tool}")
    
    # 6. Clean up any old backup files
    backup_patterns = ['*.bak', '*.backup', '*~', '*.orig']
    for pattern in backup_patterns:
        files = list(Path('.').rglob(pattern))
        for file in files:
            if file.is_file():
                try:
                    file.unlink()
                    removed_count += 1
                except:
                    pass
    
    # Final count
    final_count = count_files('.')
    
    print("\n" + "=" * 50)
    print("📊 CLEANUP SUMMARY")
    print("=" * 50)
    print(f"Files before: {initial_count:,}")
    print(f"Files after:  {final_count:,}")
    print(f"Files removed: {removed_count:,}")
    print(f"Reduction: {((initial_count - final_count) / initial_count * 100):.1f}%")
    
    print("\n⚠️  IMPORTANT: Virtual environment removed!")
    print("   Run 'install.bat' to recreate .venv313 when needed")
    
    print("\n✅ Aggressive cleanup complete!")

if __name__ == "__main__":
    main()
