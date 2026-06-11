"""
RailGym — OpenAI Gymnasium Environment & PPO Dispatch Optimizer.
"""

import os
import logging
from typing import Tuple, Dict, Any

import numpy as np
import gymnasium as gym
from gymnasium import spaces

try:
    import mlflow
    import mlflow.pytorch

    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.callbacks import EvalCallback

    HAS_SB3 = True
except ImportError:
    HAS_SB3 = False

logger = logging.getLogger(__name__)


class RailGym(gym.Env):
    """
    RailGym: A Gymnasium environment for Indian Railways dispatch optimization.

    State space (observation):
        For each of the N_SECTIONS:
        - current train count (normalized)
        - average delay of trains in section (normalized, max 120 min)
        - section capacity utilization (0 to 1+)
        - time steps since last hold action (normalized)
        - passenger train count (normalized)
        - freight train count (normalized)
        - Kavach signaling active (binary)
        Total size: N_SECTIONS * 7

    Action space:
        Discrete choice per section:
        0 = PROCEED (nominal signal status)
        1 = HOLD_FREIGHT (give priority to passenger trains)
        2 = HOLD_ALL (extreme congestion control)
        3 = SPEED_RESTRICT (impose speed restriction due to track/weather)
        Total size: N_SECTIONS (multi-discrete)

    Reward:
        R = - (passenger_delay_minutes * 1.0)
            - (freight_delay_minutes * 0.3)
            - (safety_violations * 10000)
            + (disruption_resolved_bonus)
    """

    metadata = {"render_modes": ["human"], "render_fps": 4}

    N_SECTIONS = 8
    N_ACTIONS_PER_SECTION = 4

    def __init__(self, scenario: str = "normal", render_mode=None):
        super().__init__()
        self.scenario = scenario
        self.render_mode = render_mode

        # Observation space: 7 features per section
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(self.N_SECTIONS * 7,),
            dtype=np.float32,
        )

        # Action space: one discrete action (0-3) for each of the 8 sections
        self.action_space = spaces.MultiDiscrete([self.N_ACTIONS_PER_SECTION] * self.N_SECTIONS)

        self._state = None
        self._step_count = 0
        self._max_steps = 60  # 60 minutes per episode
        self.np_random = np.random.default_rng()

    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            self.np_random = np.random.default_rng(seed)

        self._step_count = 0
        self._state = self._generate_initial_state()
        return self._observe(), {}

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        self._step_count += 1

        # Apply agent decisions
        self._apply_actions(action)

        # Advance environment state by 1 step (1 minute)
        reward, info = self._advance_simulation()

        terminated = self._step_count >= self._max_steps
        truncated = False

        return self._observe(), reward, terminated, truncated, info

    def _observe(self) -> np.ndarray:
        obs = []
        for sec in self._state["sections"]:
            obs.extend(
                [
                    sec["train_count"] / 5.0,
                    min(sec["avg_delay"], 120.0) / 120.0,
                    sec["capacity_util"],
                    sec["last_hold_steps"] / 10.0,
                    sec["passenger_count"] / 4.0,
                    sec["freight_count"] / 3.0,
                    float(sec["kavach_active"]),
                ]
            )
        return np.array(obs, dtype=np.float32)

    def _generate_initial_state(self) -> Dict[str, Any]:
        scenarios = {
            "normal": {"base_delay": 5.0, "disruption_prob": 0.1},
            "moderate": {"base_delay": 20.0, "disruption_prob": 0.3},
            "severe": {"base_delay": 60.0, "disruption_prob": 0.6},
            "fog": {"base_delay": 30.0, "disruption_prob": 0.4, "weather": "FOG"},
        }
        cfg = scenarios.get(self.scenario, scenarios["normal"])

        sections = []
        for _ in range(self.N_SECTIONS):
            disrupted = self.np_random.random() < cfg["disruption_prob"]
            sections.append(
                {
                    "train_count": int(self.np_random.integers(1, 5)),
                    "avg_delay": float(
                        cfg["base_delay"] * (3 if disrupted else 1) + self.np_random.integers(0, 10)
                    ),
                    "capacity_util": float(self.np_random.uniform(0.3, 0.95 if disrupted else 0.7)),
                    "last_hold_steps": int(self.np_random.integers(0, 10)),
                    "passenger_count": int(self.np_random.integers(1, 4)),
                    "freight_count": int(self.np_random.integers(0, 3)),
                    "kavach_active": self.np_random.random() > 0.05,
                    "weather_visibility": 1.0
                    if cfg.get("weather") != "FOG"
                    else float(self.np_random.uniform(0.1, 0.5)),
                }
            )
        return {"sections": sections, "step": 0}

    def _apply_actions(self, action: np.ndarray):
        for i, act in enumerate(action):
            sec = self._state["sections"][i]
            if act == 1:  # HOLD_FREIGHT
                sec["freight_count"] = max(0, sec["freight_count"] - 1)
                sec["last_hold_steps"] = 0
            elif act == 2:  # HOLD_ALL
                sec["train_count"] = max(0, sec["train_count"] - 1)
                sec["last_hold_steps"] = 0
            elif act == 3:  # SPEED_RESTRICT
                sec["capacity_util"] = min(1.0, sec["capacity_util"] * 0.8)
            elif act == 0:  # PROCEED
                sec["last_hold_steps"] += 1

    def _advance_simulation(self) -> Tuple[float, Dict[str, Any]]:
        total_passenger_delay = 0.0
        total_freight_delay = 0.0
        safety_violations = 0

        for sec in self._state["sections"]:
            # Delays grow naturally under load/traffic
            delay_growth = 0.05 * sec["avg_delay"] if sec["capacity_util"] > 0.8 else -0.02
            sec["avg_delay"] = max(
                0.0, sec["avg_delay"] + delay_growth + float(self.np_random.normal(0, 2))
            )

            total_passenger_delay += sec["avg_delay"] * sec["passenger_count"]
            total_freight_delay += sec["avg_delay"] * sec["freight_count"]

            # Safety checks: overcrowding sections without safety systems (Kavach)
            if sec["capacity_util"] > 1.0 and not sec["kavach_active"]:
                safety_violations += 1

        # Objective reward calculation
        reward = (
            -total_passenger_delay * 1.0 - total_freight_delay * 0.3 - safety_violations * 10000.0
        )

        # Clear cascade bonus
        avg_delay = float(np.mean([s["avg_delay"] for s in self._state["sections"]]))
        if avg_delay < 10.0:
            reward += 500.0

        return reward, {
            "passenger_delay": total_passenger_delay,
            "freight_delay": total_freight_delay,
            "safety_violations": safety_violations,
            "avg_delay": avg_delay,
        }


def train_dispatch_agent(
    total_timesteps: int = 100000,
    model_path: str = "app/ml/artifacts/ppo_dispatch",
    n_envs: int = 4,
    n_steps: int = 2048,
):
    """
    Trains a stable-baselines3 PPO dispatch agent inside RailGym.
    """
    if not HAS_SB3:
        logger.warning("stable-baselines3 is not installed. Skipping training.")
        return None

    # Create artifacts directory
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    # Configure MLflow if available
    run_context = None
    if HAS_MLFLOW:
        try:
            mlflow.set_experiment("railgym-ppo-dispatch")
            run_context = mlflow.start_run(run_name="ppo-dispatch-train")
            mlflow.log_params(
                {
                    "algorithm": "PPO",
                    "policy": "MlpPolicy",
                    "total_timesteps": total_timesteps,
                    "net_arch": "256x256",
                }
            )
        except Exception as e:
            logger.warning(f"Could not initialize MLflow run: {e}")

    # Setup environments
    from stable_baselines3.common.vec_env import DummyVecEnv

    if n_envs == 1:
        train_env = DummyVecEnv([lambda: RailGym(scenario="moderate")])
    else:
        train_env = make_vec_env(lambda: RailGym(scenario="moderate"), n_envs=n_envs)
    eval_env = DummyVecEnv([lambda: RailGym(scenario="severe")])

    model = PPO(
        "MlpPolicy",
        train_env,
        learning_rate=3e-4,
        n_steps=n_steps,
        batch_size=min(64, n_steps * n_envs),
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        policy_kwargs={"net_arch": [256, 256]},
        verbose=1,
    )

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=os.path.dirname(model_path),
        log_path=os.path.dirname(model_path),
        eval_freq=10000,
        deterministic=True,
        render=False,
    )

    print(f"Starting reinforcement learning policy training for {total_timesteps} steps...")
    model.learn(total_timesteps=total_timesteps, callback=eval_callback, progress_bar=False)

    # Save policy
    model.save(model_path)
    print(f"Model saved successfully to {model_path}.zip")

    if HAS_MLFLOW and run_context:
        try:
            mlflow.log_metric("eval_mean_reward", float(eval_callback.last_mean_reward))
            mlflow.pytorch.log_model(model.policy, "ppo-dispatch-policy")
            mlflow.end_run()
        except Exception as e:
            logger.warning(f"Could not log metrics to MLflow: {e}")

    return model


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_dispatch_agent(total_timesteps=2000)
