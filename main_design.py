from utils import convert as cv
from src.assembly import HeatExchanger
from src.fluids import FluidState, StreamType, Fluid, FluidStream
from src.zones import TubeBankZone, PipeFlowZone, PlateFinZone
from src.models import TariqModel # <--- Import the vacuum physics model
from src.viz import plot_temperature_profile, plot_pressure_profile
from src.assembly import HeatExchanger
from src.reporting.results import CompositeReporter, CsvExportReporter, MatplotlibReporter, ReportConfig


def run_simulation():
    
    # Upstream Conditions to the heat exchanger
    pip_dia = cv.convert(12, 'in', 'm')
    inlet_pipe = PipeFlowZone(
        name="Inlet Pipe",
        length=cv.convert(10, 'ft', 'm'), 
        diameter=cv.convert(12, 'in', 'm')
    )
    
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
    T_c     = cv.convert(80, 'degF', 'K')
    P_c     = cv.convert(50, 'psi', 'Pa')
    mdot_c  = cv.convert(6, 'gal/min', 'm^3/s') * 997.0  # assume density of H2O at 25 degC 
    cold_in = FluidState(name=name_c, T=T_c, P=P_c, m_dot=mdot_c, fluid=fluid_c)

    # Set Fluid Streams and Create the Heat Exchanger    
    hot_stream  = FluidStream(hot_in)
    cold_stream = FluidStream(cold_in)
    hx          = HeatExchanger("HX-1", hot_stream, cold_stream)
    

    
    
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
    
    hx.add_zone(inlet_pipe)
    hx.add_zone(zone1)
    hx.add_zone(zone2)
    hx.build_geometry()
    


    
    # Define your specific requirement
    target_temp_K = cv.convert(100, 'degC', 'K')
    hx.set_target_outlet_temp(target_temp_K)

    hx.solve()
    hx.summary()   

    # 3. Advanced Reporting
    # Create a configuration
    # Create a config (you can change output_dir here)
    config = ReportConfig(output_dir="sim_results", save_plots=True)
    
    # Combine CSV and Plotting into one runner
    reporter = CompositeReporter([
        CsvExportReporter(config),
        MatplotlibReporter(config)
    ])
    
    reporter.report(hx)
    
if __name__ == "__main__":
    run_simulation()        
  
    
 
    
    
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
    
    


    






   
    
    

   
