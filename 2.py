import random

class CorridorEnvironment:
    def __init__(self, N):
        self.N = N
        self.state = {i: random.choice(['Clean', 'Dirty']) for i in range(N)}
        self.location = 0
        self.score = 0

    def percept(self):
        return self.location, self.state[self.location]

    def execute(self, action):
        if action == 'Right' and self.location < self.N - 1:
            self.location += 1
            self.score -= 1
        elif action == 'Left' and self.location > 0:
            self.location -= 1
            self.score -= 1
        elif action == 'Suck':
            if self.state[self.location] == 'Dirty':
                self.state[self.location] = 'Clean'
                self.score += 10


class SweepAgent:
    def __init__(self, N):
        self.N = N
        self.direction = 'Right'

    def program(self, percept):
        location, status = percept
        
        if status == 'Dirty':
            return 'Suck'
        
        # Change direction at boundaries
        if location == self.N - 1:
            self.direction = 'Left'
        elif location == 0:
            self.direction = 'Right'
            
        return self.direction


N = 5
env = CorridorEnvironment(N)
agent = SweepAgent(N)

for step in range(15):
    percept = env.percept()
    action = agent.program(percept)
    env.execute(action)

print(f"Final State: {env.state}")
print("Final Score:", env.score)