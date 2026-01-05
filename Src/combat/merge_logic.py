"""
Rush Royale Bot - Merge Logic Module
Python 3.13 Compatible

Provides unit merging strategies:
- Basic unit merging
- Special unit handling (Dryad, Harlequin, Mime)
- Merge target prioritization
"""
from __future__ import annotations

import time
import logging
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..adb_controller import ADBController
    from ..vision.grid_analysis import GridAnalyzer

# Import grid utilities
try:
    from ..utils.grid_utils import (
        get_grid,
        adv_filter_keys,
        preserve_unit,
        grid_meta_info,
    )
except ImportError:
    from Src.utils.grid_utils import (
        get_grid,
        adv_filter_keys,
        preserve_unit,
        grid_meta_info,
    )


class MergeController:
    """
    Controls unit merging logic.
    
    Handles:
    - Basic merge operations
    - Special unit merging (Dryad, Harlequin)
    - Merge target prioritization
    - Board state management
    """
    
    def __init__(
        self,
        adb: 'ADBController',
        grid_analyzer: 'GridAnalyzer',
        logger: logging.Logger | None = None
    ):
        """
        Initialize merge controller.
        
        Args:
            adb: ADB controller for swipe actions
            grid_analyzer: Grid analyzer for board state
            logger: Optional logger instance
        """
        self.adb = adb
        self.grid = grid_analyzer
        self.logger = logger or logging.getLogger(__name__)
    
    def swipe_merge(
        self,
        start: tuple[int, int],
        end: tuple[int, int]
    ) -> None:
        """
        Swipe to merge units on grid.
        
        Args:
            start: Start grid position (row, col)
            end: End grid position (row, col)
        """
        boxes, _ = get_grid()
        self.adb.swipe_grid(start, end, boxes)
        time.sleep(0.2)
    
    def merge_unit(
        self,
        df_split: pd.core.groupby.DataFrameGroupBy,
        merge_series: pd.Series
    ) -> pd.DataFrame | None:
        """
        Merge two random units from series.
        
        Args:
            df_split: Grouped grid dataframe
            merge_series: Series of mergeable units
            
        Returns:
            Merged units dataframe or None
        """
        if len(merge_series) == 0:
            return None
        
        # Pick random target
        merge_target = merge_series.sample().index[0]
        merge_df = df_split.get_group(merge_target)
        
        if len(merge_df) < 2:
            return None
        
        merge_df = merge_df.sample(n=2)
        self._log_merge(merge_df)
        
        # Execute merge
        unit_positions = merge_df['grid_pos'].tolist()
        self.swipe_merge(*unit_positions)
        
        return merge_df
    
    def merge_special_unit(
        self,
        df_split: pd.core.groupby.DataFrameGroupBy,
        merge_series: pd.Series,
        special_type: str
    ) -> pd.DataFrame | None:
        """
        Merge special units (Harlequin, Dryad, etc).
        
        Args:
            df_split: Grouped grid dataframe
            merge_series: Series of units
            special_type: Special unit type to merge
            
        Returns:
            Merged units dataframe or None
        """
        # Get special and normal units
        special_unit = adv_filter_keys(merge_series, units=special_type, remove=False)
        normal_unit = adv_filter_keys(merge_series, units=special_type, remove=True)
        
        if special_unit.empty or normal_unit.empty:
            return None
        
        # Get dataframes
        special_df = df_split.get_group(special_unit.index[0]).sample()
        normal_df = df_split.get_group(normal_unit.index[0]).sample()
        
        merge_df = pd.concat([special_df, normal_df])
        self._log_merge(merge_df)
        
        # Execute merge
        unit_positions = merge_df['grid_pos'].tolist()
        self.swipe_merge(*unit_positions)
        
        return merge_df
    
    def special_merge(
        self,
        df_split: pd.core.groupby.DataFrameGroupBy,
        merge_series: pd.Series,
        target: str = 'zealot.png'
    ) -> pd.DataFrame | None:
        """
        Handle Dryad/Harlequin special merging.
        
        Args:
            df_split: Grouped grid dataframe
            merge_series: Series of units
            target: Target unit for Dryad
            
        Returns:
            Merged units dataframe or None
        """
        # Try to rank up dryads
        dryads_series = adv_filter_keys(merge_series, units='dryad.png')
        
        if dryads_series.empty:
            return None
        
        dryads_ranks = dryads_series.index.get_level_values('rank')
        
        for rank in dryads_ranks:
            # Try Harlequin + Dryad
            merge_hq = adv_filter_keys(
                merge_series,
                units=['harlequin.png', 'dryad.png'],
                ranks=rank
            )
            if len(merge_hq.index) == 2:
                return self.merge_special_unit(df_split, merge_hq, 'harlequin.png')
            
            # Try Dryad + target
            merge_target = adv_filter_keys(
                merge_series,
                units=['dryad.png', target],
                ranks=rank
            )
            if len(merge_target.index) == 2:
                return self.merge_special_unit(df_split, merge_target, 'dryad.png')
        
        return None
    
    def harley_merge(
        self,
        df_split: pd.core.groupby.DataFrameGroupBy,
        merge_series: pd.Series,
        target: str = 'knight_statue.png'
    ) -> pd.DataFrame | None:
        """
        Use Harlequin to copy target unit.
        
        Args:
            df_split: Grouped grid dataframe
            merge_series: Series of units
            target: Unit to copy
            
        Returns:
            Merged units dataframe or None
        """
        hq_series = adv_filter_keys(merge_series, units='harlequin.png')
        
        if hq_series.empty:
            return None
        
        hq_ranks = hq_series.index.get_level_values('rank')
        
        for rank in hq_ranks:
            merge_target = adv_filter_keys(
                merge_series,
                units=['harlequin.png', target],
                ranks=rank
            )
            if len(merge_target.index) == 2:
                return self.merge_special_unit(df_split, merge_target, 'harlequin.png')
        
        return None
    
    def _log_merge(self, merge_df: pd.DataFrame) -> None:
        """Log merge operation with appropriate level."""
        df_copy = merge_df.copy()
        df_copy['unit'] = df_copy['unit'].apply(lambda x: x.replace('.png', ''))
        
        unit1, unit2 = df_copy.iloc[0:2]['unit'].values
        rank = df_copy.iloc[0]['rank']
        
        log_msg = f"Rank {rank} {unit1} -> {unit2}"
        
        if rank > 4:
            self.logger.error(log_msg)  # High rank = risky
        elif rank > 2:
            self.logger.debug(log_msg)
        else:
            self.logger.info(log_msg)
    
    def try_merge(
        self,
        rank: int = 1,
        prev_grid: pd.DataFrame | None = None,
        merge_target: str = 'zealot.png',
        config: 'ConfigParser | None' = None
    ) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame | None, str]:
        """
        Attempt to find and execute a merge.
        
        Args:
            rank: Minimum rank to merge
            prev_grid: Previous grid state
            merge_target: Primary merge target unit
            config: Bot configuration
            
        Returns:
            Tuple of (grid_df, unit_series, merge_series, merge_df, info)
        """
        info = ''
        merge_df = None
        
        # Scan grid
        names = self.grid.scan_grid(refresh=False)
        
        # Import bot_perception for grid status
        try:
            from .. import bot_perception
        except ImportError:
            import bot_perception
        
        grid_df = bot_perception.grid_status(names, prev_grid=prev_grid)
        df_split, unit_series, df_groups, _ = grid_meta_info(grid_df)
        
        # Prepare merge series
        merge_series = unit_series.copy()
        merge_series = adv_filter_keys(merge_series, units='empty.png', remove=True)
        
        # Special merges
        self.special_merge(df_split, merge_series, merge_target)
        
        # Demon hunter handling
        if merge_target == 'demon_hunter.png':
            self.harley_merge(df_split, merge_series, target=merge_target)
            
            demons = adv_filter_keys(merge_series, units='demon_hunter.png')
            if sum(demons) >= 11:
                self.logger.info('Board is full of demons, waiting...')
                time.sleep(10)
            
            if config and config.getboolean('bot', 'require_shaman', fallback=False):
                merge_series = adv_filter_keys(
                    merge_series, units='demon_hunter.png', remove=True
                )
        
        # Preserve key units
        merge_series = preserve_unit(merge_series, target='chemist.png')
        
        # Keep 4 cauldrons
        for _ in range(4):
            merge_series = preserve_unit(merge_series, target='cauldron.png', keep_min=True)
        
        # Keep knight statues balanced
        num_knight = sum(adv_filter_keys(merge_series, units='knight_statue.png'))
        if num_knight % 2 == 1:
            self.harley_merge(df_split, merge_series, target='knight_statue.png')
        
        for _ in range(2):
            merge_series = preserve_unit(merge_series, target='knight_statue.png')
        
        # Filter mergeable units
        merge_series = merge_series[merge_series >= 2]
        merge_series = adv_filter_keys(merge_series, ranks=7, remove=True)
        
        # Priority merging
        merge_prio = adv_filter_keys(
            merge_series,
            units=['chemist.png', 'bombardier.png', 'summoner.png', 'knight_statue.png']
        )
        
        if not merge_prio.empty:
            info = 'Merging High Priority!'
            merge_df = self.merge_unit(df_split, merge_prio)
        
        # Merge when board is full
        elif df_groups.get('empty.png', 0) <= 2:
            low_series = adv_filter_keys(merge_series, ranks=rank, remove=False)
            
            if not low_series.empty:
                info = 'Merging!'
                merge_df = self.merge_unit(df_split, low_series)
            else:
                info = 'Merging high level!'
                high_merge = adv_filter_keys(
                    merge_series,
                    ranks=[3, 4, 5, 6, 7],
                    units=['zealot.png', 'crystal.png', 'bruser.png', merge_target],
                    remove=True
                )
                if not high_merge.empty:
                    merge_df = self.merge_unit(df_split, high_merge)
        else:
            info = 'need more units!'
        
        return grid_df, unit_series, merge_series, merge_df, info
