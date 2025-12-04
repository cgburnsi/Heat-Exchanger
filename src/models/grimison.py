import math
import logging

try: from .base import HeatTransferModel
except ImportError: from  base import HeatTransferModel    # Fallback when running as a script 

# Set Logger for this module
logger = logging.getLogger(__name__)


class GrimisonModel(HeatTransferModel):
    ''' Grimison Heat Transfer Model (1937 Version) '''
    """
    Grimison (1937) Correlation.
    
    Methods:
      - 'nearest': Table lookup (Robust)
      - 'hammock': Polynomial fits from Hammock Dissertation (Best for Validation)
    """
    LIMITS = {'Re_min': 500, 'Re_max': 40_000,
              'a_min': 1.25,  'a_max':  3.60,       # a = S_T/d_out
              'b_min': 0.60,  'b_max':  3.00,       # b = S_L/d_out
        }
    
    _COEFFICIENTS = {
        (3.00, 0.60): (0.213, 0.636),
    
        (2.00, 0.90): (0.446, 0.571),
        (3.00, 0.90): (0.401, 0.581),
    
        (1.50, 1.00): (0.497, 0.558),
    
        (2.00, 1.125): (0.478, 0.565),
        (3.00, 1.125): (0.518, 0.560),
    
        (1.25, 1.25): (0.518, 0.556),
        (1.50, 1.25): (0.505, 0.554),
        (2.00, 1.25): (0.519, 0.556),
        (3.00, 1.25): (0.552, 0.562),
    
        (1.25, 1.50): (0.451, 0.568),
        (1.50, 1.50): (0.460, 0.562),
        (2.00, 1.50): (0.452, 0.568),
        (3.00, 1.50): (0.488, 0.568),
    
        (1.25, 2.00): (0.404, 0.568),
        (1.50, 2.00): (0.416, 0.568),
        (2.00, 2.00): (0.482, 0.556),
        (3.00, 2.00): (0.449, 0.570),
    
        (1.25, 3.00): (0.310, 0.592),
        (1.50, 3.00): (0.356, 0.580),
        (2.00, 3.00): (0.440, 0.562),
        (3.00, 3.00): (0.428, 0.574),
    }

    _ROW_CORRECTIONS = {1: 0.68, 2: 0.75, 3: 0.83, 4: 0.89, 5: 0.92,
                        6: 0.95, 7: 0.97, 8: 0.98, 9: 0.99}

    def __init__(self, method="hammock"):
        ''' method: 'hammock' will use the Hammock Polynomial Curves
                    'nearest' will use table lookup from the provided _COEFFICIENTS '''
        self.method = method
        msg = f'Grimison (1937): Using {method} for coefficient calculation.'
        logger.info(msg)

    # ---------- INTERNAL METHODS ---------------------------------------------------------------------------
    def _check_reynolds(self, Re):
        ''' Check Reynolds Number Against Correlation Limits '''
        if Re < self.LIMITS['Re_min']:
            msg = f'Reynolds {Re:.0f} < {self.LIMITS["Re_min"]}: Grimison (1937) valid in Turbulent Flows Only.'
            logger.critical(msg)
            raise ValueError(msg)
        if Re > self.LIMITS['Re_max']:
            msg = f'Reynolds {Re:.0f} > {self.LIMITS["Re_max"]}: Grimison (1937) Not Valid.'
            logger.critical(msg)
            raise ValueError(msg)

    def _check_geometry(self, a, b):
        # 1. Physical Overlap
        if (0.5 * a)**2 + b**2 < 1.0:
            msg = f"Grimison (1937) Geometry Overlap! S_T/D={a:.2f}, S_L/D={b:.2f} implies collision."
            logger.critical(msg)
            raise ValueError(msg)
        # 2. Table Range Check
        L = self.LIMITS
        is_valid = (L['a_min'] <= a <= L['a_max']) and (L['b_min'] <= b <= L['b_max'])
        
        if not is_valid:
            msg = (f"Grimison (1937) Geometry ({a:.2f}, {b:.2f}) outside valid Grimison range.")
            logger.critical(msg)            
            raise ValueError(msg)

    def _get_c2_factor(self, N_rows):
        """
        Retrieves Row Correction Factor C2.
        Enforces STRICT INTEGER inputs.
        """
        # 1. Strict Integer Check
        if isinstance(N_rows, float) and not N_rows.is_integer():
            msg = f"Physical Violation: N_rows must be a whole number. Received {N_rows}."
            logger.critical(msg)
            raise ValueError(msg)
        n_int = int(N_rows)
        # 2. Physics Check
        if n_int < 1:
            msg = "Grimison (1937) Geometry Violation: Less than 1 column of tubes specified."
            logger.critical(msg)
            raise ValueError(msg)
        elif n_int > 9:
            msg = "Grimison (1937) Geometry: Greater than 9 columns. Assuming C2=1.0"
            logger.info(msg)
            return 1.0
        else:
            return self._ROW_CORRECTIONS[n_int]

    def _get_coeffs_hammock(self, S_T, S_L, D):
        """
        Polynomial curve fits from Hammock Dissertation (Fig 3 data source).
        """
        # Ratios
        a = S_T / D
        b = S_L / D
        
        # 1. Calculate C1 (Coefficient)
        # Poly = A*b^3 + B*b^2 + C*b + D
        # where A,B,C,D are functions of a
        a_coeff = -0.066572 * a**2 + 0.438619 * a - 0.534414
        b_coeff =  0.447806 * a**2 - 2.867419 * a + 3.482562
        c_coeff = -1.046594 * a**2 + 6.359781 * a - 7.686638
        d_coeff =  0.803673 * a**2 - 4.605252 * a + 5.975412 
        
        C1 = a_coeff * b**3 + b_coeff * b**2 + c_coeff * b + d_coeff
        
        # 2. Calculate m (Exponent)
        a_exp =  0.009058 * a**2 - 0.076068 * a + 0.104510
        b_exp = -0.071578 * a**2 + 0.534418 * a - 0.706706
        c_exp =  0.193359 * a**2 - 1.270342 * a + 1.608849
        d_exp = -0.154482 * a**2 + 0.934097 * a - 0.585832 
        
        m = a_exp * b**3 + b_exp * b**2 + c_exp * b + d_exp
        
        return C1, m

    def _get_coeffs_nearest(self, S_T, S_L, D):
        target_a = S_T / D
        target_b = S_L / D
        best_key = min(self._COEFFICIENTS.keys(), 
                       key=lambda k: math.sqrt((k[0]-target_a)**2 + (k[1]-target_b)**2))
        return self._COEFFICIENTS[best_key]

    # ---------- CALCULATION METHODS ------------------------------------------------------------------------
    def calculate_Re_max(self, rho, m_dot, A_front, S_T, S_L, D, mu):
        S_D = math.sqrt(S_L**2 + (S_T / 2.0)**2)
        if S_D < (S_T + D) / 2.0:
            u_front = m_dot / (rho * A_front)
            u_max = u_front * (S_T / (2.0 * (S_D - D)))
        else:
            u_front = m_dot / (rho * A_front)
            u_max = u_front * (S_T / (S_T - D))
        return (rho * u_max * D) / mu if mu > 0 else 0.0

    def calculate_Nu(self, Re, Pr, **kwargs):
        try:
            S_T, S_L, D = kwargs['S_T'], kwargs['S_L'], kwargs['D']
            N_rows = kwargs.get('N_rows', 20)
        except KeyError as e:
            raise ValueError(f"GrimisonModel requires parameter {e}")

        # 1. Validate
        self._check_geometry(S_T/D, S_L/D)
        self._check_reynolds(Re)

        # 2. Coefficients
        if self.method == "hammock":
            C1, m = self._get_coeffs_hammock(S_T, S_L, D)
        else:
            C1, m = self._get_coeffs_nearest(S_T, S_L, D)
            
        # 3. Correction
        C2 = self._get_c2_factor(N_rows)
        
        return C2 * C1 * (Re**m) * (Pr**(1.0/3.0))
    
    
    
    
    
    

# ... (Class definition remains the same) ...

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import numpy as np
    from collections import defaultdict
    
    # Simple Test for Logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    

    print("--- GRIMISON MODEL DIAGNOSTICS ---")
    model_poly = GrimisonModel(method="hammock")

    # 1. Extract Reference Data (The dots)
    data_by_a = defaultdict(list)
    for (a, b), (C, m) in GrimisonModel._COEFFICIENTS.items():
        data_by_a[a].append((b, C, m))
    for a in data_by_a: data_by_a[a].sort()

    # 2. Define Plot Styles
    target_ratios = [1.25, 1.5, 2.0, 3.0]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes_flat = axes.flatten()
    b_smooth = np.linspace(1.0, 3.0, 100)

    # ==========================================================================
    # NEW: Define a Test Geometry to "Spot Check" the Code
    # ==========================================================================
    # Example: Bank 1 Geometry
    # D_out=1.518, S_T=4.4375, S_L=1.9060
    test_D = 1.518
    test_ST = 4.4375
    test_SL = 1.9060
    
    # Calculate Ratios
    test_a = test_ST / test_D  # ~2.92
    test_b = test_SL / test_D  # ~1.25
    
    # RUN THE CODE for this specific point
    test_C, test_m = model_poly._get_coeffs_hammock(test_ST, test_SL, test_D)
    
    print(f"\n[Spot Check] Bank 1 Geometry:")
    print(f"  a={test_a:.3f}, b={test_b:.3f}")
    print(f"  Calculated C1={test_C:.4f}, m={test_m:.4f}")
    # ==========================================================================

    # 3. Loop through plots
    for idx, a_val in enumerate(target_ratios):
        ax1 = axes_flat[idx]
        
        # Setup Secondary Axis
        ax2 = ax1.twinx()
        
        # Plot Reference Data (The Dots)
        if a_val in data_by_a:
            raw_data = data_by_a[a_val]
            b_raw = [item[0] for item in raw_data]
            C_raw = [item[1] for item in raw_data]
            m_raw = [item[2] for item in raw_data]
            
            ax1.scatter(b_raw, C_raw, color='tab:blue', s=60, label='Ref Data $C_1$', zorder=3)
            ax2.scatter(b_raw, m_raw, color='tab:red', marker='D', s=40, label='Ref Data $m$', zorder=3)

        # Plot Our Code's Output (The Lines)
        C_smooth = []
        m_smooth = []
        for b_val in b_smooth:
            c_calc, m_calc = model_poly._get_coeffs_hammock(S_T=a_val, S_L=b_val, D=1.0)
            C_smooth.append(c_calc)
            m_smooth.append(m_calc)
            
        ax1.plot(b_smooth, C_smooth, 'tab:blue', linewidth=2, label='Code Model $C_1$', zorder=2)
        ax2.plot(b_smooth, m_smooth, 'tab:red', linewidth=2, linestyle='--', label='Code Model $m$', zorder=2)

        # ----------------------------------------------------------------------
        # PLOT THE SPOT CHECK (Only on the plot closest to its 'a' value)
        # ----------------------------------------------------------------------
        # Bank 1 has a=2.92. We plot it on the a=3.0 chart for comparison.
        if abs(test_a - a_val) < 0.25:
            ax1.scatter(test_b, test_C, color='gold', marker='*', s=300, edgecolors='black', 
                        label='Bank 1 Calc', zorder=10)
            ax2.scatter(test_b, test_m, color='gold', marker='*', s=300, edgecolors='black', 
                        zorder=10)
            # Add annotation
            ax1.text(test_b, test_C+0.02, f"Bank 1\n(a={test_a:.2f})", ha='center', fontsize=9, 
                     bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))

        # Formatting
        ax1.set_title(f"Geometry: $S_T/D \\approx {a_val}$", fontsize=12, fontweight='bold')
        ax1.set_xlabel("$S_L/D$")
        ax1.set_ylabel("$C_1$", color='tab:blue', fontweight='bold')
        ax2.set_ylabel("$m$", color='tab:red', fontweight='bold')
        
        ax1.tick_params(axis='y', labelcolor='tab:blue')
        ax2.tick_params(axis='y', labelcolor='tab:red')
        ax1.grid(True, alpha=0.3)
        
        # Limits
        ax1.set_ylim(0.2, 0.6)
        ax2.set_ylim(0.5, 0.75)
        ax1.set_xlim(0.5, 3.1)

    # Global Legend (from the last plot)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    fig.legend(lines1 + lines2, labels1 + labels2, loc='lower center', ncol=5, bbox_to_anchor=(0.5, 0.01))

    plt.suptitle("Model Validation: Hammock Polynomials vs. Reference Data", fontsize=16)
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.show()
    print("  Done. Gold Stars indicate your Bank 1 calculation.")