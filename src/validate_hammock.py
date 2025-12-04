import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import CoolProp.CoolProp as cp
from utils import convert as cv
from src.fluids import FluidState, StreamType, Fluid, FluidStream
from src.assembly import HeatExchanger
from src.zones import TubeBankZone
from src.models import GrimisonModel # <--- Import the new model
from src.models import ModifiedGrimisonModel

# ==============================================================================
# REFERENCE DATA (Your Digitized Points)
# ==============================================================================
REF_DATA = {
    "Row Number": [0, 2, 4, 6, 8, 10, 15, 20, 25, 30, 32, 35, 40, 50, 60, 80],
    "Modified Grimison": [5050, 4200, 3600, 3100, 2750, 2400, 1700, 1250, 950, 750, 600, 250, 120, 80, 50, 50],
    "Zhukauskas": [4900, 3900, 3200, 2800, 2400, 2100, 1500, 1100, 850, 650, 500, 200, 100, 60, 50, 50],
    "Kays & London": [4800, 3600, 2950, 2550, 2250, 2000, 1450, 1100, 800, 600, 450, 180, 90, 60, 50, 50],
    "Original Grimison": [5000, 3200, 1800, 1400, 1100, 900, 500, 350, 250, 150, 100, 80, 50, 20, 20, 20]
}

def plot_comparison(hx, ref_data):
    df = pd.DataFrame(ref_data)
    
    plt.figure(figsize=(12, 8))
    
    # 1. Plot Reference Lines
    plt.plot(df["Row Number"], df["Modified Grimison"], '--', label="Ref: Mod. Grimison", color='red', alpha=0.4, linewidth=2)
    plt.plot(df["Row Number"], df["Zhukauskas"], '--', label="Ref: Zhukauskas", color='green', alpha=0.4)
    plt.plot(df["Row Number"], df["Original Grimison"], '--', label="Ref: Orig. Grimison", color='purple', alpha=0.4)

    # 2. Process Simulation Data
    # We need to map the cumulative column count to x-axis
    sim_T_K = []
    sim_rows = []
    
    current_row = 0
    # Get inlet point
    sim_T_K.append(hx.hot_stream.profile[0].T)
    sim_rows.append(0)
    
    # Loop through history to find zone boundaries vs columns
    # The profile list has (N_cols_total + 1) entries
    # We need to be careful matching them to rows if n_rows varies per zone
    # Simplified: We assume the profile index roughly maps to Row Number for this validation case
    # because we set up the zones to be 1 column = 1 row depth roughly?
    # Actually, TubeBankZone solves by *Column*, where N_cols is the depth.
    
    # Let's rebuild the x-axis based on the zone configuration
    total_rows = 0
    profile_idx = 1 # Start after inlet
    
    for zone in hx.zones:
        # For each column in this zone...
        for _ in range(zone.n_cols):
            # Access the state at the exit of this column
            if profile_idx < len(hx.hot_stream.profile):
                T_val = hx.hot_stream.profile[profile_idx].T
                
                # In TubeBankZone, "n_cols" is the number of rows deep in flow direction
                total_rows += 1 
                
                sim_T_K.append(T_val)
                sim_rows.append(total_rows)
                profile_idx += 1

    # Convert K -> F
    sim_T_F = [(t - 273.15) * 1.8 + 32.0 for t in sim_T_K]
    
    # 3. Plot Simulation
    plt.plot(sim_rows, sim_T_F, 'k-', linewidth=3, label="THIS SIMULATION (Hammock Poly)")
    
    plt.title("Validation: Gas Temperature Profile", fontsize=16, fontweight='bold')
    plt.xlabel("Row Number", fontsize=14)
    plt.ylabel("Temperature (°F)", fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 85)
    plt.ylim(0, 6000)
    plt.legend(fontsize=12)
    plt.show()

def run_validation():
    print("--- RUNNING HAMMOCK VALIDATION ---")

    # 1. Inputs (Test Point 2.84 lbm/s)
    m_dot_g = 1.288         # kg/s
    P_g     = 10135.0       # Pa (1.47 psia)
    T_cool  = 297.2         # K
    P_cool  = 613600.0      # Pa
    m_dot_c = 608.0         # kg/s
    
    # Start Temp (Match Graph 5050 F)
    T_gas = cv.convert(5050, 'degF', 'K') 

    # 2. Geometry Config
    # Note: N_rows here is the "depth" (n_cols in our code)
    zones_config = [
        {'name': 'Bank 0', 'D_out': 2.399, 'S_T': 4.75, 'S_L': 2.1875, 'N_rows': 4},
        {'name': 'Bank 1', 'D_out': 1.518, 'S_T': 4.4375, 'S_L': 1.9060, 'N_rows': 26}, # Adjusted to match x-axis spacing
        {'name': 'Bank 2', 'D_out': 1.518, 'S_T': 4.4375, 'S_L': 1.9060, 'N_rows': 2},
        {'name': 'Bank 3', 'D_out': 1.518, 'S_T': 4.4375, 'S_L': 1.9060, 'N_rows': 2},
        {'name': 'Bank 4', 'D_out': 0.625, 'S_T': 2.25, 'S_L': 0.94, 'N_rows': 46}, 
    ]
    
    H_duct = cv.convert(48, 'in', 'm')
    W_duct = cv.convert(48, 'in', 'm')

    # 3. Setup Assembly
    hot_in = FluidState(StreamType.GAS, T_gas, P_g, m_dot_g, Fluid.N2)
    cold_in = FluidState(StreamType.COOLANT, T_cool, P_cool, m_dot_c, Fluid.WATER)
    
    hx = HeatExchanger("Validation", FluidStream(hot_in), FluidStream(cold_in))
    
    # 4. Configure Zones with NEW MODEL
    # Use the polynomial method ("hammock")
    #hammock_physics = GrimisonModel(method="hammock")
    hammock_physics = ModifiedGrimisonModel(method="hammock")
    
    for z_conf in zones_config:
        D_t = cv.convert(z_conf['D_out'], 'in', 'm')
        S_T = cv.convert(z_conf['S_T'], 'in', 'm')
        S_L = cv.convert(z_conf['S_L'], 'in', 'm')
        Rp = S_T / D_t
        
        zone = TubeBankZone(
            name=z_conf['name'],
            height=H_duct, width=W_duct,
            tube_dia=D_t, R_p=Rp, 
            n_cols=z_conf['N_rows'], # Depth
            stagger=True,
            model=hammock_physics # <--- INJECT THE NEW MODEL HERE
        )
        # Force geometry overrides for exact match
        zone.S_T = S_T
        zone.S_L = S_L
        zone.eps_por = 1.0 - ((np.pi/4.0)*(D_t**2)) / (S_T * S_L)
        
        hx.add_zone(zone)
        
    hx.solve()
    
    # 5. Plot
    plot_comparison(hx, REF_DATA)

if __name__ == "__main__":
    run_validation()