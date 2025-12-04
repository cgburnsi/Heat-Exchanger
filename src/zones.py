import math
import CoolProp.CoolProp as cp
from src import correlations as corr 
from src.fluids import FluidState 
# Default model if none provided
from src.models import TariqModel

class BaseZone:
    def __init__(self, name):
        self.name = name
        self.tube_centers = []
        self.n_tubes = 0
        self.origin_x = 0.0
        self.results = {} 

    def build_geometry(self):
        raise NotImplementedError

    def solve(self, hot_state_in, cold_state_in):
        raise NotImplementedError

# ==============================================================================
# PIPE FLOW ZONE (Inlet/Outlet Ducting)
# ==============================================================================
class PipeFlowZone(BaseZone):
    """
    Models a constant-area pipe or duct feeding the HX.
    Calculates friction pressure drop (Darcy-Weisbach).
    """
    def __init__(self, name, length, diameter, roughness=15e-6):
        super().__init__(name)
        self.length = float(length)
        self.diameter = float(diameter)
        self.roughness = float(roughness)
        self.area = (math.pi / 4.0) * self.diameter**2
        
        self.n_cols = 1 
        self.S_L = self.length 
        self.origin_x = 0.0

    def build_geometry(self):
        self.tube_centers = [] 

    def solve(self, hot_state_in, cold_state_in):
        Tg, Pg = hot_state_in.T, hot_state_in.P
        mdot_g = hot_state_in.m_dot
        str_g = hot_state_in.fluid_string
        
        rho = cp.PropsSI('D', 'T', Tg, 'P', Pg, str_g)
        mu  = cp.PropsSI('V', 'T', Tg, 'P', Pg, str_g)
        
        u_avg = mdot_g / (rho * self.area)
        Re_D = corr.calc_Re(rho, u_avg, self.diameter, mu)
        
        rel_rough = self.roughness / self.diameter
        f = corr.calc_friction_SwameeJain(Re_D, rel_rough)
        dP = f * (self.length / self.diameter) * 0.5 * rho * (u_avg**2)
        
        Pg_out = Pg - dP
        x_new = hot_state_in.x + self.length
        
        hot_out = FluidState(hot_state_in.name, Tg, Pg_out, mdot_g, hot_state_in.fluid_obj, x=x_new)
        cold_out = FluidState(cold_state_in.name, cold_state_in.T, cold_state_in.P, cold_state_in.m_dot, cold_state_in.fluid_obj, x=x_new)
        
        self.results = {
            'Q_total_kW': 0.0,
            'dP_gas_Pa': dP,
            'dP_cool_Pa': 0.0,
            'h_gas_avg': 0.0,
            'h_cool_avg': 0.0,
            'Re_gas_avg': Re_D,
            'Re_cool_avg': 0.0,
            'T_gas_out': Tg,
            'T_cool_out': cold_state_in.T
        }
        return hot_out, cold_out, [hot_out], [cold_out]

# ==============================================================================
# TUBE BANK ZONE (Bare Tubes)
# ==============================================================================
class TubeBankZone(BaseZone):
    """
    Staggered tube bank zone (Bare Tubes).
    Accepts a HeatTransferModel object for physics logic.
    """
    def __init__(self, name,
                 height, tube_dia, R_p, n_cols,
                 width=0.4064, 
                 origin_x=0.0, origin_y=0.0, stagger=True,
                 t_w=0.000889, k_wall=16.2, e_roughness=15e-6,
                 model=None): 
        
        super().__init__(name)
        self.height = float(height)
        self.width  = float(width) 
        self.tube_dia = float(tube_dia)
        self.R_p = float(R_p)
        self.n_cols = int(n_cols)
        self.origin_x = float(origin_x)
        self.origin_y = float(origin_y)
        self.stagger = bool(stagger)
        
        self.model = model if model else TariqModel()

        self.t_w = t_w
        self.k_wall = k_wall
        self.e_roughness = e_roughness

        self.D_t_inner = self.tube_dia - 2.0 * self.t_w
        self.S_T = self.R_p * self.tube_dia
        self.S_L = self.R_p * self.tube_dia 
        self.eps_por = 1.0 - ( (math.pi/4.0) * (self.tube_dia**2) ) / ( self.S_T * self.S_L )

    def _rows_in_column(self, offset):
        y_min = self.tube_dia / 2.0
        y_max = self.height - self.tube_dia / 2.0
        first_center = y_min + offset
        if first_center > y_max: return 0, []
        n_rows = int(math.floor((y_max - first_center) / self.S_T)) + 1
        y_list = [first_center + i * self.S_T for i in range(n_rows)]
        return n_rows, y_list

    def build_geometry(self):
        if self.stagger and self.S_T > 0.0:
            even_offset = 0.0; odd_offset = self.S_T / 2.0
        else:
            even_offset = 0.0; odd_offset = 0.0

        n_even_rows, y_even = self._rows_in_column(even_offset)
        n_odd_rows, y_odd = self._rows_in_column(odd_offset)
        self.n_rows_avg = (n_even_rows + n_odd_rows) / 2.0 

        centers = []
        for j in range(self.n_cols):
            is_odd = (j % 2 != 0)
            col_x = self.origin_x + j * self.S_L
            rows = y_odd if is_odd else y_even
            for y_loc in rows:
                centers.append((col_x, self.origin_y + y_loc))
        
        self.tube_centers = centers
        self.n_tubes = len(centers)
        return centers

    def solve(self, hot_state_in, cold_state_in):
        if not self.tube_centers: self.build_geometry()

        Tg, Pg = hot_state_in.T, hot_state_in.P
        Tc, Pc = cold_state_in.T, cold_state_in.P
        mdot_g = hot_state_in.m_dot
        mdot_c = cold_state_in.m_dot
        
        str_g = hot_state_in.fluid_string
        str_c = cold_state_in.fluid_string
        
        hot_profile, cold_profile = [], []
        stats_Q, stats_h_g, stats_h_c = [], [], []
        stats_Re_g, stats_Re_c, stats_dP_g, stats_dP_c = [], [], [], []

        L_tubes = self.width 
        dx = self.S_L 
        A_front = self.height * L_tubes
        sigma_gap = (self.S_T - self.tube_dia) / self.S_T
        A_min_flow = A_front * sigma_gap 

        A_surf_tube = self.n_rows_avg * math.pi * self.tube_dia * L_tubes
        A_surf_cool = self.n_rows_avg * math.pi * self.D_t_inner * L_tubes
        
        if self.n_tubes == 0: self.build_geometry()
        mdot_per_tube = mdot_c / self.n_tubes
        A_c_cross = math.pi * (self.D_t_inner**2) / 4.0

        for i in range(self.n_cols):
            x_loc = self.origin_x + (i + 1) * dx
            
            try:
                rho_g = cp.PropsSI('D', 'T', Tg, 'P', Pg, str_g)
                mu_g  = cp.PropsSI('V', 'T', Tg, 'P', Pg, str_g)
                cp_g  = cp.PropsSI('C', 'T', Tg, 'P', Pg, str_g)
                k_g   = cp.PropsSI('L', 'T', Tg, 'P', Pg, str_g)
                pr_g  = cp.PropsSI('Prandtl', 'T', Tg, 'P', Pg, str_g)
                M_g   = cp.PropsSI('M', str_g)
            except ValueError as e:
                print(f"CoolProp Error: {e}")
                break

            rho_c = cp.PropsSI('D', 'T', Tc, 'P', Pc, str_c)
            mu_c  = cp.PropsSI('V', 'T', Tc, 'P', Pc, str_c)
            cp_c  = cp.PropsSI('C', 'T', Tc, 'P', Pc, str_c)
            k_c   = cp.PropsSI('L', 'T', Tc, 'P', Pc, str_c)
            pr_c  = cp.PropsSI('Prandtl', 'T', Tc, 'P', Pc, str_c)
            
            # --- GAS SIDE PHYSICS ---
            if hasattr(self.model, 'calculate_Re_max'):
                Re_t = self.model.calculate_Re_max(
                    rho_g, mdot_g, A_front, self.S_T, self.S_L, self.tube_dia, mu_g
                )
                u_max = (Re_t * mu_g) / (rho_g * self.tube_dia) if rho_g > 0 else 0.0
            else:
                u_max = mdot_g / (rho_g * A_min_flow)
                Re_t = corr.calc_Re(rho_g, u_max, self.tube_dia, mu_g)
            
            # --- MODEL PARAMETERS ---
            model_params = {
                'eps_por': self.eps_por,
                'T': Tg, 'rho': rho_g, 'mu': mu_g, 'M_gas': M_g,
                'D': self.tube_dia,
                'S_T': self.S_T, 'S_L': self.S_L,
                'N_rows': self.n_cols, 
                'Pr_wall': pr_g, 
                'T_wall': Tc, 
                'T_cool': Tc
            }
            
            Nu_t = self.model.calculate_Nu(Re_t, pr_g, **model_params)
            h_t = Nu_t * k_g / self.tube_dia
            
            Eu_row = corr.calc_Eu_HEDH(Re_t, self.R_p)
            dP_g_col = corr.calc_dP_gas_column(Eu_row, rho_g, u_max, self.n_rows_avg)
            
            # --- COOLANT SIDE ---
            u_c = mdot_per_tube / (rho_c * A_c_cross)
            Re_h = corr.calc_Re(rho_c, u_c, self.D_t_inner, mu_c)
            f_cool = corr.calc_friction_SwameeJain(Re_h, self.e_roughness/self.D_t_inner)
            Nu_h   = corr.calc_Nu_Gnielinski(Re_h, pr_c, f_cool, self.D_t_inner, L_tubes)
            h_c    = Nu_h * k_c / self.D_t_inner
            dP_c_col = corr.calc_dP_coolant_tube(f_cool, rho_c, u_c, self.D_t_inner, L_tubes / self.n_cols)

            # --- PHYSICS AUDIT ---
            if i == 0:
                print(f"\n--- PHYSICS AUDIT: {self.name} ---")
                # Fix: Use class name instead of missing self.correlation attribute
                model_name = self.model.__class__.__name__
                method_name = getattr(self.model, 'method', 'standard')
                print(f"  Model:    {model_name} ({method_name})")
                print(f"  Flow:     u_max={u_max:.2f} m/s, Re={Re_t:.1f}")
                
                if Re_t < 2000: print("  Regime:   Laminar / Transition")
                else: print("  Regime:   Turbulent")
                
                print(f"  Result:   Nu={Nu_t:.2f}, h={h_t:.2f} W/m2K")
                print("---------------------------------")

            # --- SOLVE ---
            R_gas  = 1.0 / (h_t * A_surf_tube)
            R_cool = 1.0 / (h_c * A_surf_cool)
            R_wall = math.log(self.tube_dia/self.D_t_inner) / (2*math.pi*self.k_wall*L_tubes * self.n_rows_avg)
            UA = 1.0 / (R_gas + R_cool + R_wall)
            
            dT = Tg - Tc
            Q = UA * dT
            
            Tg -= Q / (mdot_g * cp_g)
            Tc += Q / (mdot_c * cp_c)
            Pg -= dP_g_col
            Pc -= dP_c_col 
            
            hot_profile.append(FluidState(hot_state_in.name, Tg, Pg, mdot_g, hot_state_in.fluid_obj, x=x_loc))
            cold_profile.append(FluidState(cold_state_in.name, Tc, Pc, mdot_c, cold_state_in.fluid_obj, x=x_loc))

            stats_Q.append(Q)
            stats_h_g.append(h_t)
            stats_h_c.append(h_c)
            stats_Re_g.append(Re_t)
            stats_Re_c.append(Re_h)
            stats_dP_g.append(dP_g_col)
            stats_dP_c.append(dP_c_col)

        if not stats_Q: return hot_state_in, cold_state_in, [], []

        self.results = {
            'Q_total_kW': sum(stats_Q) / 1000.0,
            'dP_gas_Pa': sum(stats_dP_g),
            'dP_cool_Pa': sum(stats_dP_c),
            'h_gas_avg': sum(stats_h_g) / len(stats_h_g),
            'h_cool_avg': sum(stats_h_c) / len(stats_h_c),
            'Re_gas_avg': sum(stats_Re_g) / len(stats_Re_g),
            'Re_cool_avg': sum(stats_Re_c) / len(stats_Re_c),
            'T_gas_out': Tg,
            'T_cool_out': Tc
        }

        return hot_profile[-1], cold_profile[-1], hot_profile, cold_profile

# ==============================================================================
# PLATE FIN ZONE (Inherits Dependency Injection from TubeBankZone)
# ==============================================================================
class PlateFinZone(TubeBankZone):
    def __init__(self, name, height, tube_dia, R_p, n_cols,
                 fin_pitch, fin_thickness, 
                 width=0.4064, origin_x=0.0, origin_y=0.0, stagger=True,
                 t_w=0.000889, k_wall=16.2, e_roughness=15e-6,
                 model=None): 
        
        super().__init__(name, height, tube_dia, R_p, n_cols, width, 
                         origin_x, origin_y, stagger, t_w, k_wall, e_roughness,
                         model=model)
        
        self.fin_pitch = float(fin_pitch)
        self.fin_thickness = float(fin_thickness)
        self.fin_gap = self.fin_pitch - self.fin_thickness
        self.D_h = 2.0 * self.fin_gap

    def solve(self, hot_state_in, cold_state_in):
        if not self.tube_centers: self.build_geometry()

        Tg, Pg = hot_state_in.T, hot_state_in.P
        Tc, Pc = cold_state_in.T, cold_state_in.P
        mdot_g = hot_state_in.m_dot
        mdot_c = cold_state_in.m_dot
        
        str_g = hot_state_in.fluid_string
        str_c = cold_state_in.fluid_string
        
        hot_profile, cold_profile = [], []
        stats_Q, stats_h_g, stats_h_c = [], [], []
        stats_Re_g, stats_Re_c, stats_dP_g, stats_dP_c = [], [], [], []

        L_tubes = self.width 
        dx = self.S_L 
        N_fins = math.floor(L_tubes / self.fin_pitch)
        A_front = self.height * L_tubes
        sigma_gap = (self.S_T - self.tube_dia) / self.S_T
        fin_blockage = 1.0 - (self.fin_thickness / self.fin_pitch)
        A_min_flow = A_front * sigma_gap * fin_blockage

        len_exposed_tubes = L_tubes - (N_fins * self.fin_thickness)
        A_tube_surf = self.n_rows_avg * math.pi * self.tube_dia * len_exposed_tubes
        A_fin_face = (self.height * dx) - (self.n_rows_avg * 0.25 * math.pi * self.tube_dia**2)
        A_fin_surf = 2.0 * N_fins * A_fin_face
        A_cool_surf = self.n_rows_avg * math.pi * self.D_t_inner * L_tubes
        
        if self.n_tubes == 0: self.build_geometry()
        mdot_per_tube = mdot_c / self.n_tubes
        A_c_cross = math.pi * (self.D_t_inner**2) / 4.0

        for i in range(self.n_cols):
            x_loc = self.origin_x + (i + 1) * dx
            x_local = (i + 0.5) * dx 
            
            try:
                rho_g = cp.PropsSI('D', 'T', Tg, 'P', Pg, str_g)
                mu_g  = cp.PropsSI('V', 'T', Tg, 'P', Pg, str_g)
                cp_g  = cp.PropsSI('C', 'T', Tg, 'P', Pg, str_g)
                k_g   = cp.PropsSI('L', 'T', Tg, 'P', Pg, str_g)
                pr_g  = cp.PropsSI('Prandtl', 'T', Tg, 'P', Pg, str_g)
                M_g   = cp.PropsSI('M', str_g)
            except ValueError: break

            rho_c = cp.PropsSI('D', 'T', Tc, 'P', Pc, str_c)
            mu_c  = cp.PropsSI('V', 'T', Tc, 'P', Pc, str_c)
            cp_c  = cp.PropsSI('C', 'T', Tc, 'P', Pc, str_c)
            k_c   = cp.PropsSI('L', 'T', Tc, 'P', Pc, str_c)
            pr_c  = cp.PropsSI('Prandtl', 'T', Tc, 'P', Pc, str_c)
            
            # A. TUBE PHYSICS (With Model Injection)
            if hasattr(self.model, 'calculate_Re_max'):
                Re_t = self.model.calculate_Re_max(
                    rho_g, mdot_g, A_front * fin_blockage, 
                    self.S_T, self.S_L, self.tube_dia, mu_g
                )
            else:
                u_max = mdot_g / (rho_g * A_min_flow)
                Re_t = corr.calc_Re(rho_g, u_max, self.tube_dia, mu_g)
            
            model_params = {
                'eps_por': self.eps_por,
                'T': Tg, 'rho': rho_g, 'mu': mu_g, 'M_gas': M_g,
                'D': self.tube_dia,
                'S_T': self.S_T, 'S_L': self.S_L,
                'N_rows': self.n_cols, 
                'Pr_wall': pr_g,
                'T_wall': Tc, 
                'T_cool': Tc
            }
            
            Nu_t = self.model.calculate_Nu(Re_t, pr_g, **model_params)
            h_tube = Nu_t * k_g / self.tube_dia
            
            # B. FIN PHYSICS
            A_fin_channel = A_front * fin_blockage
            u_fin = mdot_g / (rho_g * A_fin_channel)
            x_entry = corr.calc_entry_length_laminar(rho_g, u_fin, mu_g, pr_g, self.D_h)
            
            if x_local < x_entry:
                Re_x = corr.calc_Re(rho_g, u_fin, x_local, mu_g)
                Nu_fin = corr.calc_Nu_FlatPlate_Laminar(Re_x, pr_g)
                h_fin = Nu_fin * k_g / x_local
            else:
                Nu_fin = corr.calc_Nu_Duct_Laminar()
                h_fin = Nu_fin * k_g / self.D_h
                
            # C. COMBINED
            UA_gas_col = (h_tube * A_tube_surf) + (h_fin * A_fin_surf)
            h_effective = UA_gas_col / (A_tube_surf + A_fin_surf)

            Eu_row = corr.calc_Eu_HEDH(Re_t, self.R_p)
            dP_g_col = corr.calc_dP_gas_column(Eu_row, rho_g, mdot_g/(rho_g*A_min_flow), self.n_rows_avg)
            
            u_c = mdot_per_tube / (rho_c * A_c_cross)
            Re_h = corr.calc_Re(rho_c, u_c, self.D_t_inner, mu_c)
            f_cool = corr.calc_friction_SwameeJain(Re_h, self.e_roughness/self.D_t_inner)
            Nu_h   = corr.calc_Nu_Gnielinski(Re_h, pr_c, f_cool, self.D_t_inner, L_tubes)
            h_c    = Nu_h * k_c / self.D_t_inner
            dP_c_col = corr.calc_dP_coolant_tube(f_cool, rho_c, u_c, self.D_t_inner, L_tubes / self.n_cols)

            # D. SOLVE
            R_gas  = 1.0 / UA_gas_col
            R_cool = 1.0 / (h_c * A_cool_surf)
            R_wall = math.log(self.tube_dia/self.D_t_inner) / (2*math.pi*self.k_wall*L_tubes * self.n_rows_avg)
            UA_total = 1.0 / (R_gas + R_cool + R_wall)
            
            dT = Tg - Tc
            Q = UA_total * dT
            
            Tg -= Q / (mdot_g * cp_g)
            Tc += Q / (mdot_c * cp_c)
            Pg -= dP_g_col
            Pc -= dP_c_col 
            
            hot_profile.append(FluidState(hot_state_in.name, Tg, Pg, mdot_g, hot_state_in.fluid_obj, x=x_loc))
            cold_profile.append(FluidState(cold_state_in.name, Tc, Pc, mdot_c, cold_state_in.fluid_obj, x=x_loc))
            
            stats_Q.append(Q)
            stats_h_g.append(h_effective)
            stats_h_c.append(h_c)
            stats_Re_g.append(Re_t)
            stats_Re_c.append(Re_h)
            stats_dP_g.append(dP_g_col)
            stats_dP_c.append(dP_c_col)

        if not stats_Q: return hot_state_in, cold_state_in, [], []

        self.results = {
            'Q_total_kW': sum(stats_Q) / 1000.0,
            'dP_gas_Pa': sum(stats_dP_g),
            'dP_cool_Pa': sum(stats_dP_c),
            'h_gas_avg': sum(stats_h_g) / len(stats_h_g),
            'h_cool_avg': sum(stats_h_c) / len(stats_h_c),
            'Re_gas_avg': sum(stats_Re_g) / len(stats_Re_g),
            'Re_cool_avg': sum(stats_Re_c) / len(stats_Re_c),
            'T_gas_out': Tg,
            'T_cool_out': Tc
        }
        return hot_profile[-1], cold_profile[-1], hot_profile, cold_profile