import math

def calc_Re(rho, u, L_char, mu):
    """
    General Reynolds number calculation.
    L_char: Characteristic length (Tube diameter for banks, Hydraulic diam for ducts)
    """
    if mu <= 0: return 0.0
    return rho * u * L_char / mu

def calc_Nu_Tariq(Re, Pr, eps_por, T, rho, mu, M_gas, L_char):
    """
    Tariq et al. correlation for staggered tube banks with rarefied-gas correction.
    """
    k_B = 1.380649e-23      # Boltzmann constant [J/K]
    N_A = 6.02214076e23     # Avogadro's number [1/mol]

    # Convert molar mass [kg/mol] -> molecular mass [kg]
    m_molecule = M_gas / N_A

    # Knudsen number from kinetic theory
    gas_term = math.sqrt((math.pi * m_molecule) / (2.0 * k_B * T))
    Kn = (mu / (rho * L_char)) * gas_term

    # Coefficients based on porosity
    c1 = 3.12 - 0.16 * math.exp(3.0 * eps_por)
    c2 = 3.45 - 3.0 * math.exp(-3.45 * eps_por)

    Re_safe = max(Re, 1.01)
    ln_Re = math.log(Re_safe)

    term1 = (0.48 - 0.2 * eps_por)
    term2 = eps_por / (1.0 - eps_por)
    term3 = ln_Re**c1
    term4 = Pr

    numerator = term1 * term3 * term4 / term2
    denominator = 1.0 + 0.1 * (ln_Re**c2) * Kn

    return numerator / denominator

def calc_friction_SwameeJain(Re, rel_roughness):
    """
    Explicit approximation of Colebrook-White friction factor.
    rel_roughness = epsilon / Diameter
    """
    if Re < 2300:
        return 64.0 / max(Re, 1.0)
    else:
        # Swamee-Jain
        term = (rel_roughness / 3.7) + (5.74 / (Re**0.9))
        return 0.25 / (math.log10(term))**2

def calc_Nu_Gnielinski(Re, Pr, f, D, L):
    """
    Gnielinski correlation for internal pipe flow (Turbulent/Transition).
    """
    if Re < 2300: 
        return 4.36 # Laminar, constant heat flux assumption
    
    f_8 = f / 8.0
    numerator = f_8 * (Re - 1000.0) * Pr
    denominator = 1.0 + 12.7 * (Pr**(2/3) - 1.0) * math.sqrt(f_8)
    
    # Entry length correction
    correction = 1.0 + (L / D)**(-0.7)
    
    return (numerator / denominator) * correction

def calc_Eu_HEDH(Re_t, R_p, correction_factor=True):
    """
    Calculates the Euler number (Eu) per row for staggered banks.
    Based on HEDH / Zukauskas with optional custom correction.
    """
    # Clamp Re to avoid division by zero errors in power laws
    Re = max(Re_t, 7.0) 
    
    # 1. Base Eu_HEDH (Zukauskas)
    if Re < 100:
        f = (3.72 / (Re**0.77)) * (1.0 + 0.5 / (R_p - 1.0))
        Eu_base = f / 2.0
    elif Re < 1000:
        f = (1.18 / (Re**0.42)) * (1.0 + 0.5 / (R_p - 1.0))
        Eu_base = f / 2.0
    else: 
        f = (0.32 / (Re**0.16)) * (1.0 + 0.5 / (R_p - 1.0))
        Eu_base = f / 2.0
        
    # 2. Apply Experimental Correction
    if correction_factor:
        corr = 3.2326 * (Re ** -0.2084)
        return Eu_base * corr
    
    return Eu_base

def calc_dP_gas_column(Eu, rho, u_max, N_rows):
    """
    Calculates gas pressure drop for a specific number of rows.
    """
    dynamic_head = 0.5 * rho * (u_max**2)
    return Eu * N_rows * dynamic_head

def calc_dP_coolant_tube(f, rho, u_avg, D, L):
    """
    Darcy-Weisbach equation for internal tube flow.
    """
    return f * (L / D) * 0.5 * rho * (u_avg**2)

# --- NEW FUNCTIONS FOR FIN PHYSICS ---

def calc_Nu_FlatPlate_Laminar(Re, Pr):
    """
    Laminar flow over a flat plate.
    Used for the developing region on the fins.
    """
    if Re <= 1.0: return 0.1 # Floor to avoid math errors
    
    term1 = 0.6774 * (Re ** 0.5) * (Pr ** (1.0/3.0))
    term2 = 1.0 + (0.0468 / Pr) ** (2.0/3.0)
    return term1 / (term2 ** 0.25)

def calc_Nu_Duct_Laminar():
    """
    Fully developed laminar flow in a rectangular duct (Aspect ratio ~ infinity).
    Constant heat flux approximation.
    """
    return 8.235

def calc_entry_length_laminar(rho, u, mu, Pr, D_hydraulic):
    """
    Estimates the hydrodynamic + thermal entry length.
    x_fd ~ 0.05 * Re_D * D_h * Pr (approx for thermal)
    """
    if mu <= 0: return 0.0
    Re_D = (rho * u * D_hydraulic) / mu
    return 0.05 * Re_D * D_hydraulic * Pr

def calc_Nu_Zukauskas_1972(Re, Pr, Pr_wall, S_T, S_L, D, N_rows=20):
    """
    Zukauskas (1972) correlation for Staggered Tube Banks.
    Valid for Re: 10 - 2,000,000
    
    Nu = C1 * C2 * Re^m * Pr^0.36 * (Pr / Pr_wall)^0.25
    
    Parameters:
      Re: Reynolds number based on D and u_max
      Pr: Prandtl number at bulk temperature
      Pr_wall: Prandtl number at wall temperature
      S_T: Transverse pitch [m]
      S_L: Longitudinal pitch [m]
      D: Tube diameter [m]
      N_rows: Number of rows (for correction factor C2)
    """
    if Re < 1.0: return 1.0 # Avoid math errors at zero flow
    
    # 1. Determine C1 and m based on Reynolds Regime
    # Ratios
    a = S_T / D
    b = S_L / D
    
    if Re < 100:
        # Laminar
        C1 = 0.9
        m = 0.4
    elif Re < 1000:
        # Transition to Turbulent
        C1 = 0.9 # (Approximate, Zukauskas charts vary slightly here)
        m = 0.4
    elif Re < 2e5:
        # Turbulent (Most common regime)
        # Coefficient depends on pitch ratio a/b
        if (a / b) < 2:
            C1 = 0.35 * ((a/b)**0.2)
        else:
            C1 = 0.40
        m = 0.60
    else:
        # High Re (Supercritical)
        C1 = 0.022
        m = 0.84

    # 2. Determine Row Correction Factor C2 (for N < 20)
    # Approximate values for Staggered banks
    if N_rows >= 20:
        C2 = 1.0
    elif N_rows >= 16:
        C2 = 0.99
    elif N_rows >= 10:
        C2 = 0.97
    elif N_rows >= 7:
        C2 = 0.95
    elif N_rows >= 5:
        C2 = 0.92
    elif N_rows >= 4:
        C2 = 0.88
    elif N_rows >= 3:
        C2 = 0.84
    elif N_rows >= 2:
        C2 = 0.77
    else:
        C2 = 0.64 # Single row

    # 3. Calculate Nu
    # Pr exponent is 0.36 for gases (Pr ~ 0.7)
    Nu = C1 * C2 * (Re**m) * (Pr**0.36) * ((Pr / Pr_wall)**0.25)
    
    return Nu