#!/usr/bin/env python3
"""
Rush Royale Bot - Command Line Interface
Simple CLI for bot operations
"""

import argparse
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from core.bot import RushRoyaleBot
from core.config import ConfigManager
from modules.automation import AutomationEngine
from modules.debug import get_debug_system


class BotCLI:
    """Command Line Interface for Rush Royale Bot"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Bot components
        self.bot: Optional[RushRoyaleBot] = None
        self.automation: Optional[AutomationEngine] = None
        self.config_manager = ConfigManager()
        
        # CLI state
        self.running = False
        
        self.logger.info("CLI initialized")
    
    def setup(self):
        """Set up bot components"""
        try:
            self.bot = RushRoyaleBot()
            self.automation = AutomationEngine(self.bot)
            
            print("✓ Bot components initialized")
            return True
            
        except Exception as e:
            print(f"✗ Setup failed: {e}")
            self.logger.error(f"Setup error: {e}")
            return False
    
    def connect_device(self) -> bool:
        """Connect to Android device"""
        try:
            print("Connecting to device...")
            
            if not self.bot:
                print("✗ Bot not initialized")
                return False
            
            success = self.bot.connect_device()
            
            if success:
                device_info = self.bot.get_device_info()
                print(f"✓ Connected to: {device_info.get('model', 'Unknown device')}")
                return True
            else:
                print("✗ Failed to connect to device")
                return False
                
        except Exception as e:
            print(f"✗ Connection error: {e}")
            self.logger.error(f"Device connection error: {e}")
            return False
    
    def run_single_battle(self, chapter: int = 1, battle_type: str = "pve") -> bool:
        """Run a single battle"""
        try:
            if not self.bot or not self.bot.is_connected():
                print("✗ Device not connected")
                return False
            
            print(f"Starting {battle_type} battle (Chapter {chapter})...")
            
            # Start battle
            success = self.bot.start_pve_battle(chapter=chapter, timeout=300)
            
            if success:
                print("✓ Battle started, waiting for completion...")
                
                # Wait for battle completion
                battle_result = self.bot.wait_for_battle_completion(timeout=300)
                
                if battle_result:
                    print("✓ Battle completed successfully")
                    
                    # Collect rewards
                    rewards = self.bot.collect_battle_rewards()
                    if rewards:
                        print("✓ Rewards collected")
                    
                    return True
                else:
                    print("✗ Battle failed or timed out")
                    return False
            else:
                print("✗ Failed to start battle")
                return False
                
        except Exception as e:
            print(f"✗ Battle error: {e}")
            self.logger.error(f"Single battle error: {e}")
            return False
    
    def run_automation(self, chapter: int = 1, max_battles: int = 10, 
                      battle_type: str = "pve") -> bool:
        """Run automation with specified parameters"""
        try:
            if not self.automation:
                print("✗ Automation not initialized")
                return False
            
            if not self.bot or not self.bot.is_connected():
                print("✗ Device not connected")
                return False
            
            print(f"Starting automation: {max_battles} battles (Chapter {chapter})")
            
            # Configure automation
            session_config = {
                'battle_type': battle_type,
                'chapter': chapter
            }
            
            automation_settings = {
                'max_battles_per_session': max_battles,
                'battle_timeout': 300,
                'auto_collect_rewards': True,
                'energy_management': True
            }
            
            self.automation.update_settings(automation_settings)
            
            # Start automation
            tasks = ['pve_farming', 'reward_collection', 'energy_management']
            self.automation.start_automation(tasks=tasks, session_config=session_config)
            
            print("✓ Automation started")
            
            # Monitor automation
            self._monitor_automation()
            
            return True
            
        except Exception as e:
            print(f"✗ Automation error: {e}")
            self.logger.error(f"Automation error: {e}")
            return False
    
    def _monitor_automation(self):
        """Monitor automation progress"""
        try:
            print("\nMonitoring automation (Press Ctrl+C to stop)...")
            print("=" * 50)
            
            last_battles = 0
            
            while self.automation.running:
                try:
                    # Get status
                    status = self.automation.get_automation_status()
                    
                    battles_completed = status.get('battles_completed', 0)
                    battles_failed = status.get('battles_failed', 0)
                    current_task = status.get('current_task', 'None')
                    
                    # Show progress if battles increased
                    if battles_completed > last_battles:
                        total_battles = battles_completed + battles_failed
                        if total_battles > 0:
                            success_rate = (battles_completed / total_battles) * 100
                        else:
                            success_rate = 0
                        
                        print(f"Progress: {battles_completed} battles completed "
                              f"({battles_failed} failed) - Success: {success_rate:.1f}%")
                        
                        last_battles = battles_completed
                    
                    # Show current task
                    if current_task and current_task != 'None':
                        print(f"Current task: {current_task}")
                    
                    time.sleep(5.0)
                    
                except KeyboardInterrupt:
                    print("\n\nStopping automation...")
                    self.automation.stop_automation()
                    break
                except Exception as e:
                    self.logger.debug(f"Monitor error: {e}")
                    time.sleep(5.0)
            
            # Final report
            print("\nAutomation completed!")
            self._show_final_report()
            
        except Exception as e:
            print(f"✗ Monitoring error: {e}")
            self.logger.error(f"Monitoring error: {e}")
    
    def _show_final_report(self):
        """Show final automation report"""
        try:
            if not self.automation:
                return
            
            report = self.automation.get_performance_report()
            
            print("=" * 50)
            print("AUTOMATION REPORT")
            print("=" * 50)
            
            successful = report.get('successful_battles', 0)
            failed = report.get('failed_battles', 0)
            total = successful + failed
            
            if total > 0:
                success_rate = (successful / total) * 100
                print(f"Total Battles: {total}")
                print(f"Successful: {successful}")
                print(f"Failed: {failed}")
                print(f"Success Rate: {success_rate:.1f}%")
                
                avg_duration = report.get('average_battle_duration', 0)
                if avg_duration > 0:
                    print(f"Average Battle Time: {avg_duration:.1f}s")
                
                efficiency = report.get('efficiency_score', 0)
                print(f"Efficiency Score: {efficiency:.1f}%")
            else:
                print("No battles completed")
            
            print("=" * 50)
            
        except Exception as e:
            print(f"Report error: {e}")
            self.logger.debug(f"Report error: {e}")
    
    def get_device_info(self):
        """Show device information"""
        try:
            if not self.bot or not self.bot.is_connected():
                print("✗ Device not connected")
                return
            
            device_info = self.bot.get_device_info()
            
            print("\nDevice Information:")
            print("=" * 30)
            for key, value in device_info.items():
                print(f"{key.capitalize()}: {value}")
            print("=" * 30)
            
        except Exception as e:
            print(f"✗ Device info error: {e}")
            self.logger.error(f"Device info error: {e}")
    
    def test_screenshot(self):
        """Test screenshot functionality"""
        try:
            if not self.bot or not self.bot.is_connected():
                print("✗ Device not connected")
                return False
            
            print("Taking screenshot...")
            
            screenshot = self.bot.get_screenshot()
            
            if screenshot is not None:
                # Save screenshot
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"test_screenshot_{timestamp}.png"
                
                import cv2
                success = cv2.imwrite(filename, screenshot)
                
                if success:
                    print(f"✓ Screenshot saved: {filename}")
                    print(f"✓ Image size: {screenshot.shape}")
                    return True
                else:
                    print("✗ Failed to save screenshot")
                    return False
            else:
                print("✗ Failed to capture screenshot")
                return False
                
        except Exception as e:
            print(f"✗ Screenshot test error: {e}")
            self.logger.error(f"Screenshot test error: {e}")
            return False
    
    def run_diagnostics(self):
        """Run system diagnostics"""
        try:
            print("Running diagnostics...")
            print("=" * 40)
            
            # Check bot initialization
            if self.bot:
                print("✓ Bot initialized")
            else:
                print("✗ Bot not initialized")
                return
            
            # Check device connection
            if self.bot.is_connected():
                print("✓ Device connected")
                self.get_device_info()
            else:
                print("✗ Device not connected")
                return
            
            # Test screenshot
            print("\nTesting screenshot...")
            if self.test_screenshot():
                print("✓ Screenshot test passed")
            else:
                print("✗ Screenshot test failed")
            
            # Test automation components
            if self.automation:
                print("✓ Automation system available")
                
                # Get automation info
                status = self.automation.get_automation_status()
                print(f"✓ Automation status: {status.get('running', False)}")
            else:
                print("✗ Automation not initialized")
            
            print("=" * 40)
            print("Diagnostics completed")
            
        except Exception as e:
            print(f"✗ Diagnostics error: {e}")
            self.logger.error(f"Diagnostics error: {e}")
    
    def enable_debug(self):
        """Enable debug mode"""
        try:
            debug_system = get_debug_system()
            debug_system.enable()
            print("✓ Debug mode enabled")
            
        except Exception as e:
            print(f"✗ Debug enable error: {e}")
            self.logger.error(f"Debug enable error: {e}")
    
    def show_help(self):
        """Show help information"""
        help_text = """
Rush Royale Bot CLI Commands:
============================

Basic Operations:
  connect         - Connect to Android device
  battle          - Run single battle
  auto            - Run automation mode
  info            - Show device information
  screenshot      - Test screenshot functionality
  diagnostics     - Run system diagnostics

Options for battle/auto:
  --chapter N     - Select chapter (1-5, default: 1)
  --type TYPE     - Battle type (pve/pvp, default: pve)
  --count N       - Number of battles for automation (default: 10)

Debug:
  --debug         - Enable debug mode
  --verbose       - Enable verbose logging

Examples:
  python -m interface.cli connect
  python -m interface.cli battle --chapter 3
  python -m interface.cli auto --chapter 2 --count 20
  python -m interface.cli diagnostics --debug
        """
        print(help_text)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Rush Royale Bot CLI")
    
    # Commands
    parser.add_argument('command', nargs='?', choices=[
        'connect', 'battle', 'auto', 'info', 'screenshot', 
        'diagnostics', 'help'
    ], default='help', help='Command to execute')
    
    # Options
    parser.add_argument('--chapter', type=int, default=1, choices=[1, 2, 3, 4, 5],
                       help='Chapter selection (1-5)')
    parser.add_argument('--type', default='pve', choices=['pve', 'pvp'],
                       help='Battle type')
    parser.add_argument('--count', type=int, default=10,
                       help='Number of battles for automation')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create CLI instance
    cli = BotCLI()
    
    # Enable debug if requested
    if args.debug:
        cli.enable_debug()
    
    # Execute command
    try:
        if args.command == 'help':
            cli.show_help()
            
        elif args.command == 'connect':
            if cli.setup():
                cli.connect_device()
                
        elif args.command == 'battle':
            if cli.setup() and cli.connect_device():
                cli.run_single_battle(chapter=args.chapter, battle_type=args.type)
                
        elif args.command == 'auto':
            if cli.setup() and cli.connect_device():
                cli.run_automation(chapter=args.chapter, max_battles=args.count, 
                                 battle_type=args.type)
                
        elif args.command == 'info':
            if cli.setup() and cli.connect_device():
                cli.get_device_info()
                
        elif args.command == 'screenshot':
            if cli.setup() and cli.connect_device():
                cli.test_screenshot()
                
        elif args.command == 'diagnostics':
            if cli.setup():
                cli.run_diagnostics()
                
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
