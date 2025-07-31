#!/usr/bin/env python3
"""
Rush Royale Bot - Automation Module
High-level automation workflows and battle management
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd


@dataclass
class AutomationTask:
    """Automation task definition"""
    name: str
    description: str
    enabled: bool = True
    priority: int = 1
    max_retries: int = 3
    timeout: float = 300.0
    last_run: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0


@dataclass
class BattleSession:
    """Battle session tracking"""
    session_id: str
    start_time: datetime
    battle_type: str = "pve"
    chapter: int = 1
    battles_completed: int = 0
    battles_failed: int = 0
    total_duration: float = 0.0
    average_battle_time: float = 0.0
    last_battle_result: Optional[str] = None
    active: bool = True


class AutomationEngine:
    """High-level automation engine for Rush Royale Bot"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.logger = logging.getLogger(__name__)
        
        # Automation state
        self.running = False
        self.paused = False
        self.current_task = None
        self.task_queue = []
        
        # Session tracking
        self.current_session: Optional[BattleSession] = None
        self.session_history = []
        
        # Automation tasks
        self.available_tasks = {}
        self.task_handlers = {}
        
        # Settings
        self.default_settings = {
            'max_battles_per_session': 50,
            'max_session_duration': 3600,  # 1 hour
            'battle_timeout': 300,  # 5 minutes
            'retry_failed_battles': True,
            'auto_collect_rewards': True,
            'energy_management': True,
            'adaptive_timing': True
        }
        
        self.settings = self.default_settings.copy()
        
        # Performance tracking
        self.performance_metrics = {
            'total_runtime': 0.0,
            'successful_battles': 0,
            'failed_battles': 0,
            'average_battle_duration': 0.0,
            'efficiency_score': 0.0
        }
        
        # Initialize automation tasks
        self._initialize_tasks()
        
        self.logger.info("Automation engine initialized")
    
    def _initialize_tasks(self):
        """Initialize available automation tasks"""
        
        # PvE Farming Task
        pve_farming = AutomationTask(
            name="pve_farming",
            description="Automated PvE dungeon farming",
            priority=1,
            timeout=self.settings['battle_timeout']
        )
        
        # Reward Collection Task
        reward_collection = AutomationTask(
            name="reward_collection",
            description="Collect available rewards and quest items",
            priority=3,
            timeout=30.0
        )
        
        # Energy Management Task
        energy_management = AutomationTask(
            name="energy_management",
            description="Monitor and manage energy levels",
            priority=2,
            timeout=60.0
        )
        
        # Store Management Task
        store_management = AutomationTask(
            name="store_management",
            description="Check and manage store items",
            priority=4,
            timeout=120.0
        )
        
        # Add tasks to registry
        self.available_tasks = {
            "pve_farming": pve_farming,
            "reward_collection": reward_collection,
            "energy_management": energy_management,
            "store_management": store_management
        }
        
        # Register task handlers
        self.task_handlers = {
            "pve_farming": self._handle_pve_farming,
            "reward_collection": self._handle_reward_collection,
            "energy_management": self._handle_energy_management,
            "store_management": self._handle_store_management
        }
    
    def start_automation(self, tasks: List[str] = None, session_config: Dict = None):
        """Start automation with specified tasks"""
        try:
            if self.running:
                self.logger.warning("Automation already running")
                return False
            
            # Set up session
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            session_config = session_config or {}
            battle_type = session_config.get('battle_type', 'pve')
            chapter = session_config.get('chapter', 1)
            
            self.current_session = BattleSession(
                session_id=session_id,
                start_time=datetime.now(),
                battle_type=battle_type,
                chapter=chapter
            )
            
            # Set up task queue
            if tasks is None:
                tasks = ["pve_farming", "reward_collection", "energy_management"]
            
            self.task_queue = [self.available_tasks[task] for task in tasks 
                              if task in self.available_tasks]
            
            # Start automation loop
            self.running = True
            self.paused = False
            
            self.logger.info(f"Starting automation session: {session_id}")
            self.logger.info(f"Queued tasks: {[t.name for t in self.task_queue]}")
            
            # Run automation loop
            self._automation_loop()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start automation: {e}")
            return False
    
    def stop_automation(self):
        """Stop automation gracefully"""
        try:
            if not self.running:
                self.logger.info("Automation not running")
                return
            
            self.running = False
            
            # Finalize current session
            if self.current_session and self.current_session.active:
                self.current_session.active = False
                self.current_session.total_duration = (
                    datetime.now() - self.current_session.start_time
                ).total_seconds()
                
                self.session_history.append(self.current_session)
            
            self.logger.info("Automation stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping automation: {e}")
    
    def pause_automation(self):
        """Pause automation"""
        self.paused = True
        self.logger.info("Automation paused")
    
    def resume_automation(self):
        """Resume automation"""
        self.paused = False
        self.logger.info("Automation resumed")
    
    def _automation_loop(self):
        """Main automation loop"""
        try:
            loop_start = time.time()
            
            while self.running:
                # Check pause state
                while self.paused and self.running:
                    time.sleep(1.0)
                
                if not self.running:
                    break
                
                # Check session limits
                if self._should_end_session():
                    self.logger.info("Session limits reached, stopping automation")
                    break
                
                # Process task queue
                if self.task_queue:
                    self._process_next_task()
                else:
                    # No tasks in queue, wait or add default tasks
                    self._replenish_task_queue()
                
                # Brief pause between task cycles
                time.sleep(2.0)
            
            # Update performance metrics
            self.performance_metrics['total_runtime'] += time.time() - loop_start
            
        except Exception as e:
            self.logger.error(f"Automation loop error: {e}")
        finally:
            self.running = False
    
    def _process_next_task(self):
        """Process the next task in queue"""
        try:
            if not self.task_queue:
                return
            
            # Get next task (priority-based)
            self.task_queue.sort(key=lambda t: t.priority)
            task = self.task_queue.pop(0)
            
            if not task.enabled:
                self.logger.debug(f"Task {task.name} is disabled, skipping")
                return
            
            self.current_task = task
            self.logger.info(f"Processing task: {task.name}")
            
            # Execute task with timeout
            success = self._execute_task_with_timeout(task)
            
            # Update task statistics
            task.last_run = datetime.now()
            if success:
                task.success_count += 1
            else:
                task.failure_count += 1
            
            self.current_task = None
            
        except Exception as e:
            self.logger.error(f"Task processing error: {e}")
    
    def _execute_task_with_timeout(self, task: AutomationTask) -> bool:
        """Execute task with timeout protection"""
        try:
            if task.name not in self.task_handlers:
                self.logger.error(f"No handler for task: {task.name}")
                return False
            
            handler = self.task_handlers[task.name]
            start_time = time.time()
            
            # Execute task handler
            success = handler(task)
            
            duration = time.time() - start_time
            self.logger.debug(f"Task {task.name} completed in {duration:.2f}s (success: {success})")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Task execution error for {task.name}: {e}")
            return False
    
    def _handle_pve_farming(self, task: AutomationTask) -> bool:
        """Handle PvE farming task"""
        try:
            if not self.current_session:
                return False
            
            # Check if we can start a battle
            if not self._can_start_battle():
                self.logger.info("Cannot start battle (energy/limits)")
                return True  # Not a failure, just skip
            
            # Start battle
            battle_start = time.time()
            success = self.bot.start_pve_battle(
                chapter=self.current_session.chapter,
                timeout=task.timeout
            )
            
            if success:
                # Wait for battle to complete
                battle_success = self.bot.wait_for_battle_completion(timeout=task.timeout)
                
                battle_duration = time.time() - battle_start
                
                if battle_success:
                    self.current_session.battles_completed += 1
                    self.current_session.last_battle_result = "success"
                    self.performance_metrics['successful_battles'] += 1
                    
                    # Update average battle time
                    self._update_average_battle_time(battle_duration)
                    
                    self.logger.info(f"Battle completed successfully in {battle_duration:.1f}s")
                else:
                    self.current_session.battles_failed += 1
                    self.current_session.last_battle_result = "failed"
                    self.performance_metrics['failed_battles'] += 1
                    
                    self.logger.warning("Battle failed or timed out")
                
                # Collect any rewards
                if self.settings['auto_collect_rewards']:
                    self.bot.collect_battle_rewards()
                
                return battle_success
            else:
                self.logger.warning("Failed to start battle")
                return False
                
        except Exception as e:
            self.logger.error(f"PvE farming error: {e}")
            return False
    
    def _handle_reward_collection(self, task: AutomationTask) -> bool:
        """Handle reward collection task"""
        try:
            collected = self.bot.collect_all_rewards()
            
            if collected:
                self.logger.info("Rewards collected successfully")
            else:
                self.logger.debug("No rewards to collect")
            
            return True  # Always successful (not finding rewards is not a failure)
            
        except Exception as e:
            self.logger.error(f"Reward collection error: {e}")
            return False
    
    def _handle_energy_management(self, task: AutomationTask) -> bool:
        """Handle energy management task"""
        try:
            if not self.settings['energy_management']:
                return True
            
            # Check current energy level
            energy_info = self.bot.get_energy_status()
            
            if energy_info and energy_info.get('current', 0) < 20:
                self.logger.info("Low energy detected, managing...")
                
                # Try to collect energy from sources
                energy_collected = self.bot.collect_energy_sources()
                
                if energy_collected:
                    self.logger.info("Energy collected from sources")
                else:
                    self.logger.info("No energy sources available")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Energy management error: {e}")
            return False
    
    def _handle_store_management(self, task: AutomationTask) -> bool:
        """Handle store management task"""
        try:
            # Check store for free items or important purchases
            store_items = self.bot.check_store_offers()
            
            if store_items:
                # Handle free items or strategic purchases
                purchases_made = self.bot.handle_store_purchases(store_items)
                
                if purchases_made:
                    self.logger.info(f"Made {purchases_made} store purchases")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Store management error: {e}")
            return False
    
    def _can_start_battle(self) -> bool:
        """Check if we can start a new battle"""
        try:
            if not self.current_session:
                return False
            
            # Check session limits
            if self.current_session.battles_completed >= self.settings['max_battles_per_session']:
                return False
            
            # Check energy (if energy management is enabled)
            if self.settings['energy_management']:
                energy_info = self.bot.get_energy_status()
                if energy_info and energy_info.get('current', 0) < 10:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Battle check error: {e}")
            return False
    
    def _should_end_session(self) -> bool:
        """Check if current session should end"""
        try:
            if not self.current_session:
                return True
            
            # Check battle count limit
            if self.current_session.battles_completed >= self.settings['max_battles_per_session']:
                return True
            
            # Check time limit
            session_duration = (datetime.now() - self.current_session.start_time).total_seconds()
            if session_duration >= self.settings['max_session_duration']:
                return True
            
            # Check failure rate
            total_battles = self.current_session.battles_completed + self.current_session.battles_failed
            if total_battles > 5:  # Only check after several battles
                failure_rate = self.current_session.battles_failed / total_battles
                if failure_rate > 0.5:  # More than 50% failure rate
                    self.logger.warning("High failure rate detected, ending session")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Session check error: {e}")
            return True
    
    def _replenish_task_queue(self):
        """Add default tasks back to queue"""
        try:
            # Add essential tasks back to queue
            essential_tasks = ["pve_farming"]
            
            if self.settings['auto_collect_rewards']:
                essential_tasks.append("reward_collection")
            
            if self.settings['energy_management']:
                essential_tasks.append("energy_management")
            
            for task_name in essential_tasks:
                if task_name in self.available_tasks:
                    task = self.available_tasks[task_name]
                    if task.enabled:
                        self.task_queue.append(task)
            
        except Exception as e:
            self.logger.error(f"Task queue replenishment error: {e}")
    
    def _update_average_battle_time(self, battle_duration: float):
        """Update average battle time calculation"""
        try:
            if not self.current_session:
                return
            
            total_battles = self.current_session.battles_completed
            if total_battles == 1:
                self.current_session.average_battle_time = battle_duration
            else:
                # Running average
                current_avg = self.current_session.average_battle_time
                new_avg = ((current_avg * (total_battles - 1)) + battle_duration) / total_battles
                self.current_session.average_battle_time = new_avg
            
            # Update global performance metrics
            self.performance_metrics['average_battle_duration'] = self.current_session.average_battle_time
            
        except Exception as e:
            self.logger.debug(f"Average battle time update error: {e}")
    
    def get_automation_status(self) -> Dict[str, Any]:
        """Get current automation status"""
        try:
            status = {
                'running': self.running,
                'paused': self.paused,
                'current_task': self.current_task.name if self.current_task else None,
                'tasks_in_queue': len(self.task_queue),
                'session_active': self.current_session.active if self.current_session else False
            }
            
            if self.current_session:
                session_duration = (datetime.now() - self.current_session.start_time).total_seconds()
                status.update({
                    'session_id': self.current_session.session_id,
                    'session_duration': session_duration,
                    'battles_completed': self.current_session.battles_completed,
                    'battles_failed': self.current_session.battles_failed,
                    'average_battle_time': self.current_session.average_battle_time,
                    'last_battle_result': self.current_session.last_battle_result
                })
            
            return status
            
        except Exception as e:
            self.logger.error(f"Status retrieval error: {e}")
            return {'error': str(e)}
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance metrics and analysis"""
        try:
            # Calculate efficiency score
            total_battles = (self.performance_metrics['successful_battles'] + 
                           self.performance_metrics['failed_battles'])
            
            if total_battles > 0:
                success_rate = self.performance_metrics['successful_battles'] / total_battles
                avg_duration = self.performance_metrics['average_battle_duration']
                
                # Efficiency based on success rate and speed
                time_efficiency = max(0, 1 - (avg_duration - 120) / 300)  # Optimal ~2min battles
                efficiency = (success_rate * 0.7) + (time_efficiency * 0.3)
                
                self.performance_metrics['efficiency_score'] = efficiency * 100
            
            report = self.performance_metrics.copy()
            
            # Add session history summary
            if self.session_history:
                total_sessions = len(self.session_history)
                avg_battles_per_session = sum(s.battles_completed for s in self.session_history) / total_sessions
                avg_session_duration = sum(s.total_duration for s in self.session_history) / total_sessions
                
                report.update({
                    'total_sessions': total_sessions,
                    'average_battles_per_session': avg_battles_per_session,
                    'average_session_duration': avg_session_duration
                })
            
            return report
            
        except Exception as e:
            self.logger.error(f"Performance report error: {e}")
            return {'error': str(e)}
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """Update automation settings"""
        try:
            for key, value in new_settings.items():
                if key in self.settings:
                    self.settings[key] = value
                    self.logger.info(f"Updated setting {key} = {value}")
                else:
                    self.logger.warning(f"Unknown setting: {key}")
            
        except Exception as e:
            self.logger.error(f"Settings update error: {e}")
    
    def enable_task(self, task_name: str):
        """Enable specific automation task"""
        if task_name in self.available_tasks:
            self.available_tasks[task_name].enabled = True
            self.logger.info(f"Enabled task: {task_name}")
        else:
            self.logger.error(f"Unknown task: {task_name}")
    
    def disable_task(self, task_name: str):
        """Disable specific automation task"""
        if task_name in self.available_tasks:
            self.available_tasks[task_name].enabled = False
            self.logger.info(f"Disabled task: {task_name}")
        else:
            self.logger.error(f"Unknown task: {task_name}")
    
    def get_task_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all tasks"""
        try:
            stats = {}
            
            for task_name, task in self.available_tasks.items():
                total_runs = task.success_count + task.failure_count
                success_rate = (task.success_count / total_runs * 100) if total_runs > 0 else 0
                
                stats[task_name] = {
                    'enabled': task.enabled,
                    'priority': task.priority,
                    'total_runs': total_runs,
                    'success_count': task.success_count,
                    'failure_count': task.failure_count,
                    'success_rate': success_rate,
                    'last_run': task.last_run.isoformat() if task.last_run else None
                }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Task statistics error: {e}")
            return {}
