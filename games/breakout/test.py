import gymnasium as gym
import time
import ale_py

gym.register_envs(ale_py)

def main():
    import os
    os.environ["SDL_AUDIODRIVER"] = "dummy"  # Disable sound for the Pygame renderer

    # ALE/Breakout-v5 is the standard Atari environment in Gymnasium
    env = gym.make('ALE/Breakout-v5', render_mode="human")
    observation, info = env.reset()

    print("Breakout environment started!")

    # Run a simple loop to demonstrate stepping through the environment
    try:
        for _ in range(1000):
            # Your Neural Network would go here to decide 'action'
            # For Breakout, actions typically are: 0=NOOP, 1=FIRE, 2=RIGHT, 3=LEFT
            action = env.action_space.sample()  # Choosing a random action for testing
            
            observation, reward, terminated, truncated, info = env.step(action)
            
            if terminated or truncated:
                observation, info = env.reset()
                
            time.sleep(0.01) # Slow down a bit to see the rendering
            
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        env.close()

if __name__ == "__main__":
    main()
