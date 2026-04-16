import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.lines import Line2D

# Grid config
rows, cols = 4, 3
dx, dy = 1.5, 1.5
cell_radius = 0.4

fig, ax = plt.subplots(figsize=(6, 10))

# Data structures
cells = {}     # (i, j): Circle
h_lines = {}   # i: Line2D (horizontal wire between row i-1 and i)
v_lines = {}   # j: Line2D (vertical wire between col j-1 and j)

# Draw cells
for i in range(rows):
    for j in range(cols):
        x = j * dx
        y = i * dy
        circle = Circle((x, y), cell_radius, color='skyblue', ec='black', zorder=3, picker=True)
        ax.add_patch(circle)
        cells[(i, j)] = circle

# Horizontal full-length wires (between rows)
for i in range(1, rows):
    y = i * dy - dy / 2
    x_start = -dx / 2
    x_end = (cols - 1) * dx + dx / 2
    line = Line2D([x_start, x_end], [y, y], color='red', linewidth=2, zorder=1)
    ax.add_line(line)
    h_lines[i] = line

# Vertical full-length wires (between columns)
for j in range(1, cols):
    x = j * dx - dx / 2
    y_start = -dy / 2
    y_end = (rows - 1) * dy + dy / 2
    line = Line2D([x, x], [y_start, y_end], color='red', linewidth=2, zorder=1)
    ax.add_line(line)
    v_lines[j] = line

# Active elements for reset
active_items = []

def highlight_fault_lines(event):
    global active_items

    for (i, j), circle in cells.items():
        if circle.contains_point((event.x, event.y), radius=1.0):
            # Highlight the cell
            circle.set_facecolor('orange')
            active_items.append(circle)

            # Top horizontal wire
            if i > 0 and i in h_lines:
                h_lines[i].set_color('orange')
                active_items.append(h_lines[i])

            # Bottom horizontal wire
            if i + 1 < rows and (i + 1) in h_lines:
                h_lines[i + 1].set_color('orange')
                active_items.append(h_lines[i + 1])

            # Left vertical wire
            if j > 0 and j in v_lines:
                v_lines[j].set_color('orange')
                active_items.append(v_lines[j])

            # Right vertical wire
            if j + 1 < cols and (j + 1) in v_lines:
                v_lines[j + 1].set_color('orange')
                active_items.append(v_lines[j + 1])

            fig.canvas.draw()
            break

def reset_highlights(event):
    global active_items
    for item in active_items:
        if isinstance(item, Circle):
            item.set_facecolor('skyblue')
        elif isinstance(item, Line2D):
            item.set_color('red')
    active_items.clear()
    fig.canvas.draw()

# Event bindings
fig.canvas.mpl_connect('button_press_event', highlight_fault_lines)
fig.canvas.mpl_connect('button_release_event', reset_highlights)

# Styling
ax.set_aspect('equal')
ax.set_xlim(-1, cols * dx)
ax.set_ylim(-1, rows * dy)
ax.axis('off')
plt.title('Click & Hold Cell to Highlight All Touching Grid Lines', fontsize=14)
plt.tight_layout()
plt.show()