"""
Future-Proof Scrcpy Integration for Python 3.13-3.15
Auto-download and management with modern subprocess approach
"""
from __future__ import annotations

import subprocess
import asyncio
import os
import time
import logging
import platform
import zipfile
import tarfile
import json
from pathlib import Path
from typing import Optional, Tuple, Union, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import shutil
import urllib.request
import urllib.error


class ScrcpyManager:
    """Auto-detecting and downloading scrcpy manager for all platforms"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.project_root = Path.cwd()
        self.scrcpy_dir = self.project_root / '.scrcpy'
        self.scrcpy_path = self._find_or_install_scrcpy()
        
    def _find_or_install_scrcpy(self) -> Optional[Path]:
        """Find scrcpy in system or auto-install latest version"""
        self.logger.info("🔍 Searching for scrcpy installation...")
        
        # 1. Check system PATH
        system_path = self._find_system_scrcpy()
        if system_path:
            self.logger.info(f"✅ Found scrcpy in system PATH: {system_path}")
            return system_path
            
        # 2. Check .scrcpy directory
        local_path = self._find_local_scrcpy()
        if local_path:
            self.logger.info(f"✅ Found scrcpy in project: {local_path}")
            return local_path
            
        # 3. Auto-download latest version
        self.logger.info("📥 scrcpy not found, downloading latest version...")
        download_path = self._download_latest_scrcpy()
        if download_path:
            self.logger.info(f"✅ Downloaded scrcpy to: {download_path}")
            return download_path
            
        self.logger.error("❌ Failed to find or install scrcpy")
        return None
    
    def _find_system_scrcpy(self) -> Optional[Path]:
        """Check if scrcpy is available in system PATH"""
        system_name = platform.system().lower()
        executable_name = 'scrcpy.exe' if system_name == 'windows' else 'scrcpy'
        
        # Use shutil.which for cross-platform PATH search
        scrcpy_path = shutil.which(executable_name)
        if scrcpy_path:
            return Path(scrcpy_path)
            
        # Additional Windows locations
        if system_name == 'windows':
            common_paths = [
                Path('C:/Program Files/scrcpy/scrcpy.exe'),
                Path('C:/Program Files (x86)/scrcpy/scrcpy.exe'),
                Path.home() / 'scrcpy' / 'scrcpy.exe',
            ]
            
            for path in common_paths:
                if path.exists():
                    return path
                    
        return None
    
    def _find_local_scrcpy(self) -> Optional[Path]:
        """Check if scrcpy exists in .scrcpy directory"""
        if not self.scrcpy_dir.exists():
            return None
            
        system_name = platform.system().lower()
        executable_name = 'scrcpy.exe' if system_name == 'windows' else 'scrcpy'
        
        scrcpy_executable = self.scrcpy_dir / executable_name
        if scrcpy_executable.exists():
            return scrcpy_executable
            
        return None
    
    def _download_latest_scrcpy(self) -> Optional[Path]:
        """Download and extract latest scrcpy release"""
        try:
            # Get latest release info from GitHub API
            api_url = "https://api.github.com/repos/Genymobile/scrcpy/releases/latest"
            self.logger.info(f"🌐 Fetching latest release info from: {api_url}")
            
            with urllib.request.urlopen(api_url, timeout=10) as response:
                release_data = json.loads(response.read().decode())
            
            version = release_data['tag_name']
            self.logger.info(f"📋 Latest scrcpy version: {version}")
            
            # Determine platform and download URL
            download_result = self._get_platform_download_url(release_data)
            if not download_result[0] or not download_result[1]:
                self.logger.error("❌ No suitable download found for this platform")
                return None
                
            download_url, filename = download_result
            
            # Create .scrcpy directory
            self.scrcpy_dir.mkdir(exist_ok=True)
            
            # Download the archive
            archive_path = self.scrcpy_dir / filename
            self.logger.info(f"📥 Downloading {filename}...")
            
            self._download_file(download_url, archive_path)
            
            # Extract the archive
            self.logger.info(f"📦 Extracting {filename}...")
            extracted_path = self._extract_archive(archive_path)
            
            # Clean up archive
            archive_path.unlink()
            
            return extracted_path
            
        except Exception as e:
            self.logger.error(f"❌ Failed to download scrcpy: {e}")
            return None
    
    def _get_platform_download_url(self, release_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """Get appropriate download URL for current platform"""
        system_name = platform.system().lower()
        architecture = platform.machine().lower()
        
        # Platform mapping
        platform_patterns = {
            'windows': {
                'patterns': ['win64', 'windows'],
                'extensions': ['.zip']
            },
            'linux': {
                'patterns': ['linux'],
                'extensions': ['.tar.gz']
            },
            'darwin': {  # macOS
                'patterns': ['macos', 'darwin'],
                'extensions': ['.zip']
            }
        }
        
        if system_name not in platform_patterns:
            self.logger.error(f"❌ Unsupported platform: {system_name}")
            return None, None
            
        platform_info = platform_patterns[system_name]
        
        # Search for matching asset
        for asset in release_data['assets']:
            asset_name = asset['name'].lower()
            
            # Check if asset matches platform
            platform_match = any(pattern in asset_name for pattern in platform_info['patterns'])
            extension_match = any(asset_name.endswith(ext) for ext in platform_info['extensions'])
            
            if platform_match and extension_match:
                self.logger.info(f"📦 Found matching asset: {asset['name']}")
                return asset['browser_download_url'], asset['name']
        
        self.logger.error(f"❌ No matching asset found for {system_name}")
        return None, None
    
    def _download_file(self, url: str, output_path: Path) -> None:
        """Download file with progress indication"""
        try:
            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, (block_num * block_size * 100) // total_size)
                    if block_num % 50 == 0 or percent >= 100:  # Update every ~50 blocks
                        self.logger.info(f"📥 Download progress: {percent}%")
            
            urllib.request.urlretrieve(url, output_path, progress_hook)
            self.logger.info(f"✅ Download completed: {output_path.name}")
            
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error downloading {url}: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to download {url}: {e}")
    
    def _extract_archive(self, archive_path: Path) -> Optional[Path]:
        """Extract archive and return path to scrcpy executable"""
        extract_dir = None
        try:
            extract_dir = self.scrcpy_dir / 'extracted'
            extract_dir.mkdir(exist_ok=True)
            
            # Extract based on file extension
            if archive_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif archive_path.name.endswith('.tar.gz'):
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)
            else:
                raise ValueError(f"Unsupported archive format: {archive_path.suffix}")
            
            # Find scrcpy executable in extracted files
            system_name = platform.system().lower()
            executable_name = 'scrcpy.exe' if system_name == 'windows' else 'scrcpy'
            
            # Search for executable recursively
            for exe_path in extract_dir.rglob(executable_name):
                if exe_path.is_file():
                    # Move executable to .scrcpy root
                    final_path = self.scrcpy_dir / executable_name
                    shutil.move(str(exe_path), str(final_path))
                    
                    # Copy any required DLLs (Windows)
                    if system_name == 'windows':
                        exe_dir = exe_path.parent
                        for dll_file in exe_dir.glob('*.dll'):
                            shutil.copy2(dll_file, self.scrcpy_dir)
                    
                    # Clean up extracted directory
                    shutil.rmtree(extract_dir, ignore_errors=True)
                    
                    # Make executable on Unix systems
                    if system_name != 'windows':
                        final_path.chmod(0o755)
                    
                    self.logger.info(f"✅ Installed scrcpy to: {final_path}")
                    return final_path
            
            raise FileNotFoundError(f"scrcpy executable not found in {archive_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to extract {archive_path}: {e}")
            # Clean up on failure
            if extract_dir is not None:
                shutil.rmtree(extract_dir, ignore_errors=True)
            return None
    
    def get_version(self) -> Optional[str]:
        """Get scrcpy version"""
        if not self.scrcpy_path:
            return None
            
        try:
            result = subprocess.run(
                [str(self.scrcpy_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Extract version from output
                version_line = result.stdout.strip().split('\n')[0]
                return version_line.split()[-1] if version_line else None
                
        except Exception as e:
            self.logger.debug(f"Failed to get scrcpy version: {e}")
            
        return None
    
    def is_available(self) -> bool:
        """Check if scrcpy is available and working"""
        return self.scrcpy_path is not None and self.scrcpy_path.exists()


class FutureProofScrcpy:
    """Python 3.13-3.15 compatible scrcpy integration using ScrcpyManager"""
    
    def __init__(self, scrcpy_manager: Optional[ScrcpyManager] = None, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.scrcpy_manager = scrcpy_manager or ScrcpyManager(logger=self.logger)
        self.process: Optional[subprocess.Popen] = None
        self._async_process: Optional[asyncio.subprocess.Process] = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        
    @property
    def scrcpy_path(self) -> Optional[Path]:
        """Get scrcpy executable path"""
        return self.scrcpy_manager.scrcpy_path
        
    async def start_async(self, device_id: str, **kwargs) -> Optional[asyncio.subprocess.Process]:
        """Async Version - nutzt moderne Python Features"""
        if not self.scrcpy_path:
            raise RuntimeError("scrcpy not found or failed to install")
            
        cmd = self._build_command(device_id, **kwargs)
        
        try:
            # Use asyncio.create_subprocess_exec for modern async handling
            self._async_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.logger.info(f'Started scrcpy async for device {device_id}')
            return self._async_process
            
        except Exception as e:
            self.logger.error(f'Failed to start scrcpy async: {e}')
            return None
    
    def start_sync(self, device_id: str, **kwargs) -> Optional[subprocess.Popen]:
        """Sync Version - klassisch stabil"""
        if not self.scrcpy_path:
            self.logger.error("scrcpy not found")
            return None
            
        cmd = self._build_command(device_id, **kwargs)
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            self.logger.info(f'Started scrcpy sync for device {device_id}')
            return self.process
            
        except Exception as e:
            self.logger.error(f'Failed to start scrcpy sync: {e}')
            return None
    
    def _build_command(self, device_id: str, **kwargs) -> list[str]:
        """Build scrcpy command with options"""
        cmd = [str(self.scrcpy_path)]
        
        # Device selection
        cmd.extend(['-s', device_id])
        
        # Apply common options with defaults
        options = {
            'no_control': kwargs.get('no_control', False),
            'window_title': kwargs.get('window_title', f'RR Bot {device_id}'),
            'window_width': kwargs.get('window_width', 800),
            'window_height': kwargs.get('window_height', 450),
            'max_size': kwargs.get('max_size', 1024),
            'bit_rate': kwargs.get('bit_rate', '2M'),
            'stay_awake': kwargs.get('stay_awake', True),
            'turn_screen_off': kwargs.get('turn_screen_off', False)
        }
        
        # Add options to command
        if options['no_control']:
            cmd.append('--no-control')
            
        if options['window_title']:
            cmd.extend(['--window-title', str(options['window_title'])])
            
        if options['window_width']:
            cmd.extend(['--window-width', str(options['window_width'])])
            
        if options['window_height']:
            cmd.extend(['--window-height', str(options['window_height'])])
            
        if options['max_size']:
            cmd.extend(['--max-size', str(options['max_size'])])
            
        if options['bit_rate']:
            cmd.extend(['--bit-rate', str(options['bit_rate'])])
            
        if options['stay_awake']:
            cmd.append('--stay-awake')
            
        if options['turn_screen_off']:
            cmd.append('--turn-screen-off')
        
        return cmd
    
    def stop(self):
        """Stop scrcpy process safely"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                self.logger.info('Stopped scrcpy process')
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.logger.warning('Force killed scrcpy process')
            except Exception as e:
                self.logger.error(f'Error stopping scrcpy: {e}')
            finally:
                self.process = None
                
        if self._async_process:
            try:
                self._async_process.terminate()
                # Note: async process cleanup would need await
                self.logger.info('Terminated async scrcpy process')
            except Exception as e:
                self.logger.error(f'Error stopping async scrcpy: {e}')
            finally:
                self._async_process = None
    
    def is_running(self) -> bool:
        """Check if scrcpy process is running"""
        if self.process:
            return self.process.poll() is None
        if self._async_process:
            return self._async_process.returncode is None
        return False
    
    def get_version(self) -> Optional[str]:
        """Get scrcpy version through manager"""
        return self.scrcpy_manager.get_version()
    
    def is_available(self) -> bool:
        """Check if scrcpy is available through manager"""
        return self.scrcpy_manager.is_available()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        if self._executor:
            self._executor.shutdown(wait=True)


class ModernScreenCapture:
    """Future-proof screen capture with multiple fallback methods"""
    
    def __init__(self, device_id: str, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.device_id = device_id
        
    async def via_adb_async(self, output_path: Path) -> bool:
        """Async ADB screencap - modern Python approach"""
        try:
            cmd = ['adb', '-s', self.device_id, 'exec-out', 'screencap', '-p']
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and len(stdout) > 1000:
                output_path.write_bytes(stdout)
                self.logger.debug(f'Async screenshot captured: {len(stdout)} bytes')
                return True
            else:
                self.logger.debug(f'Async screencap failed: {stderr.decode()}')
                
        except Exception as e:
            self.logger.debug(f'Async ADB screencap error: {e}')
            
        return False
    
    def via_adb_sync(self, output_path: Path) -> bool:
        """Sync ADB screencap - traditional stable method"""
        try:
            # Method 1: Direct exec-out (fastest)
            cmd = ['adb', '-s', self.device_id, 'exec-out', 'screencap', '-p']
            
            with output_path.open('wb') as f:
                result = subprocess.run(
                    cmd, 
                    stdout=f, 
                    stderr=subprocess.PIPE, 
                    timeout=10
                )
                
            if result.returncode == 0 and output_path.stat().st_size > 1000:
                self.logger.debug('Sync screenshot captured via exec-out')
                return True
                
            # Method 2: Traditional pull method (more compatible)
            self.logger.debug('Trying traditional ADB pull method')
            
            # Capture to device
            subprocess.run([
                'adb', '-s', self.device_id, 'shell', 
                'screencap', '-p', '/sdcard/bot_screenshot.png'
            ], timeout=5, check=False)
            
            time.sleep(0.2)
            
            # Pull from device
            result = subprocess.run([
                'adb', '-s', self.device_id, 'pull', 
                '/sdcard/bot_screenshot.png', str(output_path)
            ], capture_output=True, timeout=10)
            
            if result.returncode == 0 and output_path.exists():
                self.logger.debug('Sync screenshot captured via pull')
                return True
                
        except subprocess.TimeoutExpired:
            self.logger.warning('ADB screencap timeout')
        except FileNotFoundError:
            self.logger.warning('ADB not found in PATH')
        except Exception as e:
            self.logger.debug(f'Sync ADB screencap error: {e}')
            
        return False
    
    def via_fallback_method(self, output_path: Path) -> bool:
        """Additional fallback methods for screenshot capture"""
        # Could implement additional methods here:
        # - Direct device file read if rooted
        # - Alternative ADB commands
        # - Other screen capture tools
        return False


class FutureProofBot:
    """
    Modernized bot core using Python 3.13+ features with auto-downloading scrcpy
    Demonstrates future-proof architecture patterns
    """
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.logger = logging.getLogger(f'FutureBot_{device_id}')
        
        # Initialize scrcpy manager with auto-download
        self.logger.info("🚀 Initializing Future-Proof Bot with auto-scrcpy...")
        self.scrcpy_manager = ScrcpyManager(logger=self.logger)
        
        # Modern components
        self.scrcpy = FutureProofScrcpy(self.scrcpy_manager, self.logger)
        self.screen_capture = ModernScreenCapture(device_id, self.logger)
        
        # Async event loop for modern operations
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Log initialization status
        if self.scrcpy.is_available():
            version = self.scrcpy.get_version()
            self.logger.info(f"✅ Scrcpy ready! Version: {version or 'unknown'}")
        else:
            self.logger.warning("⚠️ Scrcpy not available, screenshot fallbacks will be used")
        
    async def start_async_operations(self):
        """Initialize async components"""
        self._loop = asyncio.get_running_loop()
        
        # Start scrcpy for visual monitoring if available
        if self.scrcpy.is_available():
            await self.scrcpy.start_async(
                self.device_id,
                no_control=True,
                window_title=f'RR Bot {self.device_id}'
            )
            self.logger.info("🎮 Scrcpy visual monitoring started")
        
    async def capture_screenshot_async(self, output_path: Union[str, Path]) -> bool:
        """Modern async screenshot capture"""
        output_path = Path(output_path)
        
        # Try async method first
        if await self.screen_capture.via_adb_async(output_path):
            return True
            
        # Fallback to sync method in thread pool
        if self._loop:
            return await self._loop.run_in_executor(
                None, 
                self.screen_capture.via_adb_sync, 
                output_path
            )
        
        return False
    
    def capture_screenshot_sync(self, output_path: Union[str, Path]) -> bool:
        """Traditional sync screenshot for compatibility"""
        return self.screen_capture.via_adb_sync(Path(output_path))
    
    def cleanup(self):
        """Clean shutdown of all components"""
        if self.scrcpy:
            self.scrcpy.stop()
            self.logger.info("🛑 Bot cleanup completed")


# Example usage demonstrating Python 3.13-3.15 compatibility with auto-download
async def modern_bot_example():
    """Example showing modern async bot usage with auto-scrcpy download"""
    print("🚀 Starting modern bot with auto-scrcpy management...")
    bot = FutureProofBot('emulator-5554')
    
    try:
        # Start async operations
        await bot.start_async_operations()
        
        # Capture screenshots using modern async methods
        screenshot_path = Path('modern_screenshot.png')
        success = await bot.capture_screenshot_async(screenshot_path)
        
        if success:
            print(f"📸 Screenshot captured: {screenshot_path}")
        else:
            print("❌ Screenshot failed")
            
    finally:
        bot.cleanup()


def sync_bot_example():
    """Example showing traditional sync usage with auto-scrcpy download"""
    print("⚙️ Starting sync bot with auto-scrcpy management...")
    bot = FutureProofBot('emulator-5554')
    
    try:
        # Use sync methods for traditional compatibility
        screenshot_path = Path('sync_screenshot.png')
        success = bot.capture_screenshot_sync(screenshot_path)
        
        if success:
            print(f"📸 Screenshot captured: {screenshot_path}")
        else:
            print("❌ Screenshot failed")
            
    finally:
        bot.cleanup()


def test_scrcpy_manager():
    """Test ScrcpyManager functionality"""
    print("🧪 Testing ScrcpyManager...")
    
    # Setup logging for testing
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Create manager
    manager = ScrcpyManager()
    
    print(f"📍 Scrcpy path: {manager.scrcpy_path}")
    print(f"✅ Available: {manager.is_available()}")
    
    if manager.is_available():
        version = manager.get_version()
        print(f"📋 Version: {version}")
    
    return manager.is_available()


if __name__ == "__main__":
    # Test scrcpy manager first
    print("=" * 60)
    print("🎯 SCRCPY MANAGER TEST")
    print("=" * 60)
    
    scrcpy_available = test_scrcpy_manager()
    
    if scrcpy_available:
        print("\n" + "=" * 60)
        print("🤖 BOT FUNCTIONALITY TEST")
        print("=" * 60)
        
        print("\n🔄 Testing sync approach...")
        sync_bot_example()
        
        print("\n🚀 Testing async approach...")
        asyncio.run(modern_bot_example())
        
        print("\n🎉 All tests completed!")
    else:
        print("\n⚠️ Scrcpy not available, skipping bot tests")
        print("Note: This could be due to network issues or unsupported platform")
