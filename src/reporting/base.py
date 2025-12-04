from abc import ABC, abstractmethod

class SimulationReporter(ABC):
    """Abstract Observer for Simulation Results"""
    
    @abstractmethod
    def report(self, hx_assembly: 'HeatExchanger', run_meta: dict = None):
        """
        Process the results of a simulation.
        
        Args:
            hx_assembly: The solved Heat Exchanger object.
            run_meta: Optional dict of input parameters (for parametric sweeps).
        """
        pass