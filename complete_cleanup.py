"""
Complete Workspace Cleanup - Removes all unnecessary files for production
Keeps only essential files for the Rush Royale Bot
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
    print("🧹 COMPLETE WORKSPACE CLEANUP")
    print("=" * 50)
    
    # Count initial files
    initial_count = count_files('.')
    print(f"Initial file count: {initial_count:,}")
    
    removed_count = 0
    
    # Files to remove from root directory
    unnecessary_files = [
        # Cleanup scripts
        'aggressive_cleanup.py',
        'cleanup_workspace.py',
        
        # Development documentation
        'BUGFIX_SUMMARY.md',
        'IMPLEMENTATION_SUMMARY.md', 
        'SCREENSHOT_FIX_SUMMARY.md',
        
        # Test files in root
        'test_pve_navigation.py',
        
        # Duplicate/old config
        'config.ini.template',
        
        # Development setup
        'setup_dev.bat',
        'run_tests.bat',
        '.pre-commit-config.yaml',
        'pyproject.toml',
        
        # Any backup files
        '*.bak',
        '*.backup',
        '*.orig',
        '*~'
    ]
    
    print(f"\n🗑️  Removing unnecessary files from root...")
    for file_pattern in unnecessary_files:
        if '*' in file_pattern:
            # Handle wildcards
            files = glob.glob(file_pattern)
            for file in files:
                if os.path.exists(file):
                    os.remove(file)
                    removed_count += 1
                    print(f"   ✅ Removed {file}")
        else:
            # Handle specific files
            if os.path.exists(file_pattern):
                os.remove(file_pattern)
                removed_count += 1
                print(f"   ✅ Removed {file_pattern}")
    
    # Directories to remove completely
    unnecessary_dirs = [
        'backups',
        'logs', 
        'reports',
        'tests',
        '.scrcpy'
    ]
    
    print(f"\n🗑️  Removing unnecessary directories...")
    for dir_name in unnecessary_dirs:
        if os.path.exists(dir_name):
            dir_files = count_files(dir_name)
            shutil.rmtree(dir_name, ignore_errors=True)
            removed_count += dir_files
            print(f"   ✅ Removed {dir_name}/ ({dir_files} files)")
    
    # Remove duplicate test_dependencies.py from root (keep only in tools/)
    if os.path.exists('test_dependencies.py'):
        os.remove('test_dependencies.py')
        removed_count += 1
        print(f"   ✅ Removed duplicate test_dependencies.py")
    
    # Clean up any remaining __pycache__ directories
    pycache_dirs = list(Path('.').rglob('__pycache__'))
    if pycache_dirs:
        print(f"\n🗑️  Removing {len(pycache_dirs)} __pycache__ directories...")
        for pycache_dir in pycache_dirs:
            cache_files = count_files(str(pycache_dir))
            shutil.rmtree(str(pycache_dir), ignore_errors=True)
            removed_count += cache_files
        print("   ✅ All __pycache__ directories removed")
    
    # Remove .venv313 if it still exists
    if os.path.exists('.venv313'):
        venv_files = count_files('.venv313')
        print(f"\n🗑️  Removing .venv313/ ({venv_files:,} files)...")
        shutil.rmtree('.venv313', ignore_errors=True)
        removed_count += venv_files
        print("   ✅ .venv313/ removed")
    
    # Remove temporary files
    temp_patterns = [
        '*.tmp', '*.temp', '*.log', '*.pyc', '*.pyo',
        'bot_feed_*.png', '.coverage', '*.pid'
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
    
    # Final count
    final_count = count_files('.')
    
    print("\n" + "=" * 50)
    print("📊 CLEANUP SUMMARY")
    print("=" * 50)
    print(f"Files before: {initial_count:,}")
    print(f"Files after:  {final_count:,}")
    print(f"Files removed: {removed_count:,}")
    if initial_count > 0:
        print(f"Reduction: {((initial_count - final_count) / initial_count * 100):.1f}%")
    
    print("\n✅ Complete cleanup finished!")
    print("\n📁 Remaining essential directories:")
    for item in sorted(os.listdir('.')):
        if os.path.isdir(item) and not item.startswith('.'):
            file_count = count_files(item)
            print(f"   📂 {item}/ ({file_count} files)")
    
    print(f"\n🎯 Workspace ready for production with {final_count} files!")

if __name__ == "__main__":
    main()
