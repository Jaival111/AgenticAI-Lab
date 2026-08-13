from collections import deque

grid = [
    ['S', '.', 'P', '.'],
    ['.', '.', '.', '.'],
    ['.', '.', '.', 'G']
]

def is_adjacent_to_pit(r, c, grid):
    rows, cols = len(grid), len(grid[0])
    for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 'P':
            return True
    return False

def hybrid_bfs(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    queue = deque([(start[0], start[1], [])])
    visited = {start}

    while queue:
        r, c, path = queue.popleft()
        if (r, c) == goal:
            return path
            
        for dr, dc, move in [(-1,0,'UP'), (1,0,'DOWN'), (0,-1,'LEFT'), (0,1,'RIGHT')]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != '#':
                # Reactive Safety Rule: Filter out moves adjacent to pits 'P'
                if is_adjacent_to_pit(nr, nc, grid):
                    continue
                if (nr, nc) not in visited:
                    visited.add((nr, nc))
                    queue.append((nr, nc, path + [(move, (nr, nc))]))
    return None

plan = hybrid_bfs(grid, (0, 0), (2, 3))
print("Safe Hybrid Plan:", [step[0] for step in plan] if plan else "No safe path")  