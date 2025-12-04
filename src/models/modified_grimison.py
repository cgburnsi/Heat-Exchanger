import math

# Safe import for script/module usage
try:
    # When running as part of the src package
    from .grimison import GrimisonModel
except ImportError:
    # When running this file directly
    from grimison import GrimisonModel

class ModifiedGrimisonModel(GrimisonModel):
    """
    Modified Grimison Correlation (Hammock).
    
    Inherits geometry coefficients (C1, m) and row corrections (C2) 
    from the standard Grimison model, but applies a correction factor (Xi_H)
    to account for large property variations in high-enthalpy flows.
    
    Nu = C2 * C1 * Re^m * Pr^(1/3) * Xi_H
    """

    def _calculate_xi(self, T_gas, T_wall):
        """
        Calculates the Property Variation Correction Factor (Xi_H).
        Standard correction: Xi = (T_gas / T_wall) ^ n
        """
        if T_wall <= 0 or T_gas <= 0: return 1.0
        
        # Ratio of Bulk Temp to Wall Temp (in Kelvin)
        T_ratio = T_gas / T_wall
        
        # EXPONENT 'n' (Hammock/Zukauskas standard for gas cooling)
        n = 0.25 
        
        return T_ratio ** n

    def calculate_Nu(self, Re, Pr, **kwargs):
        """
        Calculates Nu using Grimison tables + Xi_H correction.
        """
        # 1. Calculate Base Grimison Nu (C1 * C2 * Re^m * Pr^1/3)
        # We call the parent class method
        Nu_base = super().calculate_Nu(Re, Pr, **kwargs)
        
        # 2. Extract Temperatures for Correction
        T_gas = kwargs.get('T')
        
        # Look for 'T_wall' (explicit) or 'T_cool' (proxy), default to T_gas
        T_wall = kwargs.get('T_wall', kwargs.get('T_cool', T_gas))
        
        # 3. Calculate Correction Factor Xi_H
        xi_h = self._calculate_xi(T_gas, T_wall)
        
        return Nu_base * xi_h