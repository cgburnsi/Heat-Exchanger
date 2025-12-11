import traceback
import math
import CoolProp.CoolProp as cp
from utils import convert as cv
from src.fluids import FluidState, StreamType, Fluid
from src.models import ModifiedGrimisonModel
from src.models.pressure import GunterShawModel
from src import correlations as corr

# ==============================================================================
# MANUAL ZONE SOLVER (Bypasses src/zones.py to guarantee no error swallowing)
# ==============================================================================
def solve_zone_manually(name, n_rows, hot_state, cold_state, geometry, physics, pressure_model):
    print(f"\n--- Solving {name} ({n_rows} rows) ---")
    
    Tg, Pg = hot_state.T, hot_state.P
    Tc, Pc = cold_state.T, cold_state.P
    mdot_g = hot_state.m_dot
    
    # Geometry unpacking
    W, H = geometry['W'], geometry['H']
    D, ST, SL = geometry['D'], geometry['S_T'], geometry['S_L']
    
    # Derived Geometry
    A_front = W * H
    sigma = (ST - D) / ST
    A_min = A_front * sigma
    
    for i in range(n_rows):
        print(f"  Row {i:02d}: T={Tg:.2f} K, P={Pg:.2f} Pa", end=" ... ")
        
        try:
            # 1. Properties
            rho_g = cp.PropsSI('D', 'T', Tg, 'P', Pg, hot_state.fluid_string)
            mu_g  = cp.PropsSI('V', 'T', Tg, 'P', Pg, hot_state.fluid_string)
            cp_g  = cp.PropsSI('C', 'T', Tg, 'P', Pg, hot_state.fluid_string)
            k_g   = cp.PropsSI('L', 'T', Tg, 'P', Pg, hot_state.fluid_string)
            pr_g  = cp.PropsSI('Prandtl', 'T', Tg, 'P', Pg, hot_state.fluid_string)
            
            # Wall Prop
            mu_w  = cp.PropsSI('V', 'T', Tc, 'P', Pg, hot_state.fluid_string)

            # 2. Physics - Heat Transfer
            # Calculate Re
            u_max = mdot_g / (rho_g * A_min)
            Re_t = (rho_g * u_max * D) / mu_g
            
            # Calculate Nu
            model_params = {
                'eps_por': 0.5, # Dummy
                'T': Tg, 'rho': rho_g, 'mu': mu_g, 
                'D': D, 'S_T': ST, 'S_L': SL,
                'N_rows': n_rows, 'Pr_wall': pr_g, 'T_wall': Tc, 'T_cool': Tc
            }
            Nu = physics.calculate_Nu(Re_t, pr_g, **model_params)
            h_t = Nu * k_g / D
            
            # 3. Physics - Pressure Drop
            dP_params = {
                'rho': rho_g, 'mu': mu_g, 'mu_wall': mu_w, 'm_dot': mdot_g,
                'S_T': ST, 'S_L': SL, 'D': D, 'L_flow': SL, 'A_front': A_front
            }
            dP = pressure_model.calculate_dP(**dP_params)
            
            # 4. Energy Balance (e-NTU)
            # Area per row
            A_surf = math.pi * D * W # One row surface area
            
            UA = h_t * A_surf # Neglecting wall/water resistance for debug
            C_g = mdot_g * cp_g
            NTU = UA / C_g
            eps = 1.0 - math.exp(-NTU)
            Q = eps * C_g * (Tg - Tc)
            
            # Update
            Tg -= Q / C_g
            Pg -= dP
            
            print(f"OK (Q={Q/1000:.2f} kW, dP={dP:.2f} Pa)")
            
        except Exception:
            print("\n  [CRASH detected!]")
            traceback.print_exc()
            return None # Stop
            
    # Return updated state
    hot_state.T = Tg
    hot_state.P = Pg
    return hot_state

def main():
    # 1. Inputs
    hot_in = FluidState(StreamType.GAS, 
                        T=cv.convert(5050, 'degF', 'K'), 
                        P=10135.0, m_dot=1.288, fluid=Fluid.N2)
    cold_in = FluidState(StreamType.COOLANT, 
                         T=297.2, P=613600.0, m_dot=608.0, fluid=Fluid.WATER)

    W = cv.convert(48, 'in', 'm')
    
    # 2. Physics
    physics = ModifiedGrimisonModel(method="hammock")
    pressure = GunterShawModel(use_correction=False)

    # 3. Run Bank 0
    geo0 = {
        'W': W, 'H': W, 
        'D': cv.convert(2.399, 'in', 'm'),
        'S_T': cv.convert(4.75, 'in', 'm'),
        'S_L': cv.convert(2.5, 'in', 'm')
    }
    hot_out = solve_zone_manually("Bank 0", 4, hot_in, cold_in, geo0, physics, pressure)
    
    if hot_out:
        # 4. Run Bank 1 (Where it fails)
        geo1 = {
            'W': W, 'H': W, 
            'D': cv.convert(1.518, 'in', 'm'),
            'S_T': cv.convert(4.4375, 'in', 'm'),
            'S_L': cv.convert(1.9060, 'in', 'm')
        }
        solve_zone_manually("Bank 1", 26, hot_out, cold_in, geo1, physics, pressure)

if __name__ == "__main__":
    main()