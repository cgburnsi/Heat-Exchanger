import matplotlib.pyplot as plt
from utils import convert as cv
from src.fluids import FluidState, StreamType, Fluid
from src.builders import HXBuilder
from src.models import GrimisonModel, ModifiedGrimisonModel, ZhukauskasModel
from src.models.pressure import GunterShawModel

# ==============================================================================
# 1. REFERENCE DATA
# ==============================================================================
PAPER_DATA = {
    "Original Grimison": {
        "x": [0.0, 0.41, 0.93, 1.76, 3.84, 6.85, 11.83, 19.35, 28.27, 30.81, 31.90, 33.20, 41.65, 81.91],
        "y": [5023.38, 4322.08, 3381.82, 2831.17, 1828.57, 1251.95, 727.27, 358.44, 192.21, 171.43, 124.68, 98.70, 77.92, 77.92],
    },
    "Modified Grimison": {
        "x": [0.05, 0.73, 2.18, 3.84, 7.42, 3.42, 4.93, 9.75, 13.95, 21.42, 26.61, 29.93, 30.86, 31.59, 35.53, 45.49, 81.91],
        "y": [5007.79, 4576.62, 3641.56, 2940.26, 2384.42, 3148.05, 2779.22, 2051.95, 1589.61, 1038.96, 789.61, 664.94, 628.57, 529.87, 259.74, 98.70, 77.92],
    },
    "Zhukauskas Model": {
        "x": [0.05, 0.57, 1.45, 2.85, 4.31, 5.65, 7.52, 10.01, 12.19, 15.93, 21.58, 25.88, 29.93, 30.86, 31.33, 31.64, 31.90, 32.68, 34.70, 40.51, 50.68, 81.91],
        "y": [5023.38, 4768.83, 4296.10, 3719.48, 3298.70, 2971.43, 2581.82, 2129.87, 1818.18, 1418.18, 1012.99, 800.0, 649.35, 618.18, 545.45, 488.31, 436.36, 374.03, 249.35, 114.29, 83.12, 77.92],
    },
}

def get_validation_geometry():
    W = cv.convert(48, 'in', 'm')
    config = [
        {'type': 'bare', 'name': 'Bank 0', 'width': W, 'tubes_deep': 4,
         'tube_od': cv.convert(2.399, 'in', 'm'), 'S_T': cv.convert(4.75, 'in', 'm'), 'S_L': cv.convert(2.5, 'in', 'm')},
        {'type': 'bare', 'name': 'Bank 1', 'width': W, 'tubes_deep': 26,
         'tube_od': cv.convert(1.518, 'in', 'm'), 'S_T': cv.convert(4.4375, 'in', 'm'), 'S_L': cv.convert(1.9060, 'in', 'm')},
        {'type': 'bare', 'name': 'Bank 2', 'width': W, 'tubes_deep': 2,
         'tube_od': cv.convert(1.518, 'in', 'm'), 'S_T': cv.convert(4.4375, 'in', 'm'), 'S_L': cv.convert(1.9060, 'in', 'm')},
        {'type': 'bare', 'name': 'Bank 3', 'width': W, 'tubes_deep': 2,
         'tube_od': cv.convert(1.518, 'in', 'm'), 'S_T': cv.convert(4.4375, 'in', 'm'), 'S_L': cv.convert(1.9060, 'in', 'm')},
        {'type': 'finned', 'name': 'Bank 4', 'width': W, 'tubes_deep': 46,
         'tube_od': cv.convert(0.625, 'in', 'm'), 'S_T': cv.convert(2.25, 'in', 'm'), 'S_L': cv.convert(0.94, 'in', 'm'),
         'fin_pitch': cv.convert(1.0/8.0, 'in', 'm'), 'fin_thickness': cv.convert(0.012, 'in', 'm')}
    ]
    return config

def run_simulation(model_factory, model_name, hot_in, cold_in, config):
    print(f"--- Running {model_name} ---")
    
    if isinstance(model_factory, type): physics = model_factory()
    elif callable(model_factory) and not hasattr(model_factory, 'calculate_Nu'): physics = model_factory()
    else: physics = model_factory
    
    pressure_physics = GunterShawModel(use_correction=True)
    
    builder = HXBuilder("Validation_Run", physics, pressure_model=pressure_physics)
    builder.add_zones_from_config(config)
    hx = builder.build(hot_in, cold_in)
    hx.solve()
    
    rows = [0]
    temps_f = [cv.convert(hot_in.T, 'K', 'degF')]
    pressures_psi = [cv.convert(hot_in.P, 'Pa', 'psi')] 
    reynolds = [0]
    wall_temps = [cv.convert(cold_in.T, 'K', 'degF')]
    cool_temps = [cv.convert(cold_in.T, 'K', 'degF')]
    
    current_row = 0
    profile_idx = 1
    
    for zone in hx.zones:
        # History
        z_re = getattr(zone, 'history', {}).get('Re_g', [])
        z_Tw = getattr(zone, 'history', {}).get('T_wall', [])
        z_Tc = getattr(zone, 'history', {}).get('T_cool', [])
        
        for i in range(zone.n_cols):
            if profile_idx < len(hx.hot_stream.profile):
                state = hx.hot_stream.profile[profile_idx]
                current_row += 1
                rows.append(current_row)
                temps_f.append(cv.convert(state.T, 'K', 'degF'))
                pressures_psi.append(cv.convert(state.P, 'Pa', 'psi'))
                
                # Append Stats
                val_re = z_re[i] if i < len(z_re) else 0.0
                reynolds.append(val_re)
                
                val_tw = z_Tw[i] if i < len(z_Tw) else wall_temps[-1]
                wall_temps.append(cv.convert(val_tw, 'K', 'degF'))
                
                val_tc = z_Tc[i] if i < len(z_Tc) else cool_temps[-1]
                cool_temps.append(cv.convert(val_tc, 'K', 'degF'))
                
                profile_idx += 1
            else:
                return rows, temps_f, pressures_psi, reynolds, wall_temps, cool_temps
                
    return rows, temps_f, pressures_psi, reynolds, wall_temps, cool_temps

def main():
    hot_in = FluidState(StreamType.GAS, T=cv.convert(5050, 'degF', 'K'), 
                        P=cv.convert(1.47, 'psi', 'Pa'), m_dot=1.288, fluid="GuptaAir")
    cold_in = FluidState(StreamType.COOLANT, T=297.2, P=613600.0, m_dot=608.0, fluid=Fluid.WATER)

    config = get_validation_geometry()
    results = {}
    
    # Run only Modified Grimison to save time/clutter if you like, but keeping all 3 is fine
    results['Grimison'] = run_simulation(lambda: GrimisonModel(method="hammock"), "Grimison (Original)", hot_in, cold_in, config)
    results['Modified'] = run_simulation(lambda: ModifiedGrimisonModel(method="hammock"), "Modified Grimison", hot_in, cold_in, config)
    results['Zhukauskas'] = run_simulation(ZhukauskasModel, "Zhukauskas", hot_in, cold_in, config)

    # --- PLOTTING (5 Plots) ---
    fig, axes = plt.subplots(5, 1, figsize=(10, 20), sharex=True)
    ax1, ax2, ax3, ax4, ax5 = axes
    
    style_map = {
        'Grimison': ('blue', 'o'), 'Modified': ('red', 's'),
        'Zhukauskas': ('green', '^')
    }
    
    # 1. Ref Data
    for model_name, data in PAPER_DATA.items():
        color, marker = 'black', '.'
        if "Original Grimison" in model_name: color, marker = style_map['Grimison']
        elif "Modified Grimison" in model_name: color, marker = style_map['Modified']
        elif "Zhukauskas" in model_name: color, marker = style_map['Zhukauskas']
        
        # Don't plot Kays for clarity if not needed
        if "Kays" not in model_name:
            ax1.scatter(data['x'], data['y'], label=f"Paper: {model_name}", edgecolors=color, facecolors='none', marker=marker, s=60)

    # 2. Sim Results
    for name, (rows, temps, pressures, reynolds, wall_temps, cool_temps) in results.items():
        key = None
        if "Grimison" in name and "Original" in name: key = 'Grimison'
        elif "Modified" in name: key = 'Modified'
        elif "Zhukauskas" in name: key = 'Zhukauskas'
        
        color, _ = style_map.get(key, ('black', None))
        
        ax1.plot(rows, temps, color=color, linewidth=2, label=f"Sim: {name}")
        ax2.plot(rows, pressures, color=color, linewidth=2, label=f"Sim: {name}")
        ax3.plot(rows, reynolds, color=color, linewidth=2, label=f"Sim: {name}")
        ax4.plot(rows, wall_temps, color=color, linewidth=2, label=f"Sim: {name}")
        ax5.plot(rows, cool_temps, color=color, linewidth=2, label=f"Sim: {name}")

    ax1.set_ylabel("Gas Temp (°F)"); ax1.grid(True, alpha=0.3); ax1.legend()
    ax1.set_title("Gas Temperature (Figure 22)")
    
    ax2.set_ylabel("Pressure (psi)"); ax2.grid(True, alpha=0.3)
    ax2.set_title("Gas Pressure")
    
    ax3.set_ylabel("Reynolds (-)"); ax3.grid(True, alpha=0.3)
    ax3.set_title("Reynolds Number (Figure 25)")
    
    ax4.set_ylabel("Wall Temp (°F)"); ax4.grid(True, alpha=0.3)
    ax4.set_title("Tube Wall Temperature (Figure 24)")
    
    ax5.set_ylabel("Coolant Temp (°F)"); ax5.grid(True, alpha=0.3)
    ax5.set_title("Coolant Temperature (Figure 23)")
    ax5.set_xlabel("Row Number")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()