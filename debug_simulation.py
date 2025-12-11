import traceback
from utils import convert as cv
from src.fluids import FluidState, StreamType, Fluid
from src.builders import HXBuilder
from src.models import ModifiedGrimisonModel
from src.models.pressure import GunterShawModel
from src.zones import TubeBankZone

# Custom Zone that is LOUD about errors
class DebugZone(TubeBankZone):
    def solve(self, hot_state_in, cold_state_in):
        # 1. Setup
        print(f"\n--- DEBUG: Entering {self.name} ---")
        if not self.tube_centers: self.build_geometry()
        
        Tg, Pg = hot_state_in.T, hot_state_in.P
        Tc, Pc = cold_state_in.T, cold_state_in.P
        mdot_g, mdot_c = hot_state_in.m_dot, cold_state_in.m_dot
        
        hot_profile = []
        
        # 2. Manual Marching Loop (No Try/Except swallowing)
        for i in range(self.n_cols):
            print(f"  Row {i}: T_gas={Tg:.1f} K, P_gas={Pg:.1f} Pa")
            
            # A. Check Properties EXPLICITLY
            try:
                rho_g = self._get_prop('D', Tg, Pg, hot_state_in.fluid_string)
            except Exception as e:
                print(f"  [CRASH] CoolProp failed at Row {i}!")
                print(f"  State: T={Tg}, P={Pg}")
                print(f"  Error: {e}")
                traceback.print_exc()
                return hot_state_in, cold_state_in, [], [] # Stop hard

            # B. Physics (Simplified for Debug)
            # We just want to see where it breaks, so we run the full logic
            # by calling the parent logic? No, parent swallows errors.
            # We have to copy-paste the core logic or call a helper.
            # Let's trust the properties check above is the likely culprit.
            
            # Call the REAL logic but wrap it to catch the specific crash
            try:
                # We can't easily call super().solve() for just one row.
                # So we assume the crash happens in the Property lookup we just tested.
                # If we passed property lookup, let's run the rest of the loop logic manually.
                pass 
                # (Replicating full logic here is verbose, but let's see if properties fail first)
                
            except Exception:
                pass 

            # ... (Full logic replication is too long for a quick debug) ...
            # Instead, let's rely on the fact that we are injecting this class 
            # into the Builder, so we can override the behavior.
            
            # Better Plan: Use the Base Class logic but MONKEY PATCH the method
            # to remove the try/except block. 
            pass
        
        # Call original solve but we can't easily remove the try/except without rewriting.
        # So we will just run the original solve and assume the print statements in the 
        # DIAGNOSTIC script (below) will catch the state before it enters.
        
        return super().solve(hot_state_in, cold_state_in)

    def _get_prop(self, key, T, P, fluid):
        import CoolProp.CoolProp as cp
        return cp.PropsSI(key, 'T', T, 'P', P, fluid)

# Monkey Patching for Debug (Dangerous but effective)
# We redefine the solve method of TubeBankZone dynamically to print errors
def verbose_solve(self, hot_state_in, cold_state_in):
    # This is a stripped down version of the real solve that crashes LOUDLY
    if not self.tube_centers: self.build_geometry()
    Tg, Pg = hot_state_in.T, hot_state_in.P
    Tc, Pc = cold_state_in.T, cold_state_in.P
    mdot_g = hot_state_in.m_dot
    
    # Imports inside function for patch safety
    import math
    import CoolProp.CoolProp as cp
    from src import correlations as corr 
    
    hot_profile = []
    
    for i in range(self.n_cols):
        print(f"[{self.name} Row {i}] T={Tg:.2f} K, P={Pg:.2f} Pa")
        
        # 1. CRITICAL PROPERTY CHECK
        try:
            rho_g = cp.PropsSI('D', 'T', Tg, 'P', Pg, hot_state_in.fluid_string)
            mu_g  = cp.PropsSI('V', 'T', Tg, 'P', Pg, hot_state_in.fluid_string)
        except ValueError as e:
            print(f"\n!!! CRASH TRIGGERED AT ROW {i} !!!")
            print(f"Cause: CoolProp Property Failure")
            print(f"State: T={Tg}, P={Pg}")
            print(f"Error Message: {e}")
            raise e # Crash the script so user sees it

        # 2. Physics (Condensed)
        # We need to update Tg and Pg to proceed to next row
        # We will use the model to get dP and Q
        # ... (This part relies on the model being correct) ...
        
        # For the sake of the debug, we call the MODEL explicitly
        # to see if the MODEL crashes
        try:
            # Fake params to test model
            # We assume geometry is set on self
            model_params = {
                'eps_por': self.eps_por, 'T': Tg, 'rho': rho_g, 'mu': mu_g, 
                'M_gas': 28.0, 'D': self.tube_dia, 'S_T': self.S_T, 'S_L': self.S_L,
                'N_rows': self.n_cols, 'Pr_wall': 0.7, 'T_wall': Tc, 'T_cool': Tc
            }
            # Test Heat Transfer Model
            Nu = self.model.calculate_Nu(1000, 0.7, **model_params)
            
            # Test Pressure Model
            dP_params = {
                'rho': rho_g, 'mu': mu_g, 'mu_wall': mu_g, 'm_dot': mdot_g,
                'S_T': self.S_T, 'S_L': self.S_L, 'D': self.tube_dia,
                'L_flow': self.S_L, 'A_front': self.width * self.height
            }
            dP = self.pressure_model.calculate_dP(**dP_params)
            
            # Update for next step (Approximation for debug loop)
            # We aren't doing the full energy balance here, just checking for crashes
            # But we need P to drop to see if it hits 0
            Pg -= dP
            
            # Fake Temp drop to progress
            Tg -= 10.0 
            
        except Exception as e:
            print(f"\n!!! CRASH IN PHYSICS MODEL AT ROW {i} !!!")
            print(f"Error: {e}")
            raise e

    return hot_state_in, cold_state_in, [], []

def run_debug():
    # 1. Apply Patch
    TubeBankZone.solve = verbose_solve
    print("--- DEBUG MODE: TubeBankZone.solve patched ---")
    
    # 2. Setup Inputs
    hot_in = FluidState(StreamType.GAS, 
                        T=cv.convert(5050, 'degF', 'K'), 
                        P=10135.0, m_dot=1.288, fluid=Fluid.N2)
    cold_in = FluidState(StreamType.COOLANT, 
                         T=297.2, P=613600.0, m_dot=608.0, fluid=Fluid.WATER)

    # 3. Build & Run (Validation Geometry)
    W = cv.convert(48, 'in', 'm')
    config = [
        {'type': 'bare', 'name': 'Bank 0', 'width': W, 'tubes_deep': 4,
         'tube_od': cv.convert(2.399, 'in', 'm'), 'S_T': cv.convert(4.75, 'in', 'm'), 'S_L': cv.convert(2.5, 'in', 'm')},
        {'type': 'bare', 'name': 'Bank 1', 'width': W, 'tubes_deep': 26,
         'tube_od': cv.convert(1.518, 'in', 'm'), 'S_T': cv.convert(4.4375, 'in', 'm'), 'S_L': cv.convert(1.9060, 'in', 'm')}
    ]
    
    physics = ModifiedGrimisonModel(method="hammock")
    pressure = GunterShawModel(use_correction=False) # Ensure this is False!
    
    builder = HXBuilder("Debug_Run", physics, pressure_model=pressure)
    builder.add_zones_from_config(config)
    
    print("--- Starting Solve ---")
    hx = builder.build(hot_in, cold_in)
    hx.solve()

if __name__ == "__main__":
    run_debug()