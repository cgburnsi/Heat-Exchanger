import pandas as pd
import itertools
from utils import convert as cv
from src.fluids import FluidState, StreamType, Fluid
from src.models import TariqModel
from src.builders import HXBuilder

def run_parametric_study():
    print("--- STARTING PARAMETRIC STUDY ---")
    
    # 1. Base Conditions
    model = TariqModel()
    
    hot_in = FluidState(StreamType.GAS, 
                        T=cv.convert(1900, 'degC', 'K'), 
                        P=cv.convert(5, 'Torr', 'Pa'), 
                        m_dot=cv.convert(10.68, 'g/s', 'kg/s'), 
                        fluid=Fluid.N2)
    
    cold_in = FluidState(StreamType.COOLANT, 
                         T=cv.convert(80, 'degF', 'K'), 
                         P=cv.convert(50, 'psi', 'Pa'), 
                         m_dot=cv.convert(1.0, 'lb/s', 'kg/s'), 
                         fluid=Fluid.WATER)

    # 2. Define Variables to Sweep
    #    Note: Keys here are for your record-keeping in the CSV.
    sweep_vars = {
        'tube_od_in': [0.75, 1.0, 1.25],  # Inches
        'fpi':        [4.0, 8.0, 10.0],   # Fins per inch
        'n_rows':     [8, 10, 12, 14]     # Depth of Zone 2
    }

    # Generate combinations
    keys, values = zip(*sweep_vars.items())
    combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    
    results = []

    # 3. Loop
    print(f"Total Runs: {len(combinations)}")
    
    for i, params in enumerate(combinations):
        if i % 5 == 0: print(f"  Running case {i+1}/{len(combinations)}...")
        
        # --- PREPARE INPUTS (Convert to SI here) ---
        tube_od_m = cv.convert(params['tube_od_in'], 'in', 'm')
        fin_pitch_m = cv.convert(1.0 / params['fpi'], 'in', 'm')
        fin_thick_m = cv.convert(0.012, 'in', 'm')
        width_m = cv.convert(16, 'in', 'm')
        
        # --- CONFIGURE HARDWARE ---
        config = [
            # Zone 0: Inlet Pipe
            {
                'type': 'pipe', 
                'name': 'Inlet',
                'length':   cv.convert(10, 'ft', 'm'), 
                'diameter': cv.convert(12, 'in', 'm')
            },
            # Zone 1: Dense Section (Fixed depth=2)
            {
                'type': 'finned', 
                'name': 'Z1', 
                'width': width_m, 
                'tubes_deep': 2, 
                'tube_od': tube_od_m,
                'fin_pitch': cv.convert(1.0/4.0, 'in', 'm'), # Fixed 4 FPI
                'fin_thickness': fin_thick_m,
                'Rp': 1.5
            },
            # Zone 2: Bulk Section (Variable depth & FPI)
            {
                'type': 'finned', 
                'name': 'Z2', 
                'width': width_m, 
                'tubes_deep': params['n_rows'], 
                'tube_od': tube_od_m, 
                'fin_pitch': fin_pitch_m,
                'fin_thickness': fin_thick_m,
                'Rp': 2.0
            }
        ]
        
        # --- BUILD & SOLVE ---
        builder = HXBuilder(f"Run_{i}", model)
        builder.add_zones_from_config(config)
        hx = builder.build(hot_in, cold_in)
        hx.solve()
        
        # --- CAPTURE RESULT ---
        # Calculate totals relative to inlet (Assembly Level)
        Q_tot = (hot_in.h - hx.hot_out.h) * hot_in.m_dot # Watts
        dP_tot = hot_in.P - hx.hot_out.P                 # Pascals
        
        row = {
            **params, # Input variables
            'Q_total_kW': Q_tot / 1000.0,
            'T_out_K': hx.hot_out.T,
            'T_out_C': cv.convert(hx.hot_out.T, 'K', 'degC'),
            'dP_gas_Pa': dP_tot,
            'dP_gas_Torr': cv.convert(dP_tot, 'Pa', 'Torr')
        }
        results.append(row)

    # 4. Save
    df = pd.DataFrame(results)
    df.to_csv("optimization_results.csv", index=False)
    print("\n--- DONE. Saved to optimization_results.csv ---")
    
    # 5. Show Top 5 performers (Highest Heat Transfer)
    print("\nTop 5 Designs by Heat Transfer:")
    print(df.sort_values(by='Q_total_kW', ascending=False).head(5))

if __name__ == "__main__":
    run_parametric_study()