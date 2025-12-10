# run_design.py
from utils import convert as cv
from src.fluids import FluidState, StreamType, Fluid
from src.models import TariqModel
from src.builders import HXBuilder
from src.reporting.results import CompositeReporter, ConsoleSummaryReporter, MatplotlibReporter

def main():
    print("--- STARTING CALC ---")

    # 1. PHYSICS & BOUNDARY CONDITIONS
    physics_model = TariqModel()
    hot_in        = FluidState(StreamType.GAS,
                               T     = cv.convert(1900, 'degC', 'K'), 
                               P     = cv.convert(5, 'Torr', 'Pa'), 
                               m_dot = cv.convert(10.68, 'g/s', 'kg/s'), 
                               fluid = Fluid.N2)
    cold_in       = FluidState(StreamType.COOLANT, 
                               T     = cv.convert(80, 'degF', 'K'), 
                               P     = cv.convert(50, 'psi', 'Pa'), 
                               m_dot = cv.convert(1.0, 'lb/s', 'kg/s'), 
                               fluid = Fluid.WATER)

    # 2. HARDWARE DEFINITION
    hardware_config = [
        # Inlet Pipe
        {
            'type': 'pipe',   
            'name': 'Inlet Pipe', 
            'length':   cv.convert(1, 'ft', 'm'), 
            'diameter': cv.convert(12, 'in', 'm')
        },
        # Dense Section
        {
            'type': 'finned', 
            'name': 'Zone 1 (Dense)', 
            'width':         cv.convert(16, 'in', 'm'),
            # 'height':      cv.convert(16, 'in', 'm'), # Optional, defaults to width if missing
            'tube_od':       cv.convert(1.0, 'in', 'm'),
            'tubes_deep':    2,
            'Rp':            1.5,
            'fin_pitch':     cv.convert(1.0/4.0, 'in', 'm'), # 4 Fins Per Inch
            'fin_thickness': cv.convert(0.012, 'in', 'm')
        },
        # Bulk Section
        {
            'type': 'finned', 
            'name': 'Zone 2 (Bulk)', 
            'width':         cv.convert(16, 'in', 'm'),
            'tube_od':       cv.convert(1.0, 'in', 'm'),
            'tubes_deep':    10,
            'Rp':            2.0,
            'fin_pitch':     cv.convert(1.0/8.0, 'in', 'm'), # 8 Fins Per Inch
            'fin_thickness': cv.convert(0.012, 'in', 'm')
        }
    ]

    # 3. BUILD & SOLVE
    builder = HXBuilder("Vacuum_Cooler_v1", physics_model)
    builder.add_zones_from_config(hardware_config)
    
    hx = builder.build(hot_in, cold_in)
    hx.solve()

    # 4. REPORTING
    reporters = CompositeReporter([
        ConsoleSummaryReporter(target_temp_k=cv.convert(100, 'degC', 'K')),
        MatplotlibReporter()
    ])
    reporters.report(hx)

if __name__ == "__main__":
    main()