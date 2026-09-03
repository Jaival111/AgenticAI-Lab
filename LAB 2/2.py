from collections import deque

grid = [
    ['S', '.', '.', '.'],
    ['.', '#', '.', '.'],
    ['.', '.', '.', 'G']
]

def bfs(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    queue = deque([(start[0], start[1], [])])
    visited = {start}

    while queue:
        r, c, path = queue.popleft()
        if (r, c) == goal:
            return path
        for dr, dc, move in [(-1,0,'UP'), (1,0,'DOWN'), (0,-1,'LEFT'), (0,1,'RIGHT')]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != '#' and (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append((nr, nc, path + [(move, (nr, nc))]))
    return None

def run_with_replanning(grid, start, goal, blocked_cell):
    current = start
    while current != goal:
        plan = bfs(grid, current, goal)
        if not plan:
            print("No path available!")
            return
        print("Old path: ", plan)
        
        step_taken = False
        for move, next_pos in plan:
            # Simulate dynamic obstruction discovery
            if next_pos == blocked_cell:
                print(f"Obstacle detected at {next_pos}! Updating internal model and replanning...")
                grid[next_pos[0]][next_pos[1]] = '#'  # Update world model
                plan = bfs(grid, start, goal)
                print("New path: ", plan)
                return
            else:
                current = next_pos
                print(f"Executed {move} to {current}")
                step_taken = True
                
    print("Successfully reached goal!")

run_with_replanning(grid, (0, 0), (2, 3), blocked_cell=(2, 1))