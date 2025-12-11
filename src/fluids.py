import CoolProp.CoolProp as cp
from enum import Enum

class StreamType(str, Enum):
    GAS     = 'gas'
    COOLANT = 'coolant'    

class Fluid(str, Enum):
    CO2     = 'CarbonDioxide'
    CO      = 'CarbonMonoxide'
    HE      = 'Helium'
    H2      = 'Hydrogen'
    H2O     = 'Water'
    N2      = 'Nitrogen'
    O2      = 'Oxygen'
    WATER   = 'Water'
    NITROGEN = 'Nitrogen'
    AIR     = 'Air'
    
class FluidState:
    ''' Thermodynamic State for a Single Stream (Gas or Coolant).
        T (Temperature) and P (Pressure) are the Independent Property Inputs.
        density, Specific Heat, Viscosity, etc. are calculated on demand.
        Fluid can be a mixture or single species.
    '''
    def __init__(self, name,T, P, m_dot, fluid, x=0.0):        
        self.name      = name           # [StreamType] Type of Fluid (gas or coolant)
        self.T         = float(T)       # [K] Fluid Temperature
        self.P         = float(P)       # [Pa] Fluid Pressure
        self.m_dot     = float(m_dot)   # [kg/s] Fluid Mass Flowrate
        self.fluid_obj = fluid          # [Fluid or Dict] Input String for CoolProp
        self.x         = float(x)       # [m] Position along Heat Exchanger
        
        self.fluid_string = self._parse_fluid(fluid)    # Convert input fluid to CoolProp format

    def _parse_fluid(self, fluid_input):
        """
        Converts the input into a CoolProp-compatible string.
        """
        # CASE A: Simple String (Legacy support for "N2", "Water")
        if isinstance(fluid_input, str):
            return fluid_input

        # CASE B: Pure Fluid (Enum) -> "Nitrogen"
        elif isinstance(fluid_input, Fluid):
            return fluid_input.value
            
        # CASE C: Mixture (Dict) -> "HEOS::Nitrogen[0.7]&Helium[0.3]"
        elif isinstance(fluid_input, dict):
            # 1. Start with Backend (HEOS is standard for mixtures)
            s = "HEOS::"
            
            # 2. Build components list
            components = []
            for fluid_key, fraction in fluid_input.items():
                # Handle dictionary keys being Enum or String
                name = fluid_key.value if isinstance(fluid_key, Fluid) else str(fluid_key)
                components.append(f"{name}[{fraction}]")
            
            # 3. Join with ampersand
            return s + "&".join(components)
        
        else:
            raise ValueError(f"Fluid input '{fluid_input}' not recognized. Must be str, Fluid Enum, or Dict.")

    # --- DYNAMIC PROPERTIES ---
    # These use self.fluid_string instead of self.fluid
    
    @property
    def rho(self): return cp.PropsSI('D', 'T', self.T, 'P', self.P, self.fluid_string)

    @property
    def cp(self):  return cp.PropsSI('C', 'T', self.T, 'P', self.P, self.fluid_string)
        
    @property
    def mu(self):  return cp.PropsSI('V', 'T', self.T, 'P', self.P, self.fluid_string)

    @property
    def k(self):   return cp.PropsSI('L', 'T', self.T, 'P', self.P, self.fluid_string)

    @property
    def pr(self):  return cp.PropsSI('Prandtl', 'T', self.T, 'P', self.P, self.fluid_string)

    @property
    def M(self):   return cp.PropsSI('M', self.fluid_string)

    @property
    def h(self):   return cp.PropsSI('H', 'T', self.T, 'P', self.P, self.fluid_string)

    @property
    def s(self):   return cp.PropsSI('S', 'T', self.T, 'P', self.P, self.fluid_string)

    # --- UTILITIES ---

    def copy(self):
        return FluidState(
            name=self.name,
            T=self.T,
            P=self.P,
            m_dot=self.m_dot,
            fluid=self.fluid_obj, # Pass the original object (Dict/Enum/Str)
            x=self.x
        )

    def __repr__(self):
        return f"<{self.name} @ x={self.x:.3f}: T={self.T:.1f} K, P={self.P:.0f} Pa>"


class FluidStream:
    """
    Wraps inlet/outlet states and stores the profile history.
    """
    def __init__(self, inlet_state):
        self.inlet = inlet_state
        self.outlet = inlet_state.copy()
        self.profile = []

    def set_outlet(self, state):
        self.outlet = state

    def add_profile_point(self, state):
        self.profile.append(state)

    def get_data(self):
        """Helper to get arrays for plotting (x, T, P)"""
        x = [s.x for s in self.profile]
        T = [s.T for s in self.profile]
        P = [s.P for s in self.profile]
        return x, T, P
    
    
    
    
if __name__ == "__main__":
    print("--- RUNNING FLUID MODULE TESTS ---")

    # TEST 1: Pure Fluid via Enum (The Standard Way)
    print("\n[Test 1] Pure Nitrogen (Enum)")
    try:
        state_pure = FluidState(
            name=StreamType.GAS,
            T=300.0, P=101325.0, m_dot=0.5,
            fluid=Fluid.N2
        )
        print(f"  Success: Created {state_pure}")
        print(f"  Density: {state_pure.rho:.4f} kg/m^3")
        print(f"  CP String: '{state_pure.fluid_string}'")
    except Exception as e:
        print(f"  FAILED: {e}")

    # TEST 2: Binary Mixture (The Dictionary Way)
    print("\n[Test 2] 80% N2 / 20% CO2 Mixture (Dict)")
    try:
        mix_def = {Fluid.N2: 0.8, Fluid.CO2: 0.2}
        state_mix = FluidState(
            name=StreamType.GAS,
            T=300.0, P=101325.0, m_dot=0.5,
            fluid=mix_def
        )
        print(f"  Success: Created {state_mix}")
        print(f"  Density: {state_mix.rho:.4f} kg/m^3 (Should be lighter than pure N2)")
        print(f"  Molar Mass: {state_mix.M*1000:.2f} g/mol")
        print(f"  CP String: '{state_mix.fluid_string}'")
    except Exception as e:
        print(f"  FAILED: {e}")

    # TEST 3: Legacy String Support
    print("\n[Test 3] Legacy String 'Water'")
    try:
        state_legacy = FluidState(
            name="coolant", # String role
            T=300.0, P=101325.0, m_dot=1.0,
            fluid="Water"   # String fluid
        )
        print(f"  Success: Created {state_legacy}")
        print(f"  Density: {state_legacy.rho:.4f} kg/m^3")
    except Exception as e:
        print(f"  FAILED: {e}")

    # TEST 4: Error Handling (Invalid Input)
    print("\n[Test 4] Invalid Input (Should Fail)")
    try:
        state_bad = FluidState(StreamType.GAS, 300, 1e5, 1.0, fluid=12345)
    except ValueError as e:
        print(f"  CAUGHT EXPECTED ERROR: {e}")
    except Exception as e:
        print(f"  UNEXPECTED ERROR: {e}")