#!/usr/bin/env python3
"""
Comprehensive Workspace Cleanup Script
Removes temporary files, organizes documentation, and prepares the workspace for production use.
"""

import os
import shutil
import glob
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def cleanup_temporary_files():
    """Remove temporary and debug files"""
    logger.info("🧹 Cleaning temporary files...")
    
    # Files to remove
    temp_patterns = [
        "test_*.py",
        "demo_*.py", 
        "*debug*.json",
        "*debug*.png",
        "*.tmp",
        "*.temp",
        "test_*.bat",
        "*.pyc"
    ]
    
    # Directories to remove
    temp_dirs = [
        "debug_output",
        "__pycache__",
        ".pytest_cache",
        ".coverage",
        "htmlcov",
        ".mypy_cache"
    ]
    
    removed_files = 0
    removed_dirs = 0
    
    # Remove files matching patterns
    for pattern in temp_patterns:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                logger.info(f"   Removed file: {file_path}")
                removed_files += 1
            except Exception as e:
                logger.warning(f"   Could not remove {file_path}: {e}")
    
    # Remove temporary directories
    for dir_name in temp_dirs:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                logger.info(f"   Removed directory: {dir_name}")
                removed_dirs += 1
            except Exception as e:
                logger.warning(f"   Could not remove {dir_name}: {e}")
    
    # Clean Src directory
    src_cache = Path("Src") / "__pycache__"
    if src_cache.exists():
        try:
            shutil.rmtree(src_cache)
            logger.info(f"   Removed directory: {src_cache}")
            removed_dirs += 1
        except Exception as e:
            logger.warning(f"   Could not remove {src_cache}: {e}")
    
    logger.info(f"✅ Cleanup complete: {removed_files} files, {removed_dirs} directories removed")

def organize_documentation():
    """Organize documentation files into appropriate directories"""
    logger.info("📚 Organizing documentation...")
    
    # Ensure wiki directory exists
    wiki_dir = Path("wiki")
    wiki_dir.mkdir(exist_ok=True)
    
    # Documentation files to move to wiki
    doc_files = [
        "DEBUG_MODE_GUIDE.md",
        "DEBUG_IMPLEMENTATION_SUMMARY.md", 
        "PVE_NAVIGATION_FIX.md"
    ]
    
    moved_files = 0
    for doc_file in doc_files:
        if os.path.exists(doc_file):
            try:
                dest = wiki_dir / doc_file
                shutil.move(doc_file, dest)
                logger.info(f"   Moved: {doc_file} → wiki/{doc_file}")
                moved_files += 1
            except Exception as e:
                logger.warning(f"   Could not move {doc_file}: {e}")
    
    logger.info(f"✅ Documentation organized: {moved_files} files moved to wiki/")

def update_gitignore():
    """Update .gitignore with comprehensive patterns"""
    logger.info("📝 Updating .gitignore...")
    
    gitignore_path = Path(".gitignore")
    
    # Additional patterns to ensure are in .gitignore
    additional_patterns = [
        "",
        "# Cleanup patterns",
        "test_*.py",
        "demo_*.py",
        "*debug*.json",
        "*debug*.png",
        "debug_output/",
        "*.tmp",
        "*.temp",
        ".coverage",
        "htmlcov/",
        ".pytest_cache/",
        ".mypy_cache/"
    ]
    
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            existing_content = f.read()
        
        # Add patterns that aren't already present
        patterns_to_add = []
        for pattern in additional_patterns:
            if pattern not in existing_content:
                patterns_to_add.append(pattern)
        
        if patterns_to_add:
            with open(gitignore_path, 'a') as f:
                f.write('\n'.join(patterns_to_add) + '\n')
            logger.info(f"   Added {len(patterns_to_add)} new patterns to .gitignore")
        else:
            logger.info("   .gitignore is up to date")
    else:
        logger.warning("   .gitignore not found")

def verify_production_files():
    """Verify essential production files are present"""
    logger.info("🔍 Verifying production files...")
    
    essential_files = [
        "launch_gui.bat",
        "config.ini.template",
        "requirements.txt",
        "README.md",
        "Src/bot_core.py",
        "Src/bot_handler.py",
        "Src/gui.py",
        "tools/health_check.py"
    ]
    
    missing_files = []
    for file_path in essential_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.warning(f"   Missing essential files: {missing_files}")
    else:
        logger.info("   ✅ All essential production files present")

def show_workspace_summary():
    """Show summary of workspace structure"""
    logger.info("📊 Workspace Summary:")
    
    # Count files by type
    counts = {
        'Python files': len(glob.glob("**/*.py", recursive=True)),
        'Batch files': len(glob.glob("*.bat")),
        'Config files': len(glob.glob("*.ini*")),
        'Documentation': len(glob.glob("**/*.md", recursive=True)),
        'Image files': len(glob.glob("**/*.png", recursive=True))
    }
    
    for file_type, count in counts.items():
        logger.info(f"   {file_type}: {count}")
    
    # Show directory structure
    logger.info("\n📁 Directory Structure:")
    for root, dirs, files in os.walk('.'):
        level = root.replace('.', '').count(os.sep)
        indent = ' ' * 2 * level
        logger.info(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files[:3]:  # Show first 3 files
            logger.info(f"{subindent}{file}")
        if len(files) > 3:
            logger.info(f"{subindent}... and {len(files) - 3} more files")

def main():
    """Main cleanup function"""
    logger.info("🚀 Rush Royale Bot - Workspace Cleanup")
    logger.info("=" * 50)
    
    try:
        cleanup_temporary_files()
        organize_documentation() 
        update_gitignore()
        verify_production_files()
        show_workspace_summary()
        
        logger.info("=" * 50)
        logger.info("🎉 Cleanup completed successfully!")
        logger.info("💡 Workspace is now ready for production use")
        logger.info("🚀 Run 'launch_gui.bat' to start the bot")
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
