from utils import convert as cv
from src.fluids import FluidState, StreamType, Fluid
from src.builders import HXBuilder
from src.models import ModifiedGrimisonModel
from src.models.pressure import GunterShawModel
from src.zones import TubeBankZone

def run_diagnostic():
    print("--- PRESSURE DIAGNOSTIC RUN ---")
    
    # 1. Setup Inputs (Same as Validation)
    hot_in = FluidState(StreamType.GAS, 
                        T=cv.convert(5050, 'degF', 'K'), 
                        P=10135.0, # 1.47 psia
                        m_dot=1.288, 
                        fluid=Fluid.N2)
    
    cold_in = FluidState(StreamType.COOLANT, 
                         T=297.2, P=613600.0, m_dot=608.0, fluid=Fluid.WATER)

    # 2. Build Hardware MANUALLY to inject UNCORRECTED pressure model
    # We will replicate the same geometry but force correction=1.0
    
    physics = ModifiedGrimisonModel(method="hammock")
    
    # Toggle this to False to see if it fixes the crash
    USE_CORRECTION = False 
    pressure_model = GunterShawModel(use_correction=USE_CORRECTION)
    
    print(f"Testing with Boucher-Lapple Correction: {USE_CORRECTION} (Factor={pressure_model.correction})")

    # Recreate Bank 0 & 1 (Where it crashes)
    W = cv.convert(48, 'in', 'm')
    
    # Bank 0
    z0 = TubeBankZone(
        name="Bank 0", height=W, width=W, n_cols=4,
        tube_dia=cv.convert(2.399, 'in', 'm'), R_p=1.5,
        model=physics, pressure_model=pressure_model
    )
    # Bank 0 Overrides
    z0.S_T = cv.convert(4.75, 'in', 'm')
    z0.S_L = cv.convert(2.5, 'in', 'm')

    # Bank 1 (The crash site)
    z1 = TubeBankZone(
        name="Bank 1", height=W, width=W, n_cols=26,
        tube_dia=cv.convert(1.518, 'in', 'm'), R_p=1.5,
        model=physics, pressure_model=pressure_model
    )
    z1.S_T = cv.convert(4.4375, 'in', 'm')
    z1.S_L = cv.convert(1.9060, 'in', 'm')
    
    # 3. Solve and Track Pressure
    current_hot = hot_in
    current_cold = cold_in
    
    zones = [z0, z1]
    
    for z in zones:
        print(f"\nSolving {z.name}...")
        # Manually march to print pressure
        # (This duplicates logic from zones.py but adds print)
        # Actually, let's just use the zone's solve and inspect the profile
        hot_out, _, profile, _ = z.solve(current_hot, current_cold)
        
        # Print last few steps
        print(f"  > Inlet P:  {profile[0].P:.1f} Pa")
        print(f"  > Outlet P: {hot_out.P:.1f} Pa")
        
        if hot_out.P < 100:
            print("  [FAIL] Pressure crashed near zero.")
        else:
            print("  [PASS] Zone survived.")
            
        current_hot = hot_out

if __name__ == "__main__":
    run_diagnostic()