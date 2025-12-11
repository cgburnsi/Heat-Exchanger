import math

class PressureDropModel:
    """Abstract Base Class for Pressure Drop Correlations."""
    def calculate_dP(self, **kwargs):
        raise NotImplementedError

class GunterShawModel(PressureDropModel):
    """
    Gunter-Shaw (1945) Pressure Drop Model.
    Includes the Boucher & Lapple correction (1.75x) recommended by Hammock 
    for wide spacings and high-enthalpy flows.
    
    Reference: Hammock Paper, Equations 35-38.
    """
    def __init__(self, use_correction=True):
        # Boucher & Lapple correction factor of 1.75 
        self.correction = 1.75 if use_correction else 1.0

    def calculate_dP(self, **kwargs):
        """
        Calculates pressure drop using Gunter-Shaw correlation.
        
        Required kwargs:
          - rho: Gas Density [kg/m^3]
          - mu: Gas Viscosity [Pa-s]
          - mu_wall: Gas Viscosity at Wall Temp [Pa-s]
          - m_dot: Mass Flow Rate [kg/s]
          - S_T: Transverse Pitch [m]
          - S_L: Longitudinal Pitch [m]
          - D: Tube Diameter [m]
          - L_flow: Length of flow path (depth of bank) [m]
          - A_front: Frontal Area (Width * Height) [m^2]
        """
        try:
            rho = kwargs['rho']
            mu = kwargs['mu']
            # Default to bulk viscosity if wall not provided
            mu_w = kwargs.get('mu_wall', mu) 
            m_dot = kwargs['m_dot']
            S_T = kwargs['S_T']
            S_L = kwargs['S_L']
            D = kwargs['D']
            L_flow = kwargs['L_flow']
            A_front = kwargs['A_front']
        except KeyError as e:
            raise ValueError(f"GunterShawModel missing parameter: {e}")

        # 1. Volumetric Hydraulic Diameter (Dv) - Eq 38 [cite: 610]
        # Dv = (4/pi) * (ST * SL / D) - D
        D_v = (4.0 / math.pi) * (S_T * S_L / D) - D
        
        # 2. Mass Flux (G) calculation
        # Hammock implies G based on minimum flow area (standard for these correlations).
        # Calculate sigma (flow restriction ratio)
        sigma = (S_T - D) / S_T
        A_min = A_front * sigma
        G = m_dot / A_min
        
        # 3. Volumetric Reynolds Number (Re_v)
        # Note: Gunter-Shaw friction factor uses this Re, not the standard Re_D.
        if mu <= 0: return 0.0
        Re_v = (G * D_v) / mu
        
        # 4. Friction Factor (f/2) - Eq 37 [cite: 605]
        # Transition occurs at Re = 200 [cite: 604, 606]
        if Re_v <= 200:
            f_2 = 90.0 / Re_v
        else:
            f_2 = 0.96 * (Re_v**-0.145)
            
        # 5. Calculate Pressure Drop (Eq 36) 
        # dP = (f/2) * (G^2 * L / (Dv * rho)) * (mu_w/mu)^0.14 * (Dv/ST)^0.4 * (SL/ST)^0.6
        # Note: Eq 36 has a (1/g) term which is 1.0 in SI units.
        
        # Term 1: Dynamic / Geometric
        term_dyn = (G**2 * L_flow) / (D_v * rho)
        
        # Term 2: Viscosity Ratio (Property variation)
        term_visc = (mu_w / mu)**0.14
        
        # Term 3: Geometry Ratios
        term_geom = ((D_v / S_T)**0.4) * ((S_L / S_T)**0.6)
        
        dP_raw = f_2 * term_dyn * term_visc * term_geom
        
        # 6. Apply Boucher-Lapple Correction 
        return dP_raw * self.correction