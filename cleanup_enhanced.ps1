# Enhanced Windows Cleanup Script for Rush Royale Bot
# Usage examples:
#   .\cleanup.ps1                    # Standard cleanup
#   .\cleanup.ps1 -Verbose           # Detailed output
#   .\cleanup.ps1 -SkipPyCache       # Skip Python cache cleanup
#   .\cleanup.ps1 -WhatIf            # Preview what would be removed

param(
    [switch]$SkipPyCache,
    [switch]$Verbose,
    [switch]$WhatIf,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
🎯 RUSH ROYALE BOT CLEANUP SCRIPT

USAGE:
    .\cleanup.ps1 [OPTIONS]

OPTIONS:
    -Verbose        Show detailed output including files not found
    -SkipPyCache    Skip removal of __pycache__ directories  
    -WhatIf         Preview what would be removed without actually deleting
    -Help           Show this help message

EXAMPLES:
    .\cleanup.ps1                    # Standard cleanup
    .\cleanup.ps1 -Verbose           # Detailed output
    .\cleanup.ps1 -SkipPyCache       # Skip Python cache cleanup
    .\cleanup.ps1 -WhatIf            # Preview mode

This script removes:
- Temporary screenshots (*.png test files)
- Test log files
- Python __pycache__ directories
- Temporary scrcpy downloads
- Old test scripts
"@
    exit 0
}

function Write-StatusMessage {
    param([string]$Message, [string]$Status = "INFO")
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    switch ($Status) {
        "SUCCESS" { Write-Host "[$timestamp] ✅ $Message" -ForegroundColor Green }
        "ERROR"   { Write-Host "[$timestamp] ❌ $Message" -ForegroundColor Red }
        "WARNING" { Write-Host "[$timestamp] ⚠️ $Message" -ForegroundColor Yellow }
        "PREVIEW" { Write-Host "[$timestamp] 👁️ $Message" -ForegroundColor Magenta }
        default   { Write-Host "[$timestamp] ℹ️ $Message" -ForegroundColor Cyan }
    }
}

function Remove-TemporaryFiles {
    $action = if ($WhatIf) { "Would remove" } else { "Removing" }
    Write-StatusMessage "$action temporary and obsolete files..."
    
    $filesToRemove = @(
        # Test screenshots
        "sync_screenshot.png",
        "modern_screenshot.png", 
        "test_screenshot.png",
        
        # Test logs
        "scrcpy_manager_test.log",
        "bot_test.log",
        
        # Bot feed screenshots (current session)
        "bot_feed_emulator-5554.png",
        
        # Test scripts (optional cleanup)
        "test_scrcpy_manager.py",
        "test_auto_download.py",
        
        # Old documentation
        "SCRCPY_MANAGER_README.md"
    )
    
    $removedCount = 0
    
    foreach ($fileName in $filesToRemove) {
        $filePath = Join-Path $PWD $fileName
        
        if (Test-Path $filePath) {
            if ($WhatIf) {
                Write-StatusMessage "Would remove: $fileName" "PREVIEW"
                $removedCount++
            }
            else {
                try {
                    Remove-Item $filePath -Force
                    Write-StatusMessage "Removed: $fileName" "SUCCESS"
                    $removedCount++
                }
                catch {
                    Write-StatusMessage "Failed to remove $fileName`: $($_.Exception.Message)" "ERROR"
                }
            }
        }
        elseif ($Verbose) {
            Write-StatusMessage "File not found: $fileName" "WARNING"
        }
    }
    
    $actionComplete = if ($WhatIf) { "Would complete cleanup" } else { "Cleanup completed" }
    Write-StatusMessage "$actionComplete`: $removedCount files"
    return $removedCount
}

function Remove-PyCacheDirectories {
    if ($SkipPyCache) {
        Write-StatusMessage "Skipping __pycache__ cleanup (--SkipPyCache specified)"
        return 0
    }
    
    $action = if ($WhatIf) { "Would remove" } else { "Removing" }
    Write-StatusMessage "$action __pycache__ directories..."
    
    try {
        $pycacheDirs = Get-ChildItem -Path $PWD -Recurse -Directory -Name "__pycache__" -ErrorAction SilentlyContinue
        $removedCount = 0
        
        foreach ($dir in $pycacheDirs) {
            $fullPath = Join-Path $PWD $dir
            
            if ($WhatIf) {
                Write-StatusMessage "Would remove: $dir" "PREVIEW"
                $removedCount++
            }
            else {
                try {
                    Remove-Item $fullPath -Recurse -Force
                    Write-StatusMessage "Removed: $dir" "SUCCESS"
                    $removedCount++
                }
                catch {
                    Write-StatusMessage "Failed to remove $dir`: $($_.Exception.Message)" "ERROR"
                }
            }
        }
        
        $actionComplete = if ($WhatIf) { "Would complete cache cleanup" } else { "Cache cleanup completed" }
        Write-StatusMessage "$actionComplete`: $removedCount directories"
        return $removedCount
    }
    catch {
        Write-StatusMessage "Error scanning for __pycache__ directories: $($_.Exception.Message)" "ERROR"
        return 0
    }
}

function Remove-ScrcpyDownloads {
    $action = if ($WhatIf) { "Would check" } else { "Checking" }
    Write-StatusMessage "$action for temporary scrcpy downloads..."
    
    $itemsToRemove = @()
    $removedCount = 0
    
    # Check for temp directory
    $scrcpyTemp = Join-Path $PWD ".scrcpy_temp"
    if (Test-Path $scrcpyTemp) {
        $itemsToRemove += $scrcpyTemp
    }
    
    # Check for download files
    try {
        $downloadFiles = Get-ChildItem -Path $PWD -File | Where-Object { 
            $_.Name -match "scrcpy.*\.(zip|tar\.gz)$" 
        }
        if ($downloadFiles) {
            $itemsToRemove += $downloadFiles.FullName
        }
    }
    catch {
        Write-StatusMessage "Error scanning for download files: $($_.Exception.Message)" "ERROR"
    }
    
    foreach ($item in $itemsToRemove) {
        $itemName = Split-Path $item -Leaf
        
        if ($WhatIf) {
            Write-StatusMessage "Would remove: $itemName" "PREVIEW"
            $removedCount++
        }
        else {
            try {
                if (Test-Path $item -PathType Container) {
                    Remove-Item $item -Recurse -Force
                }
                else {
                    Remove-Item $item -Force
                }
                Write-StatusMessage "Removed: $itemName" "SUCCESS"
                $removedCount++
            }
            catch {
                Write-StatusMessage "Failed to remove $itemName`: $($_.Exception.Message)" "ERROR"
            }
        }
    }
    
    if ($removedCount -eq 0) {
        $message = if ($WhatIf) { "No temporary scrcpy files would be removed" } else { "No temporary scrcpy files found" }
        Write-StatusMessage $message
    }
    
    return $removedCount
}

function Show-Header {
    $mode = if ($WhatIf) { " (PREVIEW MODE)" } else { "" }
    
    Write-Host ""
    Write-Host "🎯 RUSH ROYALE BOT CLEANUP (PowerShell)$mode" -ForegroundColor Magenta
    Write-Host "=" * 60 -ForegroundColor Gray
    
    if ($WhatIf) {
        Write-Host "👁️ PREVIEW MODE: No files will actually be deleted" -ForegroundColor Yellow
        Write-Host "=" * 60 -ForegroundColor Gray
    }
    else {
        Write-Host "Cleaning up temporary files and caches..." -ForegroundColor White
        Write-Host "=" * 60 -ForegroundColor Gray
    }
    Write-Host ""
}

function Show-Summary {
    param([int]$TotalFilesRemoved, [int]$TotalDirsRemoved, [int]$ScrcpyFilesRemoved)
    
    $action = if ($WhatIf) { "PREVIEW SUMMARY" } else { "CLEANUP SUMMARY" }
    
    Write-Host ""
    Write-Host "📊 $action" -ForegroundColor Magenta
    Write-Host "=" * 30 -ForegroundColor Gray
    
    if ($WhatIf) {
        Write-StatusMessage "Files that would be removed: $TotalFilesRemoved" "PREVIEW"
        Write-StatusMessage "Directories that would be removed: $TotalDirsRemoved" "PREVIEW"
        Write-StatusMessage "Scrcpy temp files that would be removed: $ScrcpyFilesRemoved" "PREVIEW"
        Write-Host ""
        Write-Host "👁️ This was a preview. Run without -WhatIf to actually clean up." -ForegroundColor Yellow
    }
    else {
        Write-StatusMessage "Files removed: $TotalFilesRemoved" "SUCCESS"
        Write-StatusMessage "Directories removed: $TotalDirsRemoved" "SUCCESS"
        Write-StatusMessage "Scrcpy temp files removed: $ScrcpyFilesRemoved" "SUCCESS"
        Write-Host ""
        Write-Host "🎉 All cleanup operations completed!" -ForegroundColor Green
        Write-Host "The bot is now clean and ready for production use." -ForegroundColor White
    }
    Write-Host ""
}

# Main execution
try {
    Show-Header
    
    $filesRemoved = Remove-TemporaryFiles
    $dirsRemoved = Remove-PyCacheDirectories  
    $scrcpyRemoved = Remove-ScrcpyDownloads
    
    Show-Summary -TotalFilesRemoved $filesRemoved -TotalDirsRemoved $dirsRemoved -ScrcpyFilesRemoved $scrcpyRemoved
    
    if ($WhatIf) {
        exit 0
    }
}
catch {
    Write-StatusMessage "Cleanup script failed: $($_.Exception.Message)" "ERROR"
    exit 1
}
