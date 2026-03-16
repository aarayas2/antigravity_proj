import torch
import torchvision.transforms as T
import numpy as np
import gymnasium as gym
import time
import ale_py
gym.register_envs(ale_py)

def preprocess_frame(frame, device):
    """
    Converts a 210x160x3 Atari frame into a 1x84x84 normalized tensor.
    """
    # 1. Convert numpy array to torch tensor and move to M1 GPU (mps)
    frame = torch.from_numpy(frame).to(device).to(torch.float32)
    
    # 2. Reorder from (H, W, C) to (C, H, W) for PyTorch
    frame = frame.permute(2, 0, 1)
    
    # 3. Define the transform pipeline
    transforms = T.Compose([
        T.Grayscale(),                # Convert to 1 channel
        T.CenterCrop((170, 160)),     # Remove top/bottom scores/margins
        T.Resize((84, 84)),           # Shrink to 84x84
        T.Normalize(0, 255)           # Scale pixels to 0-1 range
    ])
    
    return transforms(frame).unsqueeze(0) # Add batch dimension: (1, 1, 84, 84)

def main():
    # Set device to MPS (Apple Silicon), CUDA, or CPU
    if torch.backends.mps.is_available():
        device = torch.device('mps')
    elif torch.cuda.is_available():
        device = torch.device('cuda')
    else:
        device = torch.device('cpu')
    print(f"Using device: {device}")
    import os
    os.environ["SDL_AUDIODRIVER"] = "dummy"  # Disable sound for the Pygame renderer

    # ALE/Breakout-v5 is the standard Atari environment in Gymnasium
    env = gym.make('ALE/Breakout-v5', render_mode="human")
    observation, info = env.reset()

    print("Breakout environment started!")

    # Run a simple loop to demonstrate stepping through the environment
    try:
        for _ in range(100):
            # Preprocess the observation
            processed_obs = preprocess_frame(observation, device)
            
            # Print the shape and device of the processed frame for verification
            if _ == 0:
                print(f"Original observation shape: {observation.shape}")
                print(f"Processed observation shape: {processed_obs.shape}, dtype: {processed_obs.dtype}, device: {processed_obs.device}")

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
