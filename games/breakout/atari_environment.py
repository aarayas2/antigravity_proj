import gymnasium as gym
import ale_py

import numpy as np

gym.register_envs(ale_py)

class FireResetEnv(gym.Wrapper):
    """Automatically presses FIRE to start the game."""
    def __init__(self, env):
        super().__init__(env)
        assert env.unwrapped.get_action_meanings()[1] == 'FIRE'

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        # Force the FIRE action (Action 1) to spawn the ball
        obs, _, terminated, truncated, info = self.env.step(1)
        if terminated or truncated:
            obs, info = self.env.reset(**kwargs)
        return obs, info

def make_atari_env(env_id, render_mode=None):
    """Builds the environment with the standard DeepMind pipeline."""
    env = gym.make(env_id, render_mode=render_mode, frameskip=1)
    
    # 1. Automate the FIRE button
    env = FireResetEnv(env)
    
    # 2. Apply standard DeepMind processing (Skip frames, resize to 84x84, grayscale, fear of death)
    env = gym.wrappers.AtariPreprocessing(
        env,
        noop_max=30,                   # Anti-memorization trick
        frame_skip=4,                  # Speeds up training 4x
        screen_size=84,                # Shrinks frame to 84x84
        terminal_on_life_loss=True,    # Dying now counts as Game Over
        grayscale_obs=True,            # Removes color
        scale_obs=True                 # Converts pixel values from 0-255 to 0.0-1.0 automatically
    )
    
    # 3. Stack the 4 most recent frames together so the AI can perceive motion
    env = gym.wrappers.FrameStackObservation(env, stack_size=4)
    
    return env
    