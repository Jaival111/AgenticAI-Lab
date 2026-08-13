import random

class DynamicEnvironment:
    def __init__(self):
        self.state = {'A': 'Dirty', 'B': 'Dirty'}
        self.location = 'A'
        self.score = 0

    def percept(self):
        return self.location, self.state[self.location]

    def execute(self, action):
        # Apply action
        if action == 'Right':
            self.location = 'B'
            self.score -= 1
        elif action == 'Left':
            self.location = 'A'
            self.score -= 1
        elif action == 'Suck':
            if self.state[self.location] == 'Dirty':
                self.state[self.location] = 'Clean'
                self.score += 10
                
        # Dirt reappears with probability 0.1 per step
        for loc in ['A', 'B']:
            if self.state[loc] == 'Clean' and random.random() < 0.1:
                self.state[loc] = 'Dirty'

class SimpleReflexAgent:
    def program(self, percept):
        location, status = percept
        if status == 'Dirty':
            return 'Suck'
        elif location == 'A':
            return 'Right'
        elif location == 'B':
            return 'Left'

env = DynamicEnvironment()
agent = SimpleReflexAgent()

print("Step | Loc | Action | State                        | Score")
print("-" * 60)
for step in range(1, 21):
    percept = env.percept()
    action = agent.program(percept)
    env.execute(action)
    print(f"{step:4} | {env.location:3} | {action:6} | {str(env.state):13} | {env.score}")

print("\nFinal Dynamic Score:", env.score)