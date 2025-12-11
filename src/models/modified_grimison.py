import math
import logging
# Safe import for script/module usage
try:
    from .grimison import GrimisonModel
except ImportError:
    from grimison import GrimisonModel

logger = logging.getLogger(__name__)

class ModifiedGrimisonModel(GrimisonModel):
    """
    Modified Grimison Correlation (Hammock).
    
    Reference: Eq 16 & 17 in 'Cross-Flow Staggered-Tube Heat Exchanger Analysis'
    Nu = 1.13 * Xi_H * C1 * C2 * Re^m * Pr^(1/3)
    """

    def _calculate_xi_hammock(self, Re, Pr, N_L=1):
        """
        Calculates the High-Enthalpy Correction Factor (Xi_H).
        Source: Equation 17 
        
        Note: The paper states "since the numerical model calculates the heat 
        transfer by discrete rows, N_L = 1 for each row".
        """
        if Re <= 0: return 1.0
        
        # Term 1: Sqrt(N_L)
        term_rows = math.sqrt(N_L)
        
        # Term 2: Re / 2000
        term_re = Re / 2000.0
        
        # Term 3: (Pr / 0.71)^(1/3)
        # 0.71 is the reference Prandtl number for air
        term_pr = (Pr / 0.71)**(1.0/3.0)
        
        # Combine arguments for Tanh
        arg = term_rows * term_re * term_pr
        
        # Xi_H = [ tanh( arg ) ] ^ (1/3)
        xi = math.tanh(arg)**(1.0/3.0)
        
        return xi

    def calculate_Nu(self, Re, Pr, **kwargs):
        """
        Calculates Nu using Grimison coefficients + Hammock's Xi_H correction.
        """
        # 1. Get Base Grimison Nu (Using parent class logic)
        # Note: Parent calculates C2 * C1 * Re^m * Pr^(1/3)
        # We temporarily divide out the 1.13 factor if parent adds it, 
        # but your GrimisonModel likely doesn't have the 1.13 leading coeff?
        # WAIT: Eq 13 in paper says Nu = 1.13 * C1 * ... [cite: 204]
        # Your current GrimisonModel likely implements the standard Nu = C1...
        # We will apply the 1.13 factor here explicitly.
        
        # Get raw coeffs from parent logic to be safe
        S_T, S_L, D = kwargs['S_T'], kwargs['S_L'], kwargs['D']
        N_rows = kwargs.get('N_rows', 1)
        
        # Use Hammock Polynomials (Eq 14/15 equivalent in your code)
        C1, m = self._get_coeffs_hammock(S_T, S_L, D)
        C2 = self._get_c2_factor(N_rows)
        
        # 2. Calculate Correction Factor Xi_H (Eq 17)
        # Paper says use N_L=1 for row-by-row 
        xi_h = self._calculate_xi_hammock(Re, Pr, N_L=1)
        
        # 3. Final Calculation (Eq 16) 
        # Nu = 1.13 * Xi_H * C1 * C2 * Re^m * Pr^(1/3)
        Nu = 1.13 * xi_h * C1 * C2 * (Re**m) * (Pr**(1.0/3.0))
        
        return Nu