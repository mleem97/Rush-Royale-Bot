"""
Rush Royale Bot - Grid Utilities Module
Python 3.13 Compatible

Provides utility functions for:
- Grid coordinate calculations
- Unit counting and filtering
- Series manipulation for merge logic
"""
from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    pass


# Grid configuration constants
GRID_TOP_BOX = (153, 945)
GRID_BOX_SIZE = (120, 120)
GRID_GAP = 0
GRID_HEIGHT = 3
GRID_WIDTH = 5


def get_grid() -> tuple[np.ndarray, tuple[int, int]]:
    """
    Get fight grid pixel coordinates.
    
    Returns:
        Tuple of (boxes array [3x5x2], box_size tuple)
    """
    x_coords = list(range(
        GRID_TOP_BOX[0],
        GRID_TOP_BOX[0] + (GRID_BOX_SIZE[0] + GRID_GAP) * GRID_WIDTH,
        GRID_BOX_SIZE[0] + GRID_GAP
    ))
    y_coords = list(range(
        GRID_TOP_BOX[1],
        GRID_TOP_BOX[1] + (GRID_BOX_SIZE[1] + GRID_GAP) * GRID_HEIGHT,
        GRID_BOX_SIZE[1] + GRID_GAP
    ))
    
    boxes = []
    for y_point in y_coords:
        for x_point in x_coords:
            boxes.append((x_point, y_point))
    
    # Convert to numpy array (3x5) with x,y coords
    boxes = np.array(boxes).reshape(GRID_HEIGHT, GRID_WIDTH, 2)
    return boxes, GRID_BOX_SIZE


def get_unit_count(grid_df: pd.DataFrame) -> tuple[
    pd.core.groupby.DataFrameGroupBy,
    pd.Series,
    list[str]
]:
    """
    Count units by type from grid dataframe.
    
    Args:
        grid_df: DataFrame with 'unit' column
        
    Returns:
        Tuple of (grouped df, count series, unit list)
    """
    df_split = grid_df.groupby("unit")
    df_groups = df_split["unit"].count()
    
    if 'empty.png' not in df_groups:
        df_groups['empty.png'] = 0
    
    unit_list = list(df_groups.index)
    return df_split, df_groups, unit_list


def preserve_unit(
    unit_series: pd.Series,
    target: str = 'chemist.png',
    keep_min: bool = False
) -> pd.Series:
    """
    Remove 1x of the highest/lowest rank unit from the series.
    
    Used to preserve high-value units from being merged.
    
    Args:
        unit_series: Pandas series of units indexed by (unit, rank)
        target: Target unit to keep
        keep_min: If True, keep lowest rank instead of highest
        
    Returns:
        Modified series with one target unit removed
    """
    merge_series = unit_series.copy()
    preserve_series = adv_filter_keys(merge_series, units=target, remove=False)
    
    if not preserve_series.empty:
        if keep_min:
            preserve_unit_idx = preserve_series.index.min()
        else:
            preserve_unit_idx = preserve_series.index.max()
        
        # Remove 1 count of highest/lowest rank
        mask = merge_series.index == preserve_unit_idx
        merge_series.loc[mask] = merge_series.loc[mask] - 1
        
        # Remove 0 counts
        return merge_series[merge_series > 0]
    
    return merge_series


def grid_meta_info(
    grid_df: pd.DataFrame,
    min_age: int = 0
) -> tuple[
    pd.core.groupby.DataFrameGroupBy,
    pd.Series,
    pd.Series,
    list[tuple[str, int]]
]:
    """
    Split grid df into unique units and ranks.
    
    Shows total count of unit and count of each rank.
    
    Args:
        grid_df: Grid dataframe with unit, rank, Age columns
        min_age: Minimum age of unit to include
        
    Returns:
        Tuple of (grouped df, unit series, group counts, group keys)
    """
    df_groups = get_unit_count(grid_df)[1]
    
    # Filter by age
    grid_df = grid_df[grid_df['Age'] >= min_age].reset_index(drop=True)
    
    # Group by unit and rank
    df_split = grid_df.groupby(['unit', 'rank'])
    unit_series = df_split['unit'].count()
    group_keys = list(unit_series.index)
    
    return df_split, unit_series, df_groups, group_keys


def filter_units(
    unit_series: pd.Series,
    units: str | int | list[str | int]
) -> pd.Series:
    """
    Filter unit series by unit names or ranks.
    
    Args:
        unit_series: Series indexed by (unit, rank)
        units: Unit name(s) or rank(s) to filter by
        
    Returns:
        Filtered series
    """
    if not isinstance(units, list):
        units = [units]
    
    series_list = []
    merge_series = unit_series.copy()
    
    for token in units:
        if isinstance(token, int):
            # Filter by rank
            exists = merge_series.index.get_level_values('rank').isin([token]).any()
            if exists:
                series_list.append(
                    merge_series.xs(token, level='rank', drop_level=False)
                )
        elif isinstance(token, str):
            # Filter by unit name
            if token in merge_series.index.get_level_values('unit'):
                series_list.append(
                    merge_series.xs(token, level='unit', drop_level=False)
                )
    
    if series_list:
        temp_series = pd.concat(series_list)
        merge_series = merge_series[merge_series.index.isin(temp_series.index)]
        return merge_series
    
    return pd.Series(dtype=object)


def adv_filter_keys(
    unit_series: pd.Series,
    units: str | list[str] | None = None,
    ranks: int | list[int] | None = None,
    remove: bool = False
) -> pd.Series:
    """
    Advanced filtering of unit series by units and/or ranks.
    
    Args:
        unit_series: Series indexed by (unit, rank)
        units: Unit name(s) to filter by (None = all)
        ranks: Rank(s) to filter by (None = all)
        remove: If True, remove matches; if False, keep only matches
        
    Returns:
        Filtered series
    """
    if unit_series.empty:
        return pd.Series(dtype=object)
    
    # Filter by units first
    if units is not None:
        filtered_units = filter_units(unit_series, units)
    else:
        filtered_units = unit_series.copy()
    
    # Then filter by ranks
    if ranks is not None and not filtered_units.empty:
        filtered_ranks = filter_units(filtered_units, ranks)
    else:
        filtered_ranks = filtered_units.copy()
    
    # Apply remove logic
    series = unit_series.copy()
    if remove:
        series = series[~series.index.isin(filtered_ranks.index)]
    else:
        series = series[series.index.isin(filtered_ranks.index)]
    
    return series


def get_button_pos(df: pd.DataFrame, button: str) -> np.ndarray:
    """
    Get button position from icon dataframe.
    
    Args:
        df: DataFrame with 'icon' and 'pos [X,Y]' columns
        button: Button icon name (e.g., 'refresh_button.png')
        
    Returns:
        Position as numpy array [x, y]
    """
    pos = df[df['icon'] == button]['pos [X,Y]'].reset_index(drop=True)[0]
    return np.array(pos)


def read_knowledge(bot: 'Bot', clicks: int = 1000) -> None:
    """
    Spam click to read knowledge base entries for free gold.
    
    Roughly yields 3k gold, 100 gems.
    
    Args:
        bot: Bot instance with click method
        clicks: Number of clicks to perform
    """
    for _ in range(clicks):
        bot.click(450, 1300, 0.1)
