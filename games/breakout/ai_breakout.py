import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import math
import numpy as np
import time
import random
import os
from collections import deque

# Import our custom environment builder
from atari_environment import make_atari_env

def save_checkpoint(state, filename="breakout_model.pth"):
    print(f"Saving checkpoint to {filename}...")
    torch.save(state, filename)

def load_checkpoint(filename, policy_net, target_net, optimizer, device):
    if os.path.isfile(filename):
        print(f"Loading checkpoint '{filename}'...")
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
        
        self.fc1 = nn.Linear(64 * 7 * 7, 512)
        self.head = nn.Linear(512, n_actions)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(x.size(0), -1) 
        x = F.relu(self.fc1(x))
        return self.head(x)

class ReplayBuffer:
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        return random.sample(self.buffer, batch_size)

    def __len__(self):
        return len(self.buffer)

def warm_up_buffer(env, memory, device, target_size=5000):
    print(f"Starting warm-up phase... Filling buffer to {target_size} memories.")
    observation, info = env.reset()
    
    # The wrapper gives us a (4, 84, 84) array of floats. Convert to tensor & add batch dim.
    state = torch.tensor(np.array(observation), dtype=torch.float32, device=device).unsqueeze(0)
    
    steps = 0
    while len(memory) < target_size:
        action = env.action_space.sample()
        next_observation, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        
        next_state = torch.tensor(np.array(next_observation), dtype=torch.float32, device=device).unsqueeze(0)
        memory.push(state, action, reward, next_state, done)
        
        state = next_state
        steps += 1
        
        if done:
            observation, info = env.reset()
            state = torch.tensor(np.array(observation), dtype=torch.float32, device=device).unsqueeze(0)
            
        if steps % 1000 == 0:
            print(f"Warm-up progress: {len(memory)}/{target_size} memories collected.")
            
    print("Warm-up complete! Neural Network is ready to train.")

# Hyperparameters
BATCH_SIZE = 32         
GAMMA = 0.99            
EPS_START = 1.0         
EPS_END = 0.1           
EPS_DECAY = 250000       
TARGET_UPDATE = 1000    
LEARNING_RATE = 1e-4    

#RUN_MODE = "TRAIN"
RUN_MODE = "EVALUATE"             
MAX_TRAINING_STEPS = 5_000_000 
RENDER_IN_TRAINING = False      
LEARNING_BUFFER_SIZE = 30_000   

def main():
    if torch.backends.mps.is_available():
        device = torch.device('mps')
    elif torch.cuda.is_available():
        device = torch.device('cuda')
    else:
        device = torch.device('cpu')
    print(f"Using device: {device}")
    
    os.environ["SDL_AUDIODRIVER"] = "dummy" 

    render_mode = "human" if (RENDER_IN_TRAINING or RUN_MODE == "EVALUATE") else None
    
    # Use the new environment wrapper function
    env = make_atari_env('ALE/Breakout-v5', render_mode=render_mode, evaluate=(RUN_MODE == "EVALUATE"))
    n_actions = env.action_space.n
    
    policy_net = DQN(n_actions).to(device)
    target_net = DQN(n_actions).to(device)
    target_net.load_state_dict(policy_net.state_dict())
    target_net.eval()

    optimizer = optim.Adam(policy_net.parameters(), lr=LEARNING_RATE)
    
    def optimize_model():
        if len(memory) < BATCH_SIZE:
            return  
        
        transitions = memory.sample(BATCH_SIZE)
        batch_state, batch_action, batch_reward, batch_next_state, batch_done = zip(*transitions)

        state_b = torch.cat(batch_state)
        next_state_b = torch.cat(batch_next_state)
        # Reward clipping to stabilize learning (standard DeepMind practice)
        reward_b = torch.sign(torch.tensor(batch_reward, device=device))
        action_b = torch.tensor(batch_action, device=device).unsqueeze(1)
        done_b = torch.tensor(batch_done, device=device, dtype=torch.float)

        current_q = policy_net(state_b).gather(1, action_b)

        with torch.no_grad():
            max_next_q = target_net(next_state_b).max(1)[0]
            expected_q = reward_b + (GAMMA * max_next_q * (1 - done_b))

        loss = F.huber_loss(current_q.squeeze(), expected_q)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    CHECKPOINT_FILE = "breakout_model.pth"
    steps_done = load_checkpoint(CHECKPOINT_FILE, policy_net, target_net, optimizer, device)
    memory = ReplayBuffer(capacity=LEARNING_BUFFER_SIZE)

    if RUN_MODE == "TRAIN":
        warm_up_buffer(env, memory, device, target_size=5000)

    episode_reward = 0
    
    observation, info = env.reset()
    state = torch.tensor(np.array(observation), dtype=torch.float32, device=device).unsqueeze(0)

    eval_steps = 0
    lives = info.get('lives', 0)

    try:
        while steps_done < MAX_TRAINING_STEPS or RUN_MODE == "EVALUATE":
            
            if RUN_MODE == "TRAIN":
                steps_done += 1
                epsilon = EPS_END + (EPS_START - EPS_END) * math.exp(-1. * steps_done / EPS_DECAY)
            else:
                eval_steps += 1
                epsilon = 0.00 

            current_lives = info.get('lives', 0)
            if RUN_MODE == "EVALUATE" and current_lives < lives and current_lives > 0:
                action = 1 # Force FIRE to start next ball
            else:
                if random.random() > epsilon:
                    with torch.no_grad():
                        q_values = policy_net(state)
                        action = q_values.max(1)[1].item()
                else:
                    action = env.action_space.sample()
            lives = current_lives
            
            next_observation, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            episode_reward += reward
            
            next_state = torch.tensor(np.array(next_observation), dtype=torch.float32, device=device).unsqueeze(0)
            
            if RUN_MODE == "TRAIN":
                memory.push(state, action, reward, next_state, done)
                state = next_state
                optimize_model()
                
                if steps_done % TARGET_UPDATE == 0:
                    target_net.load_state_dict(policy_net.state_dict())
                
                if steps_done % 5000 == 0: 
                    checkpoint = {
                        'steps_done': steps_done,
                        'policy_net_state_dict': policy_net.state_dict(),
                        'target_net_state_dict': target_net.state_dict(),
                        'optimizer_state_dict': optimizer.state_dict()
                    }
                    save_checkpoint(checkpoint, CHECKPOINT_FILE)
            else:
                state = next_state
            
            if done:
                if RUN_MODE == "EVALUATE":
                    with open("reward_history.csv", "a") as f:
                        f.write(f"{steps_done},{episode_reward}\n")
                
                episode_reward = 0
                observation, info = env.reset()
                state = torch.tensor(np.array(observation), dtype=torch.float32, device=device).unsqueeze(0)
                lives = info.get('lives', 0)
                
            if render_mode == "human":
                time.sleep(0.01)
            
            if RUN_MODE == "TRAIN" and steps_done % 1000 == 0:
                print(f"Step {steps_done}/{MAX_TRAINING_STEPS}: Buffer = {len(memory)}, Epsilon = {epsilon:.3f}")
            elif RUN_MODE == "EVALUATE" and eval_steps % 1000 == 0:
                print(f"Eval Step {eval_steps}: Buffer = {len(memory)}, Epsilon = {epsilon:.3f}")
            
    except KeyboardInterrupt:
            print("Interrupted by user.")
    finally:
        save_checkpoint({
            'steps_done': steps_done,
            'policy_net_state_dict': policy_net.state_dict(),
            'target_net_state_dict': target_net.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
        })
        env.close()

if __name__ == "__main__":
    main()
