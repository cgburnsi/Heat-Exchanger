from utils import convert as cv
from src.assembly import HeatExchanger
from src.fluids import FluidState, StreamType, Fluid, FluidStream
from src.zones import TubeBankZone, PipeFlowZone, PlateFinZone
from src.models import TariqModel # <--- Import the vacuum physics model
from src.viz import plot_temperature_profile, plot_pressure_profile


def HX1():
    
    # Upstream Conditions to the heat exchanger
    pip_dia = cv.convert(12, 'in', 'm')
    
    # Hot Gas Inlet Conditions
    name_g  = StreamType.GAS
    fluid_g = Fluid.N2
    T_g     = cv.convert(1800, 'degC', 'K')
    P_g     = cv.convert(5, 'Torr', 'Pa')
    mdot_g  = cv.convert(10.68, 'g/s', 'kg/s')
    hot_in  = FluidState(name=name_g, T=T_g, P=P_g, m_dot=mdot_g, fluid=fluid_g)
    
    # Coolant Inlet Conditions
    name_c  = StreamType.COOLANT
    fluid_c = Fluid.H2O
    T_c     = cv.convert(55, 'degF', 'K')
    P_c     = cv.convert(50, 'psi', 'Pa')
    mdot_c  = cv.convert(5, 'gal/min', 'm^3/s') * 997.0  # assume density of H2O at 25 degC 
    cold_in = FluidState(name=name_c, T=T_c, P=P_c, m_dot=mdot_c, fluid=fluid_c)

    # Set Fluid Streams and Create the Heat Exchanger    
    hot_stream  = FluidStream(hot_in)
    cold_stream = FluidStream(cold_in)
    hx          = HeatExchanger("HX-1", hot_stream, cold_stream)
    
    inlet_pipe = PipeFlowZone(
        name="Inlet Pipe",
        length=cv.convert(10, 'ft', 'm'), 
        diameter=cv.convert(12, 'in', 'm')
    )
    hx.add_zone(inlet_pipe)
    
    
    zone1 = TubeBankZone(
        name     = "Z1",
        height   = cv.convert(18, 'in', 'm'),
        tube_dia = cv.convert(1, 'in', 'm'),
        R_p      = 1.5,
        n_cols   = 2,
        origin_x = 0.0,
        origin_y = 0.0,
        stagger  = True,
    )    
    
    zone2 = TubeBankZone(
        name     = "Z2",
        height   = cv.convert(18, 'in', 'm'),
        tube_dia = cv.convert(1, 'in', 'm'),
        R_p      = 1.5,
        n_cols   = 20,
        #origin_x = cv.convert(10, 'in', 'm'),
        origin_y = 0.0,
        stagger  = True,
    ) 
    
    hx.add_zone(zone1)
    hx.add_zone(zone2)
    hx.build_geometry()
    


    
    # Define your specific requirement
    target_temp_K = cv.convert(100, 'degC', 'K')
    hx.set_target_outlet_temp(target_temp_K)

    hx.solve()
    hx.summary()   

    #plot_all_zones(hx.zones)
    #plot_temperature_profile(hx)
    #plot_pressure_profile(hx)


    
def HX2():
    
    # Upstream Conditions to the heat exchanger
    pip_dia = cv.convert(12, 'in', 'm')
    
    # Hot Gas Inlet Conditions
    name_g  = StreamType.GAS
    fluid_g = Fluid.N2
    T_g     = cv.convert(1300, 'degC', 'K')
    P_g     = cv.convert(5, 'Torr', 'Pa')
    mdot_g  = cv.convert(10.68, 'g/s', 'kg/s')
    hot_in  = FluidState(name=name_g, T=T_g, P=P_g, m_dot=mdot_g, fluid=fluid_g)
    
    # Coolant Inlet Conditions
    name_c  = StreamType.COOLANT
    fluid_c = Fluid.H2O
    T_c     = cv.convert(55, 'degF', 'K')
    P_c     = cv.convert(50, 'psi', 'Pa')
    mdot_c  = cv.convert(5, 'gal/min', 'm^3/s') * 997.0  # assume density of H2O at 25 degC 
    cold_in = FluidState(name=name_c, T=T_c, P=P_c, m_dot=mdot_c, fluid=fluid_c)

    # Set Fluid Streams and Create the Heat Exchanger    
    hot_stream  = FluidStream(hot_in)
    cold_stream = FluidStream(cold_in)
    hx          = HeatExchanger("HX-1", hot_stream, cold_stream)
    
    inlet_pipe = PipeFlowZone(
        name="Inlet Pipe ",
        length=cv.convert(12, 'in', 'm'), 
        diameter=cv.convert(12, 'in', 'm')
    )
    hx.add_zone(inlet_pipe)
    
    
    zone1 = PlateFinZone(
        name     = "Z1 (finned)",
        height   = cv.convert(16, 'in', 'm'),
        width    = cv.convert(16, 'in', 'm'),
        tube_dia = cv.convert(1, 'in', 'm'),
        R_p      = 1.5,
        n_cols   = 2,
        fin_pitch = cv.convert(1.0, 'in', 'm'),
        fin_thickness=cv.convert(0.125, 'in', 'm'),
        origin_x = 0.0,
        origin_y = 0.0,
        stagger  = True,
    )    

    zone2 = PlateFinZone(
        name     = "Z2 (finned)",
        height   = cv.convert(16, 'in', 'm'),
        width    = cv.convert(16, 'in', 'm'),
        tube_dia = cv.convert(1, 'in', 'm'),
        R_p      = 2.0,
        n_cols   = 20,
        fin_pitch = cv.convert(1.0, 'in', 'm'),
        fin_thickness=cv.convert(0.125, 'in', 'm'),
        origin_x = 0.0,
        origin_y = 0.0,
        stagger  = True,
    )   
    
    hx.add_zone(zone1)
    hx.add_zone(zone2)
    hx.build_geometry()
    


    
    # Define your specific requirement
    target_temp_K = cv.convert(100, 'degC', 'K')
    hx.set_target_outlet_temp(target_temp_K)

    hx.solve()
    hx.summary()   

    #plot_all_zones(hx.zones)
    #plot_temperature_profile(hx)
    #plot_pressure_profile(hx)

    


def HX3():
    """
    Design Case: Vacuum Exhaust Cooler (Tariq Model)
    """
    print("--- RUNNING HX3 DESIGN CASE (TARIQ PHYSICS) ---")

    # 1. Define Inlet States
    hot_in = FluidState(
        name=StreamType.GAS,
        T=1800.0, 
        P=661.6, 
        m_dot=0.0168, 
        fluid=Fluid.NITROGEN 
    )
    
    cold_in = FluidState(
        name=StreamType.COOLANT, 
        T=280.0, 
        P=3.0e5, 
        m_dot=0.1000, 
        fluid=Fluid.WATER 
    )
    
    # 2. Create Assembly
    hot_stream  = FluidStream(hot_in)
    cold_stream = FluidStream(cold_in)
    hx = HeatExchanger("HX-3 (Vacuum)", hot_stream, cold_stream)
    
    # Define Target Requirement
    hx.set_target_outlet_temp(cv.convert(100, 'degC', 'K'))

    # 3. Create Physics Model
    tariq_physics = TariqModel()

    # 4. Add Zones
    
    # Inlet Pipe
    inlet_pipe = PipeFlowZone(
        name="Inlet Pipe",
        length=cv.convert(12, 'in', 'm'), # 10 ft pipe run
        diameter=cv.convert(12, 'in', 'm')
    )
    hx.add_zone(inlet_pipe)

    # Zone 1: Inlet (Finned, Dense)
    # Using PlateFinZone with Tariq Model injection
    zone1 = PlateFinZone(
        name="Z1 (Finned)",
        height=cv.convert(16, 'in', 'm'),
        width=cv.convert(16, 'in', 'm'),
        tube_dia=cv.convert(1, 'in', 'm'),
        R_p=1.5,
        n_cols=2,
        fin_pitch=cv.convert(1.0, 'in', 'm'),     
        fin_thickness=cv.convert(0.125, 'in', 'm'),
        stagger=True,
        model=tariq_physics  # <--- Inject Physics Here
    )    
    hx.add_zone(zone1)
    
    # Zone 2: Bulk (Finned, Loose)
    zone2 = PlateFinZone(
        name="Z2 (Finned)",
        height=cv.convert(16, 'in', 'm'),
        width=cv.convert(16, 'in', 'm'),
        tube_dia=cv.convert(1, 'in', 'm'),
        R_p=2.0,
        n_cols=12,
        fin_pitch=cv.convert(1.0, 'in', 'm'),
        fin_thickness=cv.convert(0.125, 'in', 'm'),
        stagger=True,
        model=tariq_physics  # <--- Inject Physics Here
    ) 
    hx.add_zone(zone2)

    # 5. Run
    hx.solve()
    
    # 6. Visualize & Report
    hx.summary()
    #plot_temperature_profile(hx)
    #plot_pressure_profile(hx)

if __name__ == "__main__":
    HX3()

if __name__ == "__main__":

        #HX1()
        
        #HX2()

        HX3()
            
  
    
 
    
    
'''    
        # HX Upstream Conditions and Configuration
        self.pipe_inlet_ID              = cv.convert(12, 'in', 'm')         # [m] Pipe leading to the HX inlet
        self.fld_coolant                = 'Water'                           # [-] Coolant Fluid
        self.t_w                        = cv.convert(0.035, 'in',' m')      # [m] Tube Wall Thickness
        self.p_fin                      = cv.convert(1.0, 'in', 'm')            # [m] Fin Pitch (Distance between fins)
        self.t_fin                      = cv.convert(0.125, 'in', 'm')          # [m] Fin thickness
        self.D_t                        = cv.convert(1.0, 'in', 'm')            # [m] Tube Outer Diameter
        self.R_p                        = 2.0                                   # [-] Tube Bank Pitch-to-Diameter Ratio
        
        self.m_dot_cool=0.25
        self.e_roughness                = 15e-6                             # [m] Internal tube roughness (per PDF)
        self.k_wall                     = 16.2                              # [W/m-K] Thermal conductivity of tube wall (e.g., 304 SS)

        self.T_gas_out                  = cv.convert(100, 'degC', 'K')          # [K] Desired HX Outlet Temperature
        self.T_coolant_in               = cv.convert(50, 'degF', 'K')           # [K] Temperature of Coolant at Inlet
        self.P_coolant_in               = cv.convert(50, 'psi', 'Pa')               # [Pa] Pressure of Coolant at Inlet
    
        self.upstream_gas_vel           = self._get_upstream_gas_velocity() # [m/s] Upstream gas velocity coming into the HX
        
        self.D_t_inner                  = self.D_t - 2.0 * self.t_w         # [m] Tube Inner Diameter
        self.k_config                   = self.Tube_Configuration()         # [-] Tube Layout Geometry (Staggered vs. inline)
        self.S_T                        = self.R_p * self.D_t               # [m] Transverse Pitch (center to center of tubes)
        self.S_L                        = self.S_T * self.k_config          # [m] Lateral Pitch 
        self.H_hx                       = self.Calculate_HX_Height()        # [m] Height of Heat Exchanger
        self.L_fin                      = self.Calculate_Fin_Length()       # [m] Length of Fins (Also is the length of HX too)
        self.N_fins                     = self.Calculate_Num_of_Fins()      # [-] Number of fins based on fin pitch
        self.A_front                    = self.Calculate_Front_Area()       # [m**2] Cross Sectional Area (no internals in HX)
        self.A_front_fins               = self.Calculate_Fin_Front_Area()   # [m**2] Frontal Area of the Fin Faces
        self.A_front_tubes              = self.Calculate_Tube_Front_Area()  # [m**2] Frontal Area of Tubes in the first Column
        self.A_gas_flow                 = self.Calculate_Gas_Front_Area()   # [m**2] Open Frontal Area for Gas Flow
'''   
    
    


    






   
    
    

   
