import CoolProp.CoolProp as cp

class HeatExchanger:
    """
    Top-level container: owns streams and zones, orchestrates geometry + solve.
    """
    def __init__(self, name, hot_stream, cold_stream):
        self.name = name
        self.hot_stream = hot_stream
        self.cold_stream = cold_stream
        self.zones = []

        self.hot_out = hot_stream.inlet.copy()
        self.cold_out = cold_stream.inlet.copy()
        
        # New: Store the target (defaults to None)
        self.target_T_out = None
        self.Q_required = None

    def set_target_outlet_temp(self, T_target):
        """
        Sets the desired Gas Outlet Temperature [K].
        Calculates the required Q [W] to achieve this based on Inlet Enthalpy.
        """
        self.target_T_out = float(T_target)
        
        # 1. Get Inlet State
        inlet = self.hot_stream.inlet
        
        # 2. Calculate Required Outlet Enthalpy
        # We assume Pressure drop is negligible for this thermodynamic target check, 
        # or we use the inlet pressure as a conservative estimate.
        try:
            # Use the fluid string from the inlet state
            h_in = inlet.h
            h_out_req = cp.PropsSI('H', 'T', self.target_T_out, 'P', inlet.P, inlet.fluid_string)
            
            # Q = m_dot * (h_in - h_out)
            self.Q_required = inlet.m_dot * (h_in - h_out_req)
            
        except Exception as e:
            print(f"Warning: Could not calculate target thermodynamics: {e}")
            self.Q_required = 0.0

    def add_zone(self, zone):
        current_x_offset = 0.0
        if self.zones:
            last_zone = self.zones[-1]
            last_len = last_zone.n_cols * last_zone.S_L            
            current_x_offset = last_zone.origin_x + last_len
        
        zone.origin_x = current_x_offset
        self.zones.append(zone)

    def build_geometry(self):
        for zone in self.zones:
            zone.build_geometry()

    def solve(self):
        print(f"--- Solving {self.name} ---")
        
        current_hot = self.hot_stream.inlet
        current_cold = self.cold_stream.inlet
        
        self.hot_stream.profile = [current_hot]
        self.cold_stream.profile = [current_cold]
        
        for zone in self.zones:
            print(f"  > Marching Zone: {zone.name}...")
            
            h_out, c_out, h_prof, c_prof = zone.solve(current_hot, current_cold)
            
            self.hot_stream.profile.extend(h_prof)
            self.cold_stream.profile.extend(c_prof)
            
            current_hot = h_out
            current_cold = c_out
            
        self.hot_out = current_hot
        self.cold_out = current_cold
        
        print(f"--- Complete. T_gas_out: {self.hot_out.T:.2f} K ---")
        return self.hot_out, self.cold_out

    import CoolProp.CoolProp as cp

class HeatExchanger:
    """
    Top-level container: owns streams and zones, orchestrates geometry + solve.
    """
    def __init__(self, name, hot_stream, cold_stream):
        self.name = name
        self.hot_stream = hot_stream
        self.cold_stream = cold_stream
        self.zones = []

        self.hot_out = hot_stream.inlet.copy()
        self.cold_out = cold_stream.inlet.copy()
        
        # Store the target (defaults to None)
        self.target_T_out = None
        self.Q_required = None

    def set_target_outlet_temp(self, T_target):
        """
        Sets the desired Gas Outlet Temperature [K].
        Calculates the required Q [W] to achieve this based on Inlet Enthalpy.
        """
        self.target_T_out = float(T_target)
        
        # 1. Get Inlet State
        inlet = self.hot_stream.inlet
        
        # 2. Calculate Required Outlet Enthalpy
        try:
            h_in = inlet.h
            h_out_req = cp.PropsSI('H', 'T', self.target_T_out, 'P', inlet.P, inlet.fluid_string)
            self.Q_required = inlet.m_dot * (h_in - h_out_req)
            
        except Exception as e:
            print(f"Warning: Could not calculate target thermodynamics: {e}")
            self.Q_required = 0.0

    def add_zone(self, zone):
        current_x_offset = 0.0
        if self.zones:
            last_zone = self.zones[-1]
            last_len = last_zone.n_cols * last_zone.S_L            
            current_x_offset = last_zone.origin_x + last_len
        
        zone.origin_x = current_x_offset
        self.zones.append(zone)

    def build_geometry(self):
        for zone in self.zones:
            zone.build_geometry()

    def solve(self):
        print(f"--- Solving {self.name} ---")
        
        current_hot = self.hot_stream.inlet
        current_cold = self.cold_stream.inlet
        
        self.hot_stream.profile = [current_hot]
        self.cold_stream.profile = [current_cold]
        
        for zone in self.zones:
            print(f"  > Marching Zone: {zone.name}...")
            
            h_out, c_out, h_prof, c_prof = zone.solve(current_hot, current_cold)
            
            self.hot_stream.profile.extend(h_prof)
            self.cold_stream.profile.extend(c_prof)
            
            current_hot = h_out
            current_cold = c_out
            
        self.hot_out = current_hot
        self.cold_out = current_cold
        
        print(f"--- Complete. T_gas_out: {self.hot_out.T:.2f} K ---")
        return self.hot_out, self.cold_out

    def summary(self):
        """
        Prints a detailed physics summary of the simulation.
        Checks mass/energy balances and reports zone performance.
        """
        print(f"\n{'='*75}")
        print(f"HEAT EXCHANGER SUMMARY: {self.name}")
        print(f"{'='*75}")
        
        # 1. Global Performance
        try:
            h_g_in = self.hot_stream.inlet.h
            h_g_out = self.hot_out.h
            Q_gas = self.hot_stream.inlet.m_dot * (h_g_in - h_g_out)

            h_c_in = self.cold_stream.inlet.h
            h_c_out = self.cold_out.h
            Q_cool = self.cold_stream.inlet.m_dot * (h_c_out - h_c_in)
            
            err = abs(Q_gas - Q_cool) / max(Q_gas, 1e-6) * 100.0

            print(f"Global Energy Balance:")
            print(f"  Q_gas_actual: {Q_gas/1000.0:.3f} kW")
            print(f"  Q_cool_gain:  {Q_cool/1000.0:.3f} kW")
            print(f"  Balance Err:  {err:.4f} %")
            
            # --- REQUIREMENT CHECK ---
            if self.target_T_out is not None:
                print(f"-"*75)
                print(f"Requirement Check (Target T_out = {self.target_T_out:.1f} K):")
                print(f"  Q_Required:   {self.Q_required/1000.0:.3f} kW")
                
                margin = Q_gas - self.Q_required
                percent = (Q_gas / self.Q_required) * 100.0
                
                status = "PASS" if margin >= 0 else "FAIL"
                print(f"  Status:       {status} ({percent:.1f}% of goal)")
                print(f"  Margin:       {margin/1000.0:.3f} kW")
            
            print(f"-"*75)
            # --- CONDITIONS & DELTAS ---
            # Unit Helpers
            def to_C(T_k): return T_k - 273.15
            def to_Torr(P_pa): return P_pa / 133.322
            def to_psi(P_pa): return P_pa / 6894.76
            
            # Gas Data
            Tg_in, Pg_in = self.hot_stream.inlet.T, self.hot_stream.inlet.P
            Tg_out, Pg_out = self.hot_out.T, self.hot_out.P
            
            dT_g = Tg_in - Tg_out # Positive for cooling
            dP_g = Pg_in - Pg_out # Pressure Drop
            
            # Coolant Data
            Tc_in, Pc_in = self.cold_stream.inlet.T, self.cold_stream.inlet.P
            Tc_out, Pc_out = self.cold_out.T, self.cold_out.P
            
            dT_c = Tc_out - Tc_in # Positive for heating
            dP_c = Pc_in - Pc_out # Pressure Drop
            
            print(f"Overall Conditions:")
            print(f"  Gas Stream (Hot):")
            print(f"    Inlet:  {to_C(Tg_in):.2f} C | {to_Torr(Pg_in):.2f} Torr")
            print(f"    Outlet: {to_C(Tg_out):.2f} C | {to_Torr(Pg_out):.2f} Torr")
            print(f"    Change: -{dT_g:.2f} C   | -{to_Torr(dP_g):.2f} Torr (Drop)")
            
            print(f"  Coolant Stream (Cold):")
            print(f"    Inlet:  {to_C(Tc_in):.2f} C | {to_psi(Pc_in):.2f} psi")
            print(f"    Outlet: {to_C(Tc_out):.2f} C | {to_psi(Pc_out):.2f} psi")
            print(f"    Change: +{dT_c:.2f} C   | -{to_psi(dP_c):.2f} psi (Drop)")

            print(f"{'='*75}")
        except Exception as e:
            print(f"Could not calculate Global Energy Balance: {e}")

        # 2. Zone Breakdown
        print(f"{'ZONE':<15} | {'Q (kW)':<10} | {'h_gas':<10} | {'Re_gas':<10} | {'dP_gas (Pa)':<12}")
        print("-" * 75)
        
        for zone in self.zones:
            if not zone.results:
                print(f"{zone.name:<15} | {'(No Results)':<10}")
                continue
                
            res = zone.results
            print(f"{zone.name:<15} | "
                  f"{res['Q_total_kW']:<10.3f} | "
                  f"{res['h_gas_avg']:<10.1f} | "
                  f"{res['Re_gas_avg']:<10.0f} | "
                  f"{res['dP_gas_Pa']:<12.1f}")
        print(f"{'='*75}\n")