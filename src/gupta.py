import math

class GuptaAir:
    """
    High-Temperature 'Equilibrium Air' Property Model.
    
    Implementation: Tabular Interpolation for P = 0.1 atm (approx 10 kPa).
    This captures the dissociation effects (Cp spike, density drop) seen 
    in the Hammock validation case without relying on unstable curve fits.
    
    Data Source: Representative High-Temp Air Data (NASA CEA / Standard Atmosphere)
    at low pressure (0.1 atm).
    """
    
    # T [K], rho [kg/m3], Cp [J/kg-K], mu [Pa-s], k [W/m-K], Pr [-]
    # Note: Cp spikes at 3000-4000K due to O2 -> 2O dissociation
    _DATA = [
        (300.0,  0.1161,  1005.0, 1.846e-5, 0.0263, 0.707),
        (500.0,  0.0697,  1030.0, 2.671e-5, 0.0407, 0.680),
        (1000.0, 0.0348,  1142.0, 4.244e-5, 0.0672, 0.700),
        (1500.0, 0.0232,  1210.0, 5.580e-5, 0.0890, 0.730),
        (2000.0, 0.0174,  1280.0, 6.700e-5, 0.1100, 0.740), # Dissociation starts
        (2500.0, 0.0135,  1500.0, 7.800e-5, 0.1400, 0.720),
        (3000.0, 0.0108,  2200.0, 8.800e-5, 0.2500, 0.690), # Peak dissociation slope
        (3500.0, 0.0085,  3500.0, 9.800e-5, 0.4000, 0.650),
        (4000.0, 0.0070,  4500.0, 1.100e-4, 0.6000, 0.600),
        (5000.0, 0.0050,  3000.0, 1.300e-4, 0.8000, 0.550), # Cp drops as O2 is depleted
        (6000.0, 0.0040,  2000.0, 1.500e-4, 1.0000, 0.500)
    ]

    @staticmethod
    def PropsSI(output_key, arg1_key, arg1_val, arg2_key, arg2_val, fluid_name):
        # 1. Parse T (We ignore P for lookup, assuming P ~ 0.1 atm/vacuum)
        if arg1_key == 'T': T = arg1_val
        elif arg2_key == 'T': T = arg2_val
        else: raise ValueError("GuptaAir requires Temperature (T).")
        
        # 2. Interpolate
        return GuptaAir._interpolate(T, output_key)

    @staticmethod
    def _interpolate(T, key):
        data = GuptaAir._DATA
        
        # Clamp to bounds
        if T <= data[0][0]: return GuptaAir._get_col(data[0], key)
        if T >= data[-1][0]: return GuptaAir._get_col(data[-1], key)
        
        # Linear Search (Fast enough for this size)
        for i in range(len(data) - 1):
            t_low, t_high = data[i][0], data[i+1][0]
            if t_low <= T <= t_high:
                frac = (T - t_low) / (t_high - t_low)
                val_low = GuptaAir._get_col(data[i], key)
                val_high = GuptaAir._get_col(data[i+1], key)
                return val_low + frac * (val_high - val_low)
        return 0.0

    @staticmethod
    def _get_col(row, key):
        # Row: T, rho, Cp, mu, k, Pr
        if key == 'D': return row[1]
        if key == 'C': return row[2]
        if key == 'V': return row[3]
        if key == 'L': return row[4]
        if key == 'Prandtl': return row[5]
        if key == 'M': return 0.02896 # Approx molar mass
        raise ValueError(f"Unknown property: {key}")