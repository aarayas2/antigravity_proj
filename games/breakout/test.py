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
import os

gym.register_envs(ale_py)

def save_checkpoint(state, filename="breakout_model.pth"):
    print(f"Saving checkpoint to {filename}...")
    torch.save(state, filename)

def load_checkpoint(filename, policy_net, target_net, optimizer, device):
    if os.path.isfile(filename):
        print(f"Loading checkpoint '{filename}'...")
        # map_location ensures it loads correctly whether on CPU, CUDA, or MPS
        checkpoint = torch.load(filename, map_location=device, weights_only=False) 
        
        policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
        target_net.load_state_dict(checkpoint['target_net_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        steps_done = checkpoint['steps_done']
        
        print(f"Loaded successfully. Resuming from step {steps_done}.")
        return steps_done
    else:
        print(f"No checkpoint found at '{filename}'. Starting fresh.")
        return 0

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
EPS_DECAY = 250000       
TARGET_UPDATE = 1000    
LEARNING_RATE = 1e-4    

# --- EXECUTION CONFIGURATION ---
RUN_MODE = "TRAIN"              # Options: "TRAIN" or "EVALUATE"
MAX_TRAINING_STEPS = 2_000_000  # 2 Million steps is a good first goal
RENDER_IN_TRAINING = False      # False = Train extremely fast on M1. True = Watch it (very slow).

def main():
    # Set device to MPS (Apple Silicon), CUDA, or CPU
    if torch.backends.mps.is_available():
        device = torch.device('mps')
    elif torch.cuda.is_available():
        device = torch.device('cuda')
    else:
        device = torch.device('cpu')
    print(f"Using device: {device}")
    os.environ["SDL_AUDIODRIVER"] = "dummy"  # Disable sound for the Pygame renderer

    # ALE/Breakout-v5 is the standard Atari environment in Gymnasium
    render_mode = "human" if (RENDER_IN_TRAINING or RUN_MODE == "EVALUATE") else None
    env = gym.make('ALE/Breakout-v5', render_mode=render_mode)
    n_actions = env.action_space.n
    
    # Initialize DQN model (Policy Network)
    policy_net = DQN(n_actions).to(device)

    # Initialize The Target Network (The Mentor)
    target_net = DQN(n_actions).to(device)
    target_net.load_state_dict(policy_net.state_dict())
    target_net.eval() # Set to evaluation mode (not training)

    # Initialize The Optimizer (The Coach)
    optimizer = optim.Adam(policy_net.parameters(), lr=LEARNING_RATE)
    
    def optimize_model():
        # Don't learn until we have enough memories saved up
        if len(memory) < BATCH_SIZE:
            return  
        
        # Grab a random batch of memories
        transitions = memory.sample(BATCH_SIZE)
        batch_state, batch_action, batch_reward, batch_next_state, batch_done = zip(*transitions)

        # Convert them to PyTorch tensors on your M1 GPU
        state_b = torch.cat(batch_state)
        next_state_b = torch.cat(batch_next_state)
        reward_b = torch.tensor(batch_reward, device=device)
        action_b = torch.tensor(batch_action, device=device).unsqueeze(1)
        done_b = torch.tensor(batch_done, device=device, dtype=torch.float)

        # What did our Policy Net predict?
        current_q = policy_net(state_b).gather(1, action_b)

        # What was the actual result according to the Mentor (Target Net)?
        with torch.no_grad():
            max_next_q = target_net(next_state_b).max(1)[0]
            expected_q = reward_b + (GAMMA * max_next_q * (1 - done_b))

        # --- STAGE 2: The Loss Function (The Gradebook) ---
        loss = F.huber_loss(current_q.squeeze(), expected_q)
        
        # --- STAGE 3: The Optimizer step (The Coach making adjustments) ---
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    # Check for existing save file before starting
    CHECKPOINT_FILE = "breakout_model.pth"
    steps_done = load_checkpoint(CHECKPOINT_FILE, policy_net, target_net, optimizer, device)
    
    observation, info = env.reset()

    # Preprocess the initial observation
    initial_frame = preprocess_frame(observation, device)
    
    # Initialize a deque to hold the 4 most recent frames for stacking
    frame_stack = deque([initial_frame] * 4, maxlen=4)
    state = get_state(frame_stack)

    # Initialize Replay Buffer
    memory = ReplayBuffer(capacity=10000)

    print("Breakout environment started!")

    # Run a continuous loop until we hit the maximum limit
    try:
        # Check if we are evaluating (run forever) or training (stop at MAX)
        while steps_done < MAX_TRAINING_STEPS or RUN_MODE == "EVALUATE":
            # Print the shape and device of the processed frame for verification
            if steps_done == 1:
                print(f"Original observation shape: {observation.shape}")
                print(f"Processed observation shape: {state.shape}, dtype: {state.dtype}, device: {state.device}")

            # --- ACTION SELECTION ---
            if RUN_MODE == "TRAIN":
                steps_done += 1
                epsilon = EPS_END + (EPS_START - EPS_END) * math.exp(-1. * steps_done / EPS_DECAY)
            else:
                epsilon = 0.00 # NO random moves during evaluation!
            
            if random.random() > epsilon:
                with torch.no_grad():
                    # Exploit: Let the neural network pick the best move
                    # state is (1, 4, 84, 84)
                    q_values = policy_net(state)
                    # Select the action with the highest Q-value
                    action = q_values.max(1)[1].item()
            else:
                # Explore: Pick a completely random move
                action = env.action_space.sample()
            
            # Step the environment
            next_observation, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
            # Preprocess the next observation
            next_frame = preprocess_frame(next_observation, device)
            
            # Update frame stack
            frame_stack.append(next_frame)
            next_state = get_state(frame_stack)
            
            # Move to the next state
            state = next_state
            
            # --- TRAINING LOGIC (Only if in TRAIN mode) ---
            if RUN_MODE == "TRAIN":
                # Store the transition in the replay buffer
                memory.push(state, action, reward, next_state, done)
                
                # --- TRIGGER THE STUDY SESSION ---
                optimize_model()
                
                # --- STAGE 1: Sync the Target Network with the Policy Network ---
                if steps_done % TARGET_UPDATE == 0:
                    target_net.load_state_dict(policy_net.state_dict())
                
                # --- SAVE PROGRESS PERIODICALLY ---
                if steps_done % 5000 == 0: # Save every 5,000 steps
                    checkpoint = {
                        'steps_done': steps_done,
                        'policy_net_state_dict': policy_net.state_dict(),
                        'target_net_state_dict': target_net.state_dict(),
                        'optimizer_state_dict': optimizer.state_dict()
                    }
                    save_checkpoint(checkpoint, CHECKPOINT_FILE)
            
            if done:
                observation, info = env.reset()
                initial_frame = preprocess_frame(observation, device)
                for _ in range(4): frame_stack.append(initial_frame)
                state = get_state(frame_stack)
                
            if render_mode == "human":
                time.sleep(0.01) # Slow down a bit to see the rendering
            
            # Periodically print progress for testing
            if steps_done % 1000 == 0:
                print(f"Step {steps_done}/{MAX_TRAINING_STEPS}: Replay Buffer Size = {len(memory)}, Epsilon = {epsilon:.3f}")
            
    except KeyboardInterrupt:
            print("Interrupted by user.")
    finally:
        # Save checkpoint before exiting
        save_checkpoint({
            'steps_done': steps_done,
            'policy_net_state_dict': policy_net.state_dict(),
            'target_net_state_dict': target_net.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
        })
        env.close()

if __name__ == "__main__":
    main()
