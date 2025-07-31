#!/usr/bin/env python3
"""
Rush Royale Bot - Combat Module
Handles combat strategy, merging logic, and battle decisions
"""

import time
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional


class CombatStrategy:
    """Handles combat logic and unit management during battles"""
    
    def __init__(self, config: dict):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Strategy parameters
        self.merge_target = config.get('dps_unit', 'demon_hunter')
        if not self.merge_target.endswith('.png'):
            self.merge_target += '.png'
        
        self.require_shaman = config.get('require_shaman', False)
        self.mana_levels = config.get('mana_level', [1, 3, 5])
        
        self.logger.info(f"Combat strategy initialized - Target: {self.merge_target}")
    
    def execute_combat_round(self, bot, grid_df: pd.DataFrame, round_number: int) -> Dict:
        """Execute one combat round"""
        self.logger.debug(f"Executing combat round {round_number}")
        
        try:
            # 1. Upgrade units with mana
            self._upgrade_units(bot)
            
            # 2. Spawn new units
            self._spawn_units(bot)
            
            # 3. Merge units based on strategy
            merge_info = self._execute_merge_strategy(bot, grid_df)
            
            # 4. Analyze results
            combat_results = {
                'round': round_number,
                'merged_units': merge_info.get('merged_count', 0),
                'merge_target': merge_info.get('target_unit', 'none'),
                'grid_full': self._is_grid_full(grid_df),
                'demon_count': self._count_demons(grid_df)
            }
            
            self.logger.debug(f"Combat round completed: {combat_results}")
            return combat_results
            
        except Exception as e:
            self.logger.error(f"Combat round failed: {e}")
            return {'round': round_number, 'error': str(e)}
    
    def _upgrade_units(self, bot):
        """Upgrade units using mana"""
        upgrade_positions = {
            1: [100, 1500], 2: [200, 1500], 3: [350, 1500], 
            4: [500, 1500], 5: [650, 1500]
        }
        
        # Upgrade specified mana levels
        for level in self.mana_levels:
            if level in upgrade_positions:
                bot.click(*upgrade_positions[level])
        
        # Use hero power
        bot.click(800, 1500)
        
        time.sleep(0.2)
    
    def _spawn_units(self, bot):
        """Spawn new units"""
        bot.click(450, 1360)  # Spawn button
        time.sleep(0.2)
    
    def _execute_merge_strategy(self, bot, grid_df: pd.DataFrame) -> Dict:
        """Execute merging strategy based on current grid state"""
        try:
            # Analyze grid state
            unit_counts = self._get_unit_counts(grid_df)
            merge_candidates = self._find_merge_candidates(unit_counts)
            
            if not merge_candidates:
                return {'merged_count': 0, 'reason': 'no_candidates'}
            
            # Execute merges based on priority
            merged_count = 0
            
            # 1. Special merges (Harlequin, Dryad, etc.)
            special_merges = self._execute_special_merges(bot, grid_df, merge_candidates)
            merged_count += special_merges
            
            # 2. High priority merges
            priority_merges = self._execute_priority_merges(bot, grid_df, merge_candidates)
            merged_count += priority_merges
            
            # 3. General merges if grid is full
            if self._is_grid_full(grid_df):
                general_merges = self._execute_general_merges(bot, grid_df, merge_candidates)
                merged_count += general_merges
            
            return {
                'merged_count': merged_count,
                'target_unit': self.merge_target,
                'candidates': len(merge_candidates)
            }
            
        except Exception as e:
            self.logger.error(f"Merge strategy failed: {e}")
            return {'merged_count': 0, 'error': str(e)}
    
    def _get_unit_counts(self, grid_df: pd.DataFrame) -> pd.Series:
        """Get count of each unit type"""
        if grid_df.empty:
            return pd.Series()
        
        unit_counts = grid_df['unit'].value_counts()
        return unit_counts
    
    def _find_merge_candidates(self, unit_counts: pd.Series) -> List[str]:
        """Find units that can be merged (count >= 2)"""
        candidates = []
        
        for unit, count in unit_counts.items():
            if count >= 2 and unit != 'empty.png':
                candidates.append(unit)
        
        return candidates
    
    def _execute_special_merges(self, bot, grid_df: pd.DataFrame, candidates: List[str]) -> int:
        """Execute special unit merges (Harlequin, Dryad, etc.)"""
        merged = 0
        special_units = ['harlequin.png', 'dryad.png', 'mime.png', 'scrapper.png']
        
        for special_unit in special_units:
            if special_unit in candidates:
                merge_result = self._merge_special_unit(bot, grid_df, special_unit)
                if merge_result:
                    merged += 1
                    self.logger.info(f"Special merge: {special_unit}")
        
        return merged
    
    def _execute_priority_merges(self, bot, grid_df: pd.DataFrame, candidates: List[str]) -> int:
        """Execute high priority merges"""
        merged = 0
        priority_units = ['chemist.png', 'bombardier.png', 'summoner.png', 'knight_statue.png']
        
        for priority_unit in priority_units:
            if priority_unit in candidates:
                merge_result = self._merge_unit_type(bot, grid_df, priority_unit)
                if merge_result:
                    merged += 1
                    self.logger.info(f"Priority merge: {priority_unit}")
        
        return merged
    
    def _execute_general_merges(self, bot, grid_df: pd.DataFrame, candidates: List[str]) -> int:
        """Execute general merges when grid is full"""
        merged = 0
        
        # Filter out protected units
        protected_units = ['chemist.png', 'cauldron.png', self.merge_target]
        
        for unit in candidates:
            if unit not in protected_units:
                # Check if we have enough units to merge
                unit_count = len(grid_df[grid_df['unit'] == unit])
                if unit_count >= 2:
                    merge_result = self._merge_unit_type(bot, grid_df, unit)
                    if merge_result:
                        merged += 1
                        self.logger.debug(f"General merge: {unit}")
                        break  # Only merge one type per round
        
        return merged
    
    def _merge_special_unit(self, bot, grid_df: pd.DataFrame, special_unit: str) -> bool:
        """Merge special unit with appropriate target"""
        try:
            # Find special unit positions
            special_positions = grid_df[grid_df['unit'] == special_unit]['grid_pos'].tolist()
            
            if len(special_positions) < 1:
                return False
            
            # Find target unit for special merge
            target_unit = self._find_special_merge_target(grid_df, special_unit)
            if not target_unit:
                return False
            
            target_positions = grid_df[grid_df['unit'] == target_unit]['grid_pos'].tolist()
            
            if len(target_positions) < 1:
                return False
            
            # Execute merge
            special_pos = special_positions[0]
            target_pos = target_positions[0]
            
            bot.swipe(special_pos, target_pos)
            time.sleep(0.2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Special merge failed for {special_unit}: {e}")
            return False
    
    def _merge_unit_type(self, bot, grid_df: pd.DataFrame, unit_type: str) -> bool:
        """Merge two units of the same type"""
        try:
            # Find positions of this unit type
            unit_positions = grid_df[grid_df['unit'] == unit_type]['grid_pos'].tolist()
            
            if len(unit_positions) < 2:
                return False
            
            # Select two units to merge
            pos1, pos2 = unit_positions[:2]
            
            # Execute merge
            bot.swipe(pos1, pos2)
            time.sleep(0.2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Unit merge failed for {unit_type}: {e}")
            return False
    
    def _find_special_merge_target(self, grid_df: pd.DataFrame, special_unit: str) -> Optional[str]:
        """Find appropriate target for special unit merge"""
        target_preferences = {
            'harlequin.png': [self.merge_target, 'knight_statue.png'],
            'dryad.png': ['zealot.png', 'crystal.png'],
            'mime.png': [self.merge_target],
            'scrapper.png': ['bombardier.png', 'summoner.png']
        }
        
        preferences = target_preferences.get(special_unit, [])
        
        for preferred_target in preferences:
            if preferred_target in grid_df['unit'].values:
                return preferred_target
        
        return None
    
    def _is_grid_full(self, grid_df: pd.DataFrame) -> bool:
        """Check if grid is nearly full"""
        if grid_df.empty:
            return False
        
        empty_slots = len(grid_df[grid_df['unit'] == 'empty.png'])
        return empty_slots <= 2
    
    def _count_demons(self, grid_df: pd.DataFrame) -> int:
        """Count demon hunter units on grid"""
        if grid_df.empty:
            return 0
        
        return len(grid_df[grid_df['unit'] == 'demon_hunter.png'])
    
    def should_continue_combat(self, grid_df: pd.DataFrame, round_number: int) -> bool:
        """Determine if combat should continue"""
        # Check for demon saturation
        demon_count = self._count_demons(grid_df)
        if demon_count >= 11:
            self.logger.info("Board saturated with demons, pausing combat")
            return False
        
        # Check for shaman requirement
        if self.require_shaman:
            # This would check for shaman opponent
            # Implementation depends on screen analysis
            pass
        
        return True
    
    def get_combat_statistics(self, grid_df: pd.DataFrame) -> Dict:
        """Get current combat statistics"""
        stats = {
            'total_units': len(grid_df[grid_df['unit'] != 'empty.png']),
            'empty_slots': len(grid_df[grid_df['unit'] == 'empty.png']),
            'demon_count': self._count_demons(grid_df),
            'unit_distribution': dict(grid_df['unit'].value_counts())
        }
        
        return stats


class MergeOptimizer:
    """Advanced merge optimization algorithms"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def optimize_merge_sequence(self, grid_df: pd.DataFrame, target_unit: str) -> List[Tuple]:
        """Calculate optimal merge sequence for target unit"""
        # Implementation would use graph algorithms to find optimal paths
        # This is a placeholder for the advanced optimization logic
        pass
    
    def calculate_board_value(self, grid_df: pd.DataFrame) -> float:
        """Calculate overall board value for optimization"""
        # Implementation would score board state based on unit values and positions
        pass


# Utility functions
def preserve_unit(unit_series: pd.Series, target: str = 'chemist.png', keep_min: bool = False) -> pd.Series:
    """Remove one unit of target type from merge candidates"""
    if target in unit_series.index:
        if keep_min:
            # Keep at least one
            if unit_series[target] > 1:
                unit_series[target] -= 1
        else:
            # Remove highest rank
            unit_series[target] = max(0, unit_series[target] - 1)
    
    return unit_series


def filter_units_by_criteria(unit_series: pd.Series, units: List[str] = None, 
                           ranks: List[int] = None, remove: bool = False) -> pd.Series:
    """Filter units based on type and rank criteria"""
    filtered = unit_series.copy()
    
    if units:
        unit_mask = filtered.index.isin(units)
        if remove:
            filtered = filtered[~unit_mask]
        else:
            filtered = filtered[unit_mask]
    
    # Rank filtering would be implemented here
    # This requires rank information in the series index
    
    return filtered
