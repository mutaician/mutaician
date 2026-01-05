import os
import requests
import json
from datetime import datetime, timedelta

def get_contribution_data():
    token = os.getenv("GITHUB_TOKEN")
    owner = os.getenv("GITHUB_REPOSITORY_OWNER")
    
    if not token or not owner:
        print("No GITHUB_TOKEN found. Generating mock data for local testing...")
        # Return mock data if no token (for local testing)
        import random
        grid = [[0 for _ in range(7)] for _ in range(53)]
        for w in range(53):
            if random.random() > 0.3: # Some weeks are active
                for d in range(7):
                    if random.random() > 0.5:
                        grid[w][d] = random.randint(1, 4)
        return grid

    # Precise query for the last year of contributions
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionLevel
                weekday
                date
              }
            }
          }
        }
      }
    }
    """
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post("https://api.github.com/graphql", json={"query": query, "variables": {"login": owner}}, headers=headers)
    
    if response.status_code != 200:
        return [[0 for _ in range(7)] for _ in range(53)]
        
    data = response.json()
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    
    # Map levels to 0-4
    level_map = {
        "NONE": 0,
        "FIRST_QUARTILE": 1,
        "SECOND_QUARTILE": 2,
        "THIRD_QUARTILE": 3,
        "FOURTH_QUARTILE": 4
    }
    
    grid = [[0 for _ in range(7)] for _ in range(53)]
    for w_idx, week in enumerate(weeks):
        if w_idx >= 53: break
        for day in week["contributionDays"]:
            grid[w_idx][day["weekday"]] = level_map.get(day["contributionLevel"], 0)
            
    return grid

def generate_animated_nn_svg():
    # Constants
    ROWS = 7
    COLS = 53
    CELL_SIZE = 10
    GAP = 3
    
    # GitHub Colors
    C0 = "#161b22" # Empty
    C1 = "#0e4429" # Low
    C2 = "#006d32" # Medium
    C3 = "#26a641" # High
    C4 = "#39d353" # Brightest
    
    colors = [C0, C1, C2, C3, C4]
    
    # Fetch real data
    contribution_grid = get_contribution_data()
    
    # Layer Definitions (start_col, width, height)
    layers = [
        (0, 3, 3),  # Input
        (8, 3, 5),  # Hidden 1
        (16, 3, 7), # Hidden 2
        (25, 3, 7), # Hidden 3 (Middle)
        (34, 3, 7), # Hidden 4
        (42, 3, 5), # Hidden 5
        (50, 3, 3)  # Output
    ]
    
    cell_delays = {}
    step_time = 0.08 # Faster propagation
    
    def add_cell(x, y, delay):
        if (x, y) not in cell_delays or delay < cell_delays[(x, y)]:
            cell_delays[(x, y)] = delay

    # neuron_times[layer_idx][row_in_layer] = time
    neuron_times = [{} for _ in range(len(layers))]

    # Initialize Layer 0 (Input)
    l0_start, l0_w, l0_h = layers[0]
    l0_row_start = (ROWS - l0_h) // 2
    for r in range(l0_h):
        y = l0_row_start + r
        for dx in range(l0_w):
            add_cell(l0_start + dx, y, dx * step_time)
        neuron_times[0][r] = l0_w * step_time

    # Process Gaps and subsequent Layers
    for i in range(len(layers) - 1):
        l_curr = layers[i]
        l_next = layers[i+1]
        curr_row_start = (ROWS - l_curr[2]) // 2
        next_row_start = (ROWS - l_next[2]) // 2
        
        for r_curr in range(l_curr[2]):
            y_curr = curr_row_start + r_curr
            start_t = neuron_times[i][r_curr]
            
            # Mapping logic
            targets = []
            c_h, n_h = l_curr[2], l_next[2]
            if c_h == 3 and n_h == 5:
                if r_curr == 0: targets = [0, 1]
                elif r_curr == 1: targets = [2]
                else: targets = [3, 4]
            elif c_h == 5 and n_h == 7:
                if r_curr == 0: targets = [0, 1]
                elif r_curr == 1: targets = [2]
                elif r_curr == 2: targets = [3]
                elif r_curr == 3: targets = [4]
                else: targets = [5, 6]
            elif c_h == 7 and n_h == 7:
                targets = [r_curr]
            elif c_h == 7 and n_h == 5:
                if r_curr <= 1: targets = [0]
                elif r_curr == 2: targets = [1]
                elif r_curr == 3: targets = [2]
                elif r_curr == 4: targets = [3]
                else: targets = [4]
            elif c_h == 5 and n_h == 3:
                if r_curr <= 1: targets = [0]
                elif r_curr == 2: targets = [1]
                else: targets = [2]
            
            for r_next in targets:
                y_next = next_row_start + r_next
                gap_x_start = l_curr[0] + l_curr[1]
                gap_x_end = l_next[0]
                gap_len = gap_x_end - gap_x_start
                
                t = start_t
                for idx, x in enumerate(range(gap_x_start, gap_x_end)):
                    if idx < gap_len // 2:
                        add_cell(x, y_curr, t)
                        t += step_time
                    elif idx == gap_len // 2:
                        add_cell(x, y_curr, t)
                        t += step_time
                        step = 1 if y_next > y_curr else -1
                        if y_curr != y_next:
                            for y_step in range(y_curr + step, y_next, step):
                                add_cell(x, y_step, t)
                                t += step_time
                        add_cell(x, y_next, t)
                        t += step_time
                    else:
                        add_cell(x, y_next, t)
                        t += step_time
                
                for dx in range(l_next[1]):
                    add_cell(l_next[0] + dx, y_next, t)
                    t += step_time
                
                if r_next not in neuron_times[i+1] or t < neuron_times[i+1][r_next]:
                    neuron_times[i+1][r_next] = t

    # Calculate SVG dimensions
    svg_width = COLS * (CELL_SIZE + GAP) + 20
    svg_height = ROWS * (CELL_SIZE + GAP) + 20
    
    svg = [
        f'<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" xmlns="http://www.w3.org/2000/svg">',
        '<style>',
        '  @keyframes neural-cycle {',
        f'    0% {{ fill: {C0}; }}',
        f'    5% {{ fill: {C4}; }}',
        f'    15% {{ fill: {C0}; }}',
        f'    100% {{ fill: {C0}; }}',
        '  }',
        # Discovery animations: Start at C0, pulse to C4, then settle and STAY at contribution color
        '  @keyframes discovery-1 { 0% { fill: ' + C0 + '; } 5% { fill: ' + C4 + '; } 15% { fill: ' + C1 + '; } 100% { fill: ' + C1 + '; } }',
        '  @keyframes discovery-2 { 0% { fill: ' + C0 + '; } 5% { fill: ' + C4 + '; } 15% { fill: ' + C2 + '; } 100% { fill: ' + C2 + '; } }',
        '  @keyframes discovery-3 { 0% { fill: ' + C0 + '; } 5% { fill: ' + C4 + '; } 15% { fill: ' + C3 + '; } 100% { fill: ' + C3 + '; } }',
        '  @keyframes discovery-4 { 0% { fill: ' + C0 + '; } 5% { fill: ' + C4 + '; } 15% { fill: ' + C4 + '; } 100% { fill: ' + C4 + '; } }',
        '  .cell { animation: neural-cycle 5s infinite; }',
        '  .disc-1 { animation: discovery-1 5s forwards; }',
        '  .disc-2 { animation: discovery-2 5s forwards; }',
        '  .disc-3 { animation: discovery-3 5s forwards; }',
        '  .disc-4 { animation: discovery-4 5s forwards; }',
        '</style>',
        f'<rect width="100%" height="100%" fill="#0d1117" rx="6"/>'
    ]

    # Prepare discovery sequence
    all_contributions = []
    for x in range(COLS):
        for y in range(ROWS):
            if contribution_grid[x][y] > 0:
                all_contributions.append((x, y))
    
    import random
    random.seed(42) 
    random.shuffle(all_contributions)
    
    # Map each contribution to a unique loop index
    discovery_map = {pos: i for i, pos in enumerate(all_contributions)}

    for x in range(COLS):
        for y in range(ROWS):
            cx = x * (CELL_SIZE + GAP) + 10
            cy = y * (CELL_SIZE + GAP) + 10
            
            level = contribution_grid[x][y]
            
            if (x, y) in cell_delays:
                path_delay = cell_delays[(x, y)]
                if level > 0:
                    # Contribution on the path:
                    loop_idx = discovery_map[(x, y)]
                    reveal_delay = (loop_idx * 5) + path_delay
                    svg.append(f'<rect x="{cx}" y="{cy}" width="{CELL_SIZE}" height="{CELL_SIZE}" fill="{C0}" rx="2" class="disc-{level}" style="animation-delay: {reveal_delay}s;"/>')
                else:
                    # Normal path cell: pulses infinitely
                    svg.append(f'<rect x="{cx}" y="{cy}" width="{CELL_SIZE}" height="{CELL_SIZE}" fill="{C0}" rx="2" class="cell" style="animation-delay: {path_delay}s;"/>')
            else:
                # Background cells (not in NN path)
                if level > 0:
                    loop_idx = discovery_map[(x, y)]
                    # Background cells reveal slightly after the main pulse passes their column
                    reveal_delay = (loop_idx * 5) + (x * 0.05) 
                    svg.append(f'<rect x="{cx}" y="{cy}" width="{CELL_SIZE}" height="{CELL_SIZE}" fill="{C0}" rx="2" class="disc-{level}" style="animation-delay: {reveal_delay}s;"/>')
                else:
                    svg.append(f'<rect x="{cx}" y="{cy}" width="{CELL_SIZE}" height="{CELL_SIZE}" fill="{C0}" rx="2"/>')

    svg.append('</svg>')
    return "\n".join(svg)

    svg.append('</svg>')
    return "\n".join(svg)



if __name__ == "__main__":
    with open("neural_network_graph.svg", "w") as f:
        f.write(generate_animated_nn_svg())
    print("Generated neural_network_graph.svg")
