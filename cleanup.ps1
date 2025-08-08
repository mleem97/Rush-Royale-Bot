# Rush Royale Bot Cleanup Script
# PowerShell script to remove temporary files and caches

param(
    [switch]$SkipPyCache,
    [switch]$Verbose
)

function Write-StatusMessage {
    param([string]$Message, [string]$Status = "INFO")
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    switch ($Status) {
        "SUCCESS" { Write-Host "[$timestamp] ✅ $Message" -ForegroundColor Green }
        "ERROR"   { Write-Host "[$timestamp] ❌ $Message" -ForegroundColor Red }
        "WARNING" { Write-Host "[$timestamp] ⚠️ $Message" -ForegroundColor Yellow }
        default   { Write-Host "[$timestamp] ℹ️ $Message" -ForegroundColor Cyan }
    }
}

function Remove-TemporaryFiles {
    Write-StatusMessage "Removing temporary and obsolete files..."
    
    $filesToRemove = @(
        # Test screenshots
        "sync_screenshot.png",
        "modern_screenshot.png", 
        "test_screenshot.png",
        
        # Test logs
        "scrcpy_manager_test.log",
        
        # Bot feed screenshots
        "bot_feed_emulator-5554.png",
        
        # Test scripts (if user wants to clean them)
        "test_scrcpy_manager.py",
        "test_auto_download.py"
    )
    
    $removedCount = 0
    
    foreach ($fileName in $filesToRemove) {
        $filePath = Join-Path $PWD $fileName
        
        if (Test-Path $filePath) {
            try {
                Remove-Item $filePath -Force
                Write-StatusMessage "Removed: $fileName" "SUCCESS"
                $removedCount++
            }
            catch {
                Write-StatusMessage "Failed to remove $fileName`: $($_.Exception.Message)" "ERROR"
            }
        }
        elseif ($Verbose) {
            Write-StatusMessage "File not found: $fileName" "WARNING"
        }
    }
    
    Write-StatusMessage "Cleanup completed: $removedCount files removed"
    return $removedCount
}

function Remove-PyCacheDirectories {
    if ($SkipPyCache) {
        Write-StatusMessage "Skipping __pycache__ cleanup (--SkipPyCache specified)"
        return 0
    }
    
    Write-StatusMessage "Removing __pycache__ directories..."
    
    $pycacheDirs = Get-ChildItem -Path $PWD -Recurse -Directory -Name "__pycache__" -ErrorAction SilentlyContinue
    $removedCount = 0
    
    foreach ($dir in $pycacheDirs) {
        $fullPath = Join-Path $PWD $dir
        
        try {
            Remove-Item $fullPath -Recurse -Force
            Write-StatusMessage "Removed: $dir" "SUCCESS"
            $removedCount++
        }
        catch {
            Write-StatusMessage "Failed to remove $dir`: $($_.Exception.Message)" "ERROR"
        }
    }
    
    Write-StatusMessage "Cache cleanup completed: $removedCount directories removed"
    return $removedCount
}

function Remove-ScrcpyDownloads {
    Write-StatusMessage "Checking for temporary scrcpy downloads..."
    
    $scrcpyTemp = Join-Path $PWD ".scrcpy_temp"
    $removedCount = 0
    
    if (Test-Path $scrcpyTemp) {
        try {
            Remove-Item $scrcpyTemp -Recurse -Force
            Write-StatusMessage "Removed temporary scrcpy directory: .scrcpy_temp" "SUCCESS"
            $removedCount++
        }
        catch {
            Write-StatusMessage "Failed to remove .scrcpy_temp: $($_.Exception.Message)" "ERROR"
        }
    }
    
    # Check for any .zip or .tar.gz files that might be leftover downloads
    $downloadFiles = Get-ChildItem -Path $PWD -File | Where-Object { 
        $_.Name -match "scrcpy.*\.(zip|tar\.gz)$" 
    }
    
    foreach ($file in $downloadFiles) {
        try {
            Remove-Item $file.FullName -Force
            Write-StatusMessage "Removed download file: $($file.Name)" "SUCCESS"
            $removedCount++
        }
        catch {
            Write-StatusMessage "Failed to remove $($file.Name): $($_.Exception.Message)" "ERROR"
        }
    }
    
    if ($removedCount -eq 0) {
        Write-StatusMessage "No temporary scrcpy files found"
    }
    
    return $removedCount
}

function Show-Header {
    Write-Host ""
    Write-Host "🎯 RUSH ROYALE BOT CLEANUP (PowerShell)" -ForegroundColor Magenta
    Write-Host "=" * 60 -ForegroundColor Gray
    Write-Host "Cleaning up temporary files and caches..." -ForegroundColor White
    Write-Host "=" * 60 -ForegroundColor Gray
    Write-Host ""
}

function Show-Summary {
    param([int]$TotalFilesRemoved, [int]$TotalDirsRemoved, [int]$ScrcpyFilesRemoved)
    
    Write-Host ""
    Write-Host "📊 CLEANUP SUMMARY" -ForegroundColor Magenta
    Write-Host "=" * 30 -ForegroundColor Gray
    Write-StatusMessage "Files removed: $TotalFilesRemoved" "SUCCESS"
    Write-StatusMessage "Directories removed: $TotalDirsRemoved" "SUCCESS"
    Write-StatusMessage "Scrcpy temp files removed: $ScrcpyFilesRemoved" "SUCCESS"
    Write-Host ""
    Write-Host "🎉 All cleanup operations completed!" -ForegroundColor Green
    Write-Host "The bot is now clean and ready for production use." -ForegroundColor White
    Write-Host ""
}

# Main execution
try {
    Show-Header
    
    $filesRemoved = Remove-TemporaryFiles
    $dirsRemoved = Remove-PyCacheDirectories  
    $scrcpyRemoved = Remove-ScrcpyDownloads
    
    Show-Summary -TotalFilesRemoved $filesRemoved -TotalDirsRemoved $dirsRemoved -ScrcpyFilesRemoved $scrcpyRemoved
}
catch {
    Write-StatusMessage "Cleanup script failed: $($_.Exception.Message)" "ERROR"
    exit 1
}
