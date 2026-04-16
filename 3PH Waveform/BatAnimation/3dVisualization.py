import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation
from scipy.interpolate import RegularGridInterpolator, griddata

# ─── Configuration ───────────────────────────────────────────────────────────────
N_CELLS_X = 3
N_CELLS_Y = 3
RADIUS = 0.018      # 18650 radius ≈ 18 mm
HEIGHT = 0.065      # cell height ≈ 65 mm
SPACING = 0.004     # spacing between cell surfaces (4 mm)

# Positions of cell centers (xy plane)
x_centers = np.linspace(-1, 1, N_CELLS_X) * (2*RADIUS + SPACING)
y_centers = np.linspace(-1, 1, N_CELLS_Y) * (2*RADIUS + SPACING)
XX, YY = np.meshgrid(x_centers, y_centers)

# Thermocouple positions — cross / plus sign between cells
# Assuming arrangement: between rows and between columns (like + )
tc_x = [x_centers[1], x_centers[1]]               # vertical line in middle column
tc_y = [y_centers[0], y_centers[2]]               # horizontal line in middle row
tc_positions = np.array([
    [x_centers[0], y_centers[1]],   # left-middle
    [x_centers[2], y_centers[1]],   # right-middle
    [x_centers[1], y_centers[0]],   # middle-bottom
    [x_centers[1], y_centers[2]],   # middle-top
])

# For nicer interpolation we add the four corner points with dummy/average values later

# ─── Grid for surface plotting ───────────────────────────────────────────────────
res = 80                    # resolution — higher = smoother but slower
x = np.linspace(XX.min()-RADIUS*1.1, XX.max()+RADIUS*1.1, res)
y = np.linspace(YY.min()-RADIUS*1.1, YY.max()+RADIUS*1.1, res)
X, Y = np.meshgrid(x, y)

# Cylinder surface points (for nicer look than just bars)
theta = np.linspace(0, 2*np.pi, 36)
z_cyl = np.linspace(0, HEIGHT, 24)
Theta, Z_cyl = np.meshgrid(theta, z_cyl)

# ─── Simulation-like temperature data generator ──────────────────────────────────
def generate_temperature_frame(t):
    """Silly but nice-looking evolving temperature field"""
    base = 28 + 4*np.sin(t*0.7) + 3*np.cos(t*1.1 + 1.4)
    
    # Hot spot slowly moving
    hx = 0.012 * np.sin(t*0.4 + 0.7)
    hy = 0.015 * np.cos(t*0.55 + 2.1)
    
    dist = np.sqrt((XX-hx)**2 + (YY-hy)**2)
    hotspot = 12 * np.exp(-dist**2 / (0.028**2))
    
    # Some cell-to-cell variation
    variation = np.random.normal(0, 0.7, (3,3)) * (1 + 0.3*np.sin(t*1.8))
    
    T_cells = base + hotspot + variation
    
    # Sample at thermocouple positions
    T_tc = np.array([
        T_cells[1,1],   # fake — middle should be most representative
        T_cells[1,1],
        T_cells[1,1],
        T_cells[1,1]
    ]) + np.random.normal(0, 0.4, 4) + np.array([0.8, -0.6, 1.2, -0.9])*np.sin(t*1.3)
    
    return T_cells, T_tc


# ─── Main interpolation + plotting function ──────────────────────────────────────
def update(frame):
    ax.cla()
    
    t = frame * 0.12
    T_cells, T_measured = generate_temperature_frame(t)
    
    # ── Interpolate on fine grid ────────────────────────────────────────────────
    points = tc_positions
    values = T_measured
    
    # Optional: add fake boundary points to improve edge behavior
    avg = np.mean(T_measured)
    extra_points = np.array([
        [XX.min(), YY.min()], [XX.max(), YY.min()],
        [XX.min(), YY.max()], [XX.max(), YY.max()],
    ])
    extra_values = np.array([avg]*4) + np.random.normal(0, 1.2, 4)
    
    all_points = np.vstack([points, extra_points])
    all_values = np.concatenate([values, extra_values])
    
    T_interp = griddata(all_points, all_values, (X, Y),
                        method='cubic',    # 'linear', 'nearest', 'cubic'
                        fill_value=np.mean(all_values))
    
    # ── Plot interpolated surface ───────────────────────────────────────────────
    surf = ax.plot_surface(X, Y, T_interp, 
                          rstride=1, cstride=1, 
                          cmap=cm.plasma, 
                          vmin=24, vmax=46,
                          alpha=0.85,
                          linewidth=0, antialiased=True,
                          zorder=1)
    
    # ── Plot actual 18650 cells as lit cylinders ────────────────────────────────
    for i in range(3):
        for j in range(3):
            xc, yc = XX[i,j], YY[i,j]
            Tc = T_cells[i,j]
            
            Xc = xc + RADIUS * np.cos(Theta)
            Yc = yc + RADIUS * np.sin(Theta)
            Zc = Z_cyl.reshape(-1,1) * np.ones_like(Theta)
            
            # Color by temperature
            color = cm.plasma((Tc - 24)/(46-24))
            
            cyl = ax.plot_surface(Xc, Yc, Zc,
                                 facecolors=color,
                                 shade=True,
                                 alpha=0.92,
                                 zorder=3)
    
    # ── Small spheres at thermocouple locations ─────────────────────────────────
    for (px,py), temp in zip(tc_positions, T_measured):
        ax.scatter([px],[py],[HEIGHT+0.004], 
                  s=80, color='black', zorder=10, alpha=0.9)
        ax.scatter([px],[py],[HEIGHT+0.004], 
                  s=36, color=cm.plasma((temp-24)/(46-24)), zorder=11)
    
    # ── Cosmetics ────────────────────────────────────────────────────────────────
    ax.set_zlim(0, HEIGHT*1.15)
    ax.set_xlim(X.min(), X.max())
    ax.set_ylim(Y.min(), Y.max())
    
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    
    ax.set_title(f"3×3 18650 pack – t = {t:.1f}s   |   max = {T_interp.max():.1f} °C", 
                fontsize=13, pad=12)
    
    fig.colorbar(surf, ax=ax, shrink=0.6, aspect=30, pad=0.12,
                label='Temperature (°C)')
    
    ax.view_init(elev=22 + 8*np.sin(frame*0.07), 
                azim=frame*1.8 - 60)   # gentle rotation + bobbing
    
    return surf,


# ─── Animation setup ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(11, 9), dpi=100, facecolor='#111111')
ax = fig.add_subplot(111, projection='3d')
ax.set_facecolor('#0a0a0a')

ani = animation.FuncAnimation(
    fig, update,
    frames=300,
    interval=40,
    blit=False
)

plt.tight_layout()
plt.show()

# To save (uncomment if needed):
# ani.save('battery_pack_temperature.mp4', writer='ffmpeg', fps=25, dpi=120,
#          extra_args=['-vcodec', 'libx264', '-crf', '18'])