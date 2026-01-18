"""Rush Royale Bot - Reinforcement Learning Environment.

Gymnasium-compatible environment for training RL agents.
Wraps the bot's perception and action systems.

Usage:
    from bot_env import RushRoyaleEnv
    from stable_baselines3 import PPO

    env = RushRoyaleEnv(bot_instance)
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=10000)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces

    GYM_AVAILABLE = True
except ImportError:
    # Fallback for older gym
    try:
        import gym
        from gym import spaces

        GYM_AVAILABLE = True
    except ImportError:
        GYM_AVAILABLE = False
        gym = None
        spaces = None


# Unit type encoding for observation space
UNIT_ENCODING = {
    "empty.png": 0,
    "demon_hunter.png": 1,
    "dryad.png": 2,
    "harlequin.png": 3,
    "chemist.png": 4,
    "knight_statue.png": 5,
    "shaman.png": 6,
    "bombardier.png": 7,
    "engineer.png": 8,
    "frost.png": 9,
    "meteor.png": 10,
    "vampire.png": 11,
    "witch.png": 12,
    # Add more as needed
}

# Action space:
# 0-59: Merge actions (15 positions * 4 directions)
# 60: Summon new unit
# 61-65: Upgrade mana levels 1-5
# 66: Do nothing (wait)
ACTION_MERGE_START = 0
ACTION_MERGE_END = 59
ACTION_SUMMON = 60
ACTION_UPGRADE_1 = 61
ACTION_UPGRADE_5 = 65
ACTION_WAIT = 66


class RushRoyaleEnv:
    """Gymnasium-compatible environment for Rush Royale bot.

    Observation Space:
        - 15 grid cells, each with (unit_type, rank) = shape (15, 2)
        - unit_type: 0-20 (encoded unit names)
        - rank: 0-7

    Action Space:
        - 0-59: Merge (position * 4 + direction)
        - 60: Summon
        - 61-65: Upgrade mana 1-5
        - 66: Wait

    Reward:
        - +1 per step survived
        - +10 for high rank unit created (rank 5+)
        - +5 for successful merge
        - -100 for game over/lost
        - +100 for floor completion
    """

    def __init__(
        self,
        bot_instance: Any,
        max_steps: int = 1000,
        step_delay: float = 0.5,
    ):
        if not GYM_AVAILABLE:
            raise ImportError("gymnasium or gym required. Install with: pip install gymnasium")

        self.bot = bot_instance
        self.max_steps = max_steps
        self.step_delay = step_delay
        self.current_step = 0
        self.logger = logging.getLogger(__name__)

        # Gymnasium spaces
        self.action_space = spaces.Discrete(67)  # 60 merges + summon + 5 upgrades + wait
        self.observation_space = spaces.Box(
            low=0,
            high=20,
            shape=(15, 2),
            dtype=np.int32,
        )

        # State tracking
        self._last_grid_df = None
        self._last_combat = 0
        self._episode_reward = 0

    def reset(
        self,
        seed: int | None = None,
        options: dict | None = None,
    ) -> tuple[np.ndarray, dict]:
        """Reset environment for new episode."""
        self.current_step = 0
        self._episode_reward = 0
        self._last_combat = 0

        # Wait for game to be in fighting state
        self._wait_for_combat()

        # Get initial observation
        observation = self._get_observation()

        return observation, {"combat": self._last_combat}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        """Execute action and return (observation, reward, terminated, truncated, info)."""
        self.current_step += 1
        reward = 0.0
        terminated = False
        truncated = False
        info = {}

        # Execute action
        action_success = self._execute_action(action)
        if action_success:
            reward += 0.5  # Small reward for valid action

        # Wait for game state to update
        time.sleep(self.step_delay)

        # Get new observation
        observation = self._get_observation()

        # Calculate reward based on game state
        reward += self._calculate_reward()

        # Check termination conditions
        if self._is_game_over():
            terminated = True
            reward -= 100  # Penalty for losing
        elif self._is_floor_complete():
            terminated = True
            reward += 100  # Bonus for winning

        # Check truncation (max steps)
        if self.current_step >= self.max_steps:
            truncated = True

        self._episode_reward += reward

        info = {
            "step": self.current_step,
            "combat": self._last_combat,
            "episode_reward": self._episode_reward,
            "action_success": action_success,
        }

        return observation, reward, terminated, truncated, info

    def _execute_action(self, action: int) -> bool:
        """Execute the given action on the bot."""
        try:
            if ACTION_MERGE_START <= action <= ACTION_MERGE_END:
                # Merge action: decode position and direction
                pos = action // 4
                direction = action % 4

                # Convert position to grid coordinates
                row, col = pos // 5, pos % 5

                # Direction: 0=up, 1=down, 2=left, 3=right
                target_row, target_col = row, col
                if direction == 0 and row > 0:
                    target_row = row - 1
                elif direction == 1 and row < 2:
                    target_row = row + 1
                elif direction == 2 and col > 0:
                    target_col = col - 1
                elif direction == 3 and col < 4:
                    target_col = col + 1
                else:
                    return False  # Invalid move

                # Execute swipe
                self.bot.swipe([row, col], [target_row, target_col])
                return True

            elif action == ACTION_SUMMON:
                # Summon new unit
                self.bot.click(450, 1360)
                return True

            elif ACTION_UPGRADE_1 <= action <= ACTION_UPGRADE_5:
                # Upgrade mana level
                level = action - ACTION_UPGRADE_1 + 1
                self.bot.mana_level(level)
                return True

            elif action == ACTION_WAIT:
                # Do nothing
                return True

            return False

        except Exception as e:
            self.logger.debug(f"Action {action} failed: {e}")
            return False

    def _get_observation(self) -> np.ndarray:
        """Get current game state as observation array."""
        try:
            # Scan grid
            names = self.bot.scan_grid(new=True)
            import bot_perception

            grid_df = bot_perception.grid_status(names, self._last_grid_df)
            self._last_grid_df = grid_df

            # Convert to observation array
            observation = np.zeros((15, 2), dtype=np.int32)

            for idx, row in grid_df.iterrows():
                unit_name = row["unit"]
                rank = row.get("rank", 0)

                # Encode unit type
                unit_code = UNIT_ENCODING.get(unit_name, 0)

                observation[idx, 0] = unit_code
                observation[idx, 1] = min(rank, 7)

            return observation

        except Exception as e:
            self.logger.warning(f"Failed to get observation: {e}")
            return np.zeros((15, 2), dtype=np.int32)

    def _calculate_reward(self) -> float:
        """Calculate reward based on current game state."""
        reward = 1.0  # Base survival reward

        if self._last_grid_df is not None:
            df = self._last_grid_df

            # Reward for high rank units
            high_ranks = df[df["rank"] >= 5]
            reward += len(high_ranks) * 2

            # Reward for demon hunters (DPS)
            dh_count = len(df[df["unit"] == "demon_hunter.png"])
            reward += dh_count * 0.5

            # Track combat progress
            if hasattr(self.bot, "combat") and self.bot.combat > self._last_combat:
                reward += 5  # Bonus for surviving waves
                self._last_combat = self.bot.combat

        return reward

    def _is_game_over(self) -> bool:
        """Check if game is over (lost)."""
        if hasattr(self.bot, "output"):
            return self.bot.output in ["lost", "home"]
        return False

    def _is_floor_complete(self) -> bool:
        """Check if dungeon floor is complete."""
        if hasattr(self.bot, "output"):
            return self.bot.output == "victory"
        return False

    def _wait_for_combat(self, timeout: float = 30.0):
        """Wait for game to enter combat state."""
        start = time.time()
        while time.time() - start < timeout:
            if hasattr(self.bot, "output") and self.bot.output == "fighting":
                return True
            time.sleep(0.5)
        return False

    def render(self, mode: str = "human"):
        """Render current state (optional)."""
        if self._last_grid_df is not None:
            print(f"\n=== Step {self.current_step} ===")
            print(self._last_grid_df[["unit", "rank"]].to_string())

    def close(self):
        """Cleanup environment."""
        pass


# =============================================================================
# Imitation Learning Data Collector
# =============================================================================


class ImitationDataCollector:
    """Collect state-action pairs from rule-based bot for imitation learning.

    Watches the bot's decisions and records them for supervised learning.
    """

    def __init__(self, save_dir: str = "imitation_data"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.data: list[dict] = []
        self.logger = logging.getLogger(__name__)

    def record(
        self, grid_df: Any, action: int, action_type: str, details: dict | None = None
    ):
        """Record a state-action pair."""
        if grid_df is None:
            return

        # Encode state
        state = []
        for _idx, row in grid_df.iterrows():
            unit_code = UNIT_ENCODING.get(row["unit"], 0)
            rank = row.get("rank", 0)
            state.append([unit_code, rank])

        record = {
            "state": state,
            "action": action,
            "action_type": action_type,
            "details": details or {},
            "timestamp": time.time(),
        }
        self.data.append(record)

    def save(self, filename: str = "imitation_data.npz"):
        """Save collected data to file."""
        if not self.data:
            self.logger.warning("No data to save")
            return

        states = np.array([d["state"] for d in self.data])
        actions = np.array([d["action"] for d in self.data])

        path = self.save_dir / filename
        np.savez(path, states=states, actions=actions)
        self.logger.info(f"Saved {len(self.data)} samples to {path}")

    def load(self, filename: str = "imitation_data.npz") -> tuple[np.ndarray, np.ndarray]:
        """Load collected data from file."""
        path = self.save_dir / filename
        data = np.load(path)
        return data["states"], data["actions"]

    def clear(self):
        """Clear collected data."""
        self.data = []


def encode_merge_action(start_pos: list, end_pos: list) -> int:
    """Encode a merge (swipe) action to action space integer."""
    start_idx = start_pos[0] * 5 + start_pos[1]

    # Determine direction
    if end_pos[0] < start_pos[0]:
        direction = 0  # up
    elif end_pos[0] > start_pos[0]:
        direction = 1  # down
    elif end_pos[1] < start_pos[1]:
        direction = 2  # left
    else:
        direction = 3  # right

    return start_idx * 4 + direction


def decode_merge_action(action: int) -> tuple[list, list]:
    """Decode action space integer to grid positions."""
    pos = action // 4
    direction = action % 4

    row, col = pos // 5, pos % 5
    start = [row, col]

    if direction == 0:
        end = [row - 1, col]
    elif direction == 1:
        end = [row + 1, col]
    elif direction == 2:
        end = [row, col - 1]
    else:
        end = [row, col + 1]

    return start, end
