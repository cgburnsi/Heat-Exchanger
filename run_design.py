import matplotlib.pyplot as plt
import numpy as np
from utils import convert as cv
from src.fluids import FluidState, StreamType, Fluid
from src.builders import HXBuilder
from src.models import ModifiedGrimisonModel
from src.models.pressure import GunterShawModel

def get_design_geometry():
    """
    DEFINE YOUR ACTUAL DESIGN GEOMETRY HERE.
    """
    W = cv.convert(16, 'in', 'm') # Width
    
    config = [
        # Zone 1: High Temp Inlet (Bare Tubes)
        {'type': 'bare', 'name': 'Zone 1 (Bare)', 'width': W, 'tubes_deep': 8,
         'tube_od': cv.convert(1.0, 'in', 'm'), 
         'S_T': cv.convert(2.5, 'in', 'm'), 
         'S_L': cv.convert(2.0, 'in', 'm')},
         
        # Zone 2: Main Cooling (Finned Tubes)
        {'type': 'finned', 'name': 'Zone 2 (Finned)', 'width': W, 'tubes_deep': 30,
         'tube_od': cv.convert(0.75, 'in', 'm'), 
         'S_T':     cv.convert(1.5, 'in', 'm'), 
         'S_L':     cv.convert(1.25, 'in', 'm'),
         'fin_pitch':     cv.convert(1.0, 'in', 'm'), # Fins Per Inch
         'fin_thickness': cv.convert(0.012, 'in', 'm')
        }
    ]
    return config

def print_performance_report(hx):
    """Calculates and prints dimensions AND performance metrics."""
    print("\n" + "="*50)
    print("          HEAT EXCHANGER PERFORMANCE REPORT          ")
    print("="*50)
    
    # --- 1. GEOMETRY ---
    print("\n[GEOMETRY]")
    total_length = 0.0
    width = 0.0
    height = 0.0
    
    for i, zone in enumerate(hx.zones):
        z_len = 0.0
        if hasattr(zone, 'length'): 
            z_len = zone.length
        elif hasattr(zone, 'S_L') and hasattr(zone, 'n_cols'):
            z_len = zone.S_L * zone.n_cols
        
        total_length += z_len
        
        if i == 0:
            width = getattr(zone, 'width', 0.0)
            height = getattr(zone, 'height', 0.0)
            
        print(f"  Zone {i+1} ({zone.name}):")
        print(f"    > Depth: {z_len:.4f} m  ({cv.convert(z_len, 'm', 'in'):.2f} in)")
        if hasattr(zone, 'n_cols'):
            print(f"    > Rows:  {zone.n_cols}")

    print("-" * 30)
    print(f"  OVERALL SIZE: {cv.convert(width, 'm', 'in'):.1f}\" (W) x {cv.convert(height, 'm', 'in'):.1f}\" (H) x {cv.convert(total_length, 'm', 'in'):.1f}\" (D)")

    # --- 2. PERFORMANCE ---
    print("\n[PERFORMANCE]")
    
    # Extract States
    gas_in = hx.hot_stream.profile[0]
    gas_out = hx.hot_stream.profile[-1]
    cool_in = hx.cold_stream.profile[0]
    cool_out = hx.cold_stream.profile[-1]
    
    # Gas Side
    dt_gas = gas_in.T - gas_out.T
    dp_gas = gas_in.P - gas_out.P
    
    print(f"  GAS SIDE ({gas_in.fluid_string}):")
    print(f"    > Inlet T:  {cv.convert(gas_in.T, 'K', 'degC'):.1f} °C")
    print(f"    > Outlet T: {cv.convert(gas_out.T, 'K', 'degC'):.1f} °C")
    print(f"    > Delta T:  {dt_gas:.1f} K")
    print(f"    > Inlet P:  {cv.convert(gas_in.P, 'Pa', 'Torr'):.1f} Torr")
    print(f"    > Delta P:  {cv.convert(dp_gas, 'Pa', 'Torr'):.2f} Torr")
    
    # Coolant Side
    # Note: For Parallel flow, dP is not P_in - P_out (which is 0 in our code).
    # It is the average pressure drop across the parallel tubes.
    dp_cool_total = 0.0
    for zone in hx.zones:
        # Sum of 'dP_cool_Pa' in zone results is currently SUM of all tubes (legacy series assumption).
        # For Parallel, dP_zone = sum_dP / n_rows (Average drop per row).
        # Assuming zones are in SERIES with each other.
        if hasattr(zone, 'results') and 'dP_cool_Pa' in zone.results:
            n_rows = zone.n_cols if hasattr(zone, 'n_cols') and zone.n_cols > 0 else 1
            dp_zone_parallel = zone.results['dP_cool_Pa'] / n_rows
            dp_cool_total += dp_zone_parallel
            
    dt_cool = cool_out.T - cool_in.T
    
    print(f"  COOLANT SIDE ({cool_in.fluid_string}):")
    print(f"    > Inlet T:  {cv.convert(cool_in.T, 'K', 'degC'):.1f} °C")
    print(f"    > Outlet T: {cv.convert(cool_out.T, 'K', 'degC'):.1f} °C")
    print(f"    > Delta T:  {dt_cool:.1f} K")
    print(f"    > Delta P:  {cv.convert(dp_cool_total, 'Pa', 'psi'):.2f} psi (Estimated Pump Head)")
    
    print("="*50 + "\n")

def run_design_simulation(hot_in, cold_in, config):
    print("--- Running Design Simulation ---")
    print(f"  > Gas: {hot_in.fluid_string} @ {cv.convert(hot_in.T, 'K', 'degC'):.1f} C, {cv.convert(hot_in.P, 'Pa', 'Torr'):.1f} Torr")
    print(f"  > Coolant: {cold_in.fluid_string} @ {cv.convert(cold_in.T, 'K', 'degC'):.1f} C")

    # 1. Physics
    physics = ModifiedGrimisonModel(method="hammock")
    pressure_physics = GunterShawModel(use_correction=True)
    
    # 2. Build
    builder = HXBuilder("Design_v1", physics, pressure_model=pressure_physics)
    builder.add_zones_from_config(config)
    hx = builder.build(hot_in, cold_in)
    
    # 3. Solve
    hx.solve()
    
    # Report
    print_performance_report(hx)
    
    # 4. Extract Data
    rows = [0]
    temps_c = [cv.convert(hot_in.T, 'K', 'degC')]
    pressures_torr = [cv.convert(hot_in.P, 'Pa', 'Torr')]
    reynolds = [0]
    wall_temps_c = [cv.convert(cold_in.T, 'K', 'degC')]
    cool_temps_c = [cv.convert(cold_in.T, 'K', 'degC')]
    
    current_row = 0
    profile_idx = 1
    
    for zone in hx.zones:
        z_re = getattr(zone, 'history', {}).get('Re_g', [])
        z_Tw = getattr(zone, 'history', {}).get('T_wall', [])
        z_Tc = getattr(zone, 'history', {}).get('T_cool', [])
        
        for i in range(zone.n_cols):
            if profile_idx < len(hx.hot_stream.profile):
                state = hx.hot_stream.profile[profile_idx]
                current_row += 1
                
                rows.append(current_row)
                temps_c.append(cv.convert(state.T, 'K', 'degC'))
                pressures_torr.append(cv.convert(state.P, 'Pa', 'Torr'))
                
                # Reynolds
                reynolds.append(z_re[i] if i < len(z_re) else 0.0)
                
                # Wall Temp
                val_tw = z_Tw[i] if i < len(z_Tw) else cv.convert(wall_temps_c[-1], 'degC', 'K')
                wall_temps_c.append(cv.convert(val_tw, 'K', 'degC'))
                
                # Coolant Temp
                val_tc = z_Tc[i] if i < len(z_Tc) else cv.convert(cool_temps_c[-1], 'degC', 'K')
                cool_temps_c.append(cv.convert(val_tc, 'K', 'degC'))
                
                profile_idx += 1
            else:
                break
                
    return rows, temps_c, pressures_torr, reynolds, wall_temps_c, cool_temps_c

def main():
    # --- 1. DESIGN INPUTS ---
    hot_in = FluidState(StreamType.GAS, 
                        T=cv.convert(1800, 'degC', 'K'),  
                        P=cv.convert(5, 'Torr', 'Pa'),   
                        m_dot=cv.convert(10.68, 'g/s', 'kg/s'),                        
                        fluid=Fluid.N2)                 
                        
    cold_in = FluidState(StreamType.COOLANT, 
                         T=cv.convert(80, 'degF', 'K'),   
                         P=cv.convert(50, 'psi', 'Pa'),  
                         m_dot=1.0,                      
                         fluid=Fluid.WATER)

    geometry = get_design_geometry()

    # --- 2. RUN ---
    rows, temps, pressures, re, wall, cool = run_design_simulation(hot_in, cold_in, geometry)

    # --- 3. DASHBOARD PLOT ---
    print("--- Generating Design Dashboard ---")
    fig, axes = plt.subplots(5, 1, figsize=(10, 18), sharex=True)
    ax1, ax2, ax3, ax4, ax5 = axes
    
    # Gas Temp (degC)
    ax1.plot(rows, temps, color='tab:red', linewidth=2)
    ax1.set_ylabel("Gas Temp (°C)")
    ax1.set_title("Design Performance: Gas Temperature Profile")
    ax1.grid(True, alpha=0.3)
    
    # Gas Pressure (Torr)
    ax2.plot(rows, pressures, color='tab:orange', linewidth=2)
    ax2.set_ylabel("Gas Pressure (Torr)")
    ax2.set_title("Gas Pressure Profile")
    ax2.grid(True, alpha=0.3)
    
    # Reynolds
    ax3.plot(rows, re, color='tab:green', linewidth=2)
    ax3.set_ylabel("Reynolds Number (-)")
    ax3.set_title("Gas Reynolds Number")
    ax3.grid(True, alpha=0.3)
    
    # Wall Temp (degC)
    ax4.plot(rows, wall, color='tab:purple', linewidth=2)
    ax4.set_ylabel("Wall Temp (°C)")
    ax4.set_title("Tube Wall Temperature")
    ax4.axhline(100, color='k', linestyle='--', alpha=0.5, label="Boiling Risk (100°C)")
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    
    # Coolant Temp (degC)
    ax5.plot(rows, cool, color='tab:blue', linewidth=2)
    ax5.set_ylabel("Coolant Temp (°C)")
    ax5.set_title("Coolant Temperature Rise")
    ax5.set_xlabel("Cumulative Row Number")
    ax5.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()