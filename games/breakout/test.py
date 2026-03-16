import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torchvision.transforms as T
import math
import numpy as np
import gymnasium as gym
import time
import ale_py
import random
from collections import deque
gym.register_envs(ale_py)

class DQN(nn.Module):
    def __init__(self, n_actions):
        super(DQN, self).__init__()
        # Input: (Batch, 4, 84, 84) - 4 stacked grayscale frames
        self.conv1 = nn.Conv2d(4, 32, kernel_size=8, stride=4)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=4, stride=2)
        self.conv3 = nn.Conv2d(64, 64, kernel_size=3, stride=1)
        
        # After conv layers, the 84x84 image becomes 7x7 with 64 channels
        self.fc1 = nn.Linear(64 * 7 * 7, 512)
        self.head = nn.Linear(512, n_actions)

    def forward(self, x):
        # Move data through convolutions with ReLU activation
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        
        # Flatten and move through fully connected layers
        x = x.view(x.size(0), -1) 
        x = F.relu(self.fc1(x))
        return self.head(x) # Returns Q-values for each action

class ReplayBuffer:
    def __init__(self, capacity):
        # deque automatically 'pops' the oldest memory when capacity is reached
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        # Store a transition as a tuple
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        # Randomly grab a 'batch' of experiences for the NN to study
        return random.sample(self.buffer, batch_size)

    def __len__(self):
        return len(self.buffer)

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

def get_state(obs_deque):
    """
    Combines 4 frames from a deque into a single tensor of shape (1, 4, 84, 84)
    """
    # obs_deque contains 4 tensors of shape (1, 1, 84, 84)
    # Concatenate them along the channel dimension (dim=1)
    return torch.cat(list(obs_deque), dim=1)

# Hyperparameters
BATCH_SIZE = 32         
GAMMA = 0.99            
EPS_START = 1.0         
EPS_END = 0.1           
EPS_DECAY = 10000       
TARGET_UPDATE = 1000    
LEARNING_RATE = 1e-4    

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
    n_actions = env.action_space.n
    
    # Initialize DQN model (Policy Network)
    policy_net = DQN(n_actions).to(device)

    # Initialize The Target Network (The Mentor)
    target_net = DQN(n_actions).to(device)
    target_net.load_state_dict(policy_net.state_dict())
    target_net.eval() # Set to evaluation mode (not training)

    # Initialize The Optimizer (The Coach)
    optimizer = optim.Adam(policy_net.parameters(), lr=LEARNING_RATE)
    
    observation, info = env.reset()

    # Preprocess the initial observation
    initial_frame = preprocess_frame(observation, device)
    
    # Initialize a deque to hold the 4 most recent frames for stacking
    frame_stack = deque([initial_frame] * 4, maxlen=4)
    state = get_state(frame_stack)

    # Initialize Replay Buffer
    memory = ReplayBuffer(capacity=10000)

    print("Breakout environment started!")

    # Run a simple loop to demonstrate stepping through the environment
    try:
        for step in range(100):
            # Print the shape and device of the processed frame for verification
            if step == 0:
                print(f"Original observation shape: {observation.shape}")
                print(f"Processed observation shape: {state.shape}, dtype: {state.dtype}, device: {state.device}")

            # Your Neural Network would go here to decide 'action'
            # For Breakout, actions typically are: 0=NOOP, 1=FIRE, 2=RIGHT, 3=LEFT
            
            # Epsilon-greedy action selection or test evaluation
            # For now, just choose best action according to policy net to test inference
            with torch.no_grad():
                # state is (1, 4, 84, 84)
                q_values = policy_net(state)
                # Select the action with the highest Q-value
                action = q_values.max(1)[1].item()
                
                # In training, we would typically use epsilon-greedy:
                # if random.random() < epsilon: action = env.action_space.sample()
            
            # Step the environment
            next_observation, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
            # Preprocess the next observation
            next_frame = preprocess_frame(next_observation, device)
            
            # Update frame stack
            frame_stack.append(next_frame)
            next_state = get_state(frame_stack)
            
            # Store the transition in the replay buffer
            memory.push(state, action, reward, next_state, done)
            
            # Move to the next state
            state = next_state
            
            if done:
                observation, info = env.reset()
                initial_frame = preprocess_frame(observation, device)
                for _ in range(4): frame_stack.append(initial_frame)
                state = get_state(frame_stack)
                
            time.sleep(0.01) # Slow down a bit to see the rendering
            
            # Periodically print buffer size for testing
            if step % 20 == 0:
                print(f"Step {step}: Replay Buffer Size = {len(memory)}")
            
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        env.close()

if __name__ == "__main__":
    main()
