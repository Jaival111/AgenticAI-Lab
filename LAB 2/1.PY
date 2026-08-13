import heapq

grid = [
    ['S', '.', '.', '#'],
    ['.', '#', '.', '.'],
    ['.', '.', '.', 'G']
]

costs = [
    [1, 5, 1, 1],
    [1, 1, 1, 1],
    [1, 10, 1, 1]
]

moves = [(-1, 0, 'UP'), (1, 0, 'DOWN'), (0, -1, 'LEFT'), (0, 1, 'RIGHT')]

def ucs(grid, costs, start, goal):
    rows, cols = len(grid), len(grid[0])
    pq = [(0, start[0], start[1], [])]  # (cost, r, c, path)
    visited = {}

    while pq:
        cost, r, c, path = heapq.heappop(pq)

        if (r, c) in visited and visited[(r, c)] <= cost:
            continue
        visited[(r, c)] = cost

        if (r, c) == goal:
            return path, cost

        for dr, dc, move in moves:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != '#':
                new_cost = cost + costs[nr][nc]
                heapq.heappush(pq, (new_cost, nr, nc, path + [(move, (nr, nc))]))
    return None, float('inf')

start = (0, 0)
goal = (2, 3)
plan, total_cost = ucs(grid, costs, start, goal)

print(f"Optimal Path: {[step[0] for step in plan]}")
print(f"Total Cost: {total_cost}")