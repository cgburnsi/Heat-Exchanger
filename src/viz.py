import matplotlib.pyplot as plt
from matplotlib.patches import Circle

def plot_all_zones(zones, ax=None, show=True):
    """
    Plot the tube layouts for all zones on a single axes.

    Assumes each zone:
      - has .tube_centers (list of (x, y)) or a .build_geometry() method
      - has .tube_dia
      - optionally has .origin_x, .origin_y, .height, .S_L, .n_cols for a zone box
    """
    if ax is None:
        fig, ax = plt.subplots()

    x_min_global = None
    x_max_global = None
    y_min_global = None
    y_max_global = None

    for zone in zones:
        # Ensure geometry exists
        if not getattr(zone, "tube_centers", None):
            if hasattr(zone, "build_geometry"):
                zone.build_geometry()
            else:
                continue

        if not hasattr(zone, "tube_dia"):
            continue

        r = 0.5 * zone.tube_dia
        xs = []
        ys = []

        # Draw tubes as circles
        for x, y in zone.tube_centers:
            circ = Circle((x, y), r, fill=False)
            ax.add_patch(circ)
            xs.append(x)
            ys.append(y)

        # Update global limits from tube extents
        if xs and ys:
            x_min_local = min(xs) - r
            x_max_local = max(xs) + r
            y_min_local = min(ys) - r
            y_max_local = max(ys) + r

            if x_min_global is None or x_min_local < x_min_global:
                x_min_global = x_min_local
            if x_max_global is None or x_max_local > x_max_global:
                x_max_global = x_max_local
            if y_min_global is None or y_min_local < y_min_global:
                y_min_global = y_min_local
            if y_max_global is None or y_max_local > y_max_global:
                y_max_global = y_max_local

        # Draw zone rectangle if we have enough info
        if (hasattr(zone, "origin_x") and hasattr(zone, "origin_y")
                and hasattr(zone, "height") and hasattr(zone, "S_L")
                and hasattr(zone, "n_cols")):
            x_min = zone.origin_x - r
            x_max = zone.origin_x + (zone.n_cols - 1) * zone.S_L + r
            y_min = zone.origin_y
            y_max = zone.origin_y + zone.height

            ax.plot(
                [x_min, x_max, x_max, x_min, x_min],
                [y_min, y_min, y_max, y_max, y_min],
                linestyle="--"
            )

            # Label the zone at its center
            name = getattr(zone, "name", "")
            if name:
                ax.text(
                    0.5 * (x_min + x_max),
                    y_max,
                    name,
                    ha="center",
                    va="bottom"
                )

    # Set global limits and aspect
    if x_min_global is not None:
        ax.set_xlim(x_min_global, x_max_global)
    if y_min_global is not None:
        ax.set_ylim(y_min_global, y_max_global)

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title("Heat Exchanger Tube Layout (All Zones)")

    if show:
        plt.show()

    return ax

def plot_temperature_profile(hx):
    """Plots T vs x for hot and cold streams."""
    import matplotlib.pyplot as plt
    
    # Extract data using the helper we added to FluidStream
    hx_g, T_g, _ = hx.hot_stream.get_data()
    hx_c, T_c, _ = hx.cold_stream.get_data()
    
    plt.figure(figsize=(10, 6))
    plt.plot(hx_g, T_g, 'r-', linewidth=2, label='Gas')
    plt.plot(hx_c, T_c, 'b-', linewidth=2, label='Coolant')
    
    # Draw vertical lines for zone boundaries
    for zone in hx.zones:
        plt.axvline(zone.origin_x, color='k', linestyle=':', alpha=0.5)
        # Label zone
        plt.text(zone.origin_x, (min(T_c)+max(T_g))/2, f" {zone.name}", rotation=90, va='center')

    plt.xlabel("Position [m]")
    plt.ylabel("Temperature [K]")
    plt.title(f"Temperature Profile: {hx.name}")
    plt.legend()
    plt.grid(True)
    plt.show()
    
    
    
    
def plot_pressure_profile(hx):
    """
    Plot P vs x for hot and cold streams using Twin Axes.
    Left Axis: Gas (Torr)
    Right Axis: Coolant (psi)
    """
    import matplotlib.pyplot as plt

    # Extract data
    x_g, _, P_g = hx.hot_stream.get_data()
    x_c, _, P_c = hx.cold_stream.get_data()
    
    # Convert Units for Plotting
    # Gas: Pa -> Torr
    P_g_torr = [p / 133.322 for p in P_g]
    # Coolant: Pa -> psi
    P_c_psi = [p / 6894.76 for p in P_c]

    fig, ax1 = plt.subplots(figsize=(10, 6))

    # --- LEFT AXIS (GAS) ---
    color = 'tab:red'
    ax1.set_xlabel('Position [m]')
    ax1.set_ylabel('Gas Pressure [Torr]', color=color)
    if x_g and P_g_torr:
        ax1.plot(x_g, P_g_torr, color=color, linewidth=2, label='Gas')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True, linestyle=':', alpha=0.6)

    # --- RIGHT AXIS (COOLANT) ---
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    color = 'tab:blue'
    ax2.set_ylabel('Coolant Pressure [psi]', color=color)
    if x_c and P_c_psi:
        ax2.plot(x_c, P_c_psi, color=color, linewidth=2, linestyle='--', label='Coolant')
    ax2.tick_params(axis='y', labelcolor=color)

    # Draw Vertical Zone Lines
    # We use the y-limits of ax1 for drawing the lines
    y_min, y_max = ax1.get_ylim()
    for zone in hx.zones:
        ax1.axvline(zone.origin_x, color='k', linestyle='-', alpha=0.3)
        # Label zone at the top
        ax1.text(zone.origin_x, y_max, f" {zone.name}", 
                 rotation=90, va='top', ha='left', fontsize=9, color='gray')

    plt.title(f"Pressure Profile: {hx.name}")
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.show()