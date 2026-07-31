class Environment:
    def __init__(self):
        self.state = {'A': 'Dirty', 'B': 'Dirty'}
        self.location = 'A'
        self.score = 0

    def percept(self):
        return self.location, self.state[self.location]

    def execute(self, action):
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
        elif action == 'NoOp':
            pass

class ModelBasedAgent:
    def __init__(self):
        self.model = {'A': 'Unknown', 'B': 'Unknown'}

    def program(self, percept):
        location, status = percept
        self.model[location] = status
        
        if status == 'Dirty':
            return 'Suck'
        elif self.model['A'] == 'Clean' and self.model['B'] == 'Clean':
            return 'NoOp'
        elif location == 'A':
            return 'Right'
        elif location == 'B':
            return 'Left'

env = Environment()
agent = ModelBasedAgent()

print("Step | Loc | Action | State                        | Score")
print("-" * 60)
for step in range(1, 21):
    percept = env.percept()
    action = agent.program(percept)
    env.execute(action)
    print(f"{step:4} | {env.location:3} | {action:6} | {str(env.state):13} | {env.score}")

print("\nFinal Model-Based Agent's score:", env.score)