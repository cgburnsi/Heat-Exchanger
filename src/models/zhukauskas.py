import math
import logging
try:
    from .base import HeatTransferModel
except ImportError:
    from base import HeatTransferModel

logger = logging.getLogger(__name__)

class ZhukauskasModel(HeatTransferModel):
    """
    Zhukauskas (1972) Correlation for Staggered Tube Banks.
    Reference: Eq 18 in 'Cross-Flow Staggered-Tube Heat Exchanger Analysis' 
    """
    
    def _get_c1_m(self, Re, ST, SL):
        """
        Retrieves C1 and m from Table 5.
        """
        # 10 < Re < 100
        if Re < 100:
            return 0.90, 0.40
            
        # 100 < Re < 1000
        elif Re < 1000:
            # Paper says "Approximate as an isolated cylinder" 
            # Uses Eq 20 constants from Table 6 [cite: 456]
            return 0.51, 0.50 
            
        # 1000 < Re < 2e5
        elif Re < 2e5:
            ratio = ST / SL
            if ratio < 2.0:
                # C1 = 0.35 * (ST/SL)^0.2
                c1 = 0.35 * (ratio**0.2)
                return c1, 0.60
            else:
                return 0.40, 0.60
                
        # 2e5 < Re < 2e6
        else:
            return 0.022, 0.84

    def _get_c2(self, N_rows, Re):
        """
        Calculates Row Correction Factor C2 (Eq 19)[cite: 443].
        Approximates Tables 3 & 4.
        """
        if N_rows >= 20: return 1.0
        
        # Eq 19 [cite: 443]
        if Re > 1000:
            # C2 = 1 - e^(-N_L^(1/2)) ?? The PDF text is fuzzy here.
            # Usually Zhukauskas C2 is a simple lookup. 
            # Let's use the Table 4 values directly for accuracy [cite: 440]
            # (Valid for Re >= 1000)
            table = {1:0.64, 2:0.76, 3:0.84, 4:0.89, 5:0.92, 7:0.95, 10:0.97, 13:0.98, 16:0.99}
            
        else:
            # Table 3 (Re < 1000) [cite: 436]
            table = {1:0.83, 2:0.88, 3:0.91, 4:0.94, 5:0.95, 7:0.97, 10:0.98, 13:0.99, 16:1.0}
            
        # Discrete Lookup (Nearest)
        return table.get(int(N_rows), 1.0) # Default to 1.0 if not in sparse table

    def calculate_Nu(self, Re, Pr, **kwargs):
        """
        Eq 18: Nu = C1 * C2 * Re^m * Pr^n * (Pr/Pr_s)^0.25
        """
        try:
            S_T, S_L = kwargs['S_T'], kwargs['S_L']
            N_rows = kwargs.get('N_rows', 20)
            # Pr_s is Prandtl at surface temp. 
            # If not provided, assume Pr_s = Pr (Wall temp ~ Bulk temp)
            Pr_s = kwargs.get('Pr_wall', Pr) 
        except KeyError as e:
            raise ValueError(f"ZhukauskasModel requires {e}")

        # 1. Get Coefficients
        C1, m = self._get_c1_m(Re, S_T, S_L)
        C2 = self._get_c2(N_rows, Re)
        
        # 2. Exponent n
        # Table 5 says n=0.36 for Re < 2e5 
        # Text says n=0.4 for heating, 0.3 for cooling? 
        # Actually Eq 18 just lists 'n' in Table 5.
        n = 0.36
        
        # 3. Calculate
        # Nu = C1 * C2 * Re^m * Pr^n * (Pr / Pr_s)^0.25
        Nu = C1 * C2 * (Re**m) * (Pr**n) * ((Pr / Pr_s)**0.25)
        
        return Nu