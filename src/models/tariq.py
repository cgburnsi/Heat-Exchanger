import math
# Import base class safely
try:
    from .base import HeatTransferModel
except ImportError:
    from base import HeatTransferModel

class TariqModel(HeatTransferModel):
    """
    Tariq et al. Correlation for Staggered Tube Banks.
    
    Specific for:
      - Low Reynolds Numbers
      - Rarefied Gas Flows (Slip Flow / Transition)
      - High Porosity
      
    Reference: Eq 10 in Tariq (2010?) Dissertation/Paper.
    """

    def calculate_Nu(self, Re, Pr, **kwargs):
        """
        Calculates Nu based on Tariq correlation with Knudsen correction.
        
        Required kwargs:
          - eps_por : Porosity (Void Fraction)
          - T       : Gas Temperature [K]
          - rho     : Gas Density [kg/m3]
          - mu      : Gas Viscosity [Pa-s]
          - M_gas   : Molar Mass [kg/mol]
          - D       : Tube Diameter [m]
        """
        # 1. Extract & Validate Parameters
        required = ['eps_por', 'T', 'rho', 'mu', 'M_gas', 'D']
        try:
            params = {k: kwargs[k] for k in required}
        except KeyError as e:
            raise ValueError(f"TariqModel requires parameter {e}")

        # Unpack for readability
        eps = params['eps_por']
        T   = params['T']
        rho = params['rho']
        mu  = params['mu']
        M   = params['M_gas']
        D   = params['D']

        # 2. Physics Constants
        k_B = 1.380649e-23      # Boltzmann [J/K]
        N_A = 6.02214076e23     # Avogadro [1/mol]

        # 3. Calculate Knudsen Number (Kn)
        # Convert molar mass [kg/mol] -> molecular mass [kg]
        m_molecule = M / N_A
        
        # Mean free path / Characteristic Length
        gas_term = math.sqrt((math.pi * m_molecule) / (2.0 * k_B * T))
        Kn = (mu / (rho * D)) * gas_term

        # 4. Coefficients based on Porosity
        # c1 affects the Reynolds scaling strength
        c1 = 3.12 - 0.16 * math.exp(3.0 * eps)
        # c2 affects the Rarefaction penalty strength
        c2 = 3.45 - 3.0 * math.exp(-3.45 * eps)

        # 5. Calculation
        # Protect against log(<=0)
        Re_safe = max(Re, 1.01)
        ln_Re = math.log(Re_safe)

        # Tariq Eq 10 Breakdown:
        # Nu = [ (0.48 - 0.2*eps) * (ln Re)^c1 * Pr / (eps/(1-eps)) ] 
        #      ------------------------------------------------------
        #                  [ 1 + 0.1 * (ln Re)^c2 * Kn ]

        term1 = (0.48 - 0.2 * eps)
        term2 = eps / (1.0 - eps)  # Porosity geometry factor
        term3 = ln_Re**c1
        
        numerator = term1 * term3 * Pr / term2
        denominator = 1.0 + 0.1 * (ln_Re**c2) * Kn

        return numerator / denominator
    
    
    
    
    
    
    