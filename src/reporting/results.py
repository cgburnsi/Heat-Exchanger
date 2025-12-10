import os
import csv
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import List, Any
from .base import SimulationReporter

@dataclass
class ReportConfig:
    """Configuration for output directories and formatting."""
    output_dir: str = "output"
    save_plots: bool = True
    show_plots: bool = True
    csv_delimiter: str = ","

class CompositeReporter(SimulationReporter):
    """
    Allows multiple reporters to run in sequence (e.g., print summary + plot + save CSV).
    """
    def __init__(self, reporters: List[SimulationReporter]):
        self.reporters = reporters

    def report(self, hx_assembly: Any, run_meta: dict = None):
        for reporter in self.reporters:
            reporter.report(hx_assembly, run_meta)

class ConsoleSummaryReporter(SimulationReporter):
    """
    Prints the standard text summary table to the console.
    Optionally checks against a target temperature.
    """
    def __init__(self, target_temp_k=None):
        self.target = target_temp_k

    def report(self, hx_assembly: Any, run_meta: dict = None):
        # 1. Print Standard Physics Summary (Delegates to HX object)
        hx_assembly.summary()
        
        # 2. Print Target Check
        if self.target:
            actual_T = hx_assembly.hot_out.T
            print("-" * 60)
            if actual_T <= self.target:
                print(f"[PASS] Goal {self.target:.1f} K met (Actual: {actual_T:.1f} K)")
            else:
                print(f"[FAIL] Goal {self.target:.1f} K missed (Actual: {actual_T:.1f} K)")
            print("-" * 60)

class MatplotlibReporter(SimulationReporter):
    """
    Generates standard temperature and pressure profile plots.
    """
    def __init__(self, config: ReportConfig = ReportConfig()):
        self.config = config
        if self.config.save_plots:
            os.makedirs(self.config.output_dir, exist_ok=True)

    def report(self, hx_assembly: Any, run_meta: dict = None):
        # We assume viz functions are available. 
        # Ideally, we import them here to avoid circular deps if viz imports assembly.
        from src.viz import plot_temperature_profile, plot_pressure_profile
        
        # Plot Temperature
        plot_temperature_profile(hx_assembly)
        if self.config.save_plots:
            plt.savefig(os.path.join(self.config.output_dir, f"{hx_assembly.name}_temp.png"))
        
        # Plot Pressure
        plot_pressure_profile(hx_assembly)
        if self.config.save_plots:
            plt.savefig(os.path.join(self.config.output_dir, f"{hx_assembly.name}_press.png"))
            
        if self.config.show_plots:
            plt.show()

class CsvExportReporter(SimulationReporter):
    """
    Exports the Hot and Cold stream profiles to a CSV file.
    """
    def __init__(self, config: ReportConfig = ReportConfig()):
        self.config = config
        os.makedirs(self.config.output_dir, exist_ok=True)

    def report(self, hx_assembly: Any, run_meta: dict = None):
        safe_name = hx_assembly.name.replace(' ', '_')
        filename = f"{safe_name}_results.csv"
        filepath = os.path.join(self.config.output_dir, filename)
        
        print(f"Exporting CSV to: {filepath}")
        
        # Extract profiles
        hot_data = hx_assembly.hot_stream.profile
        cold_data = hx_assembly.cold_stream.profile
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=self.config.csv_delimiter)
            
            # Header
            writer.writerow(['Position_m', 'Hot_T_K', 'Hot_P_Pa', 'Cold_T_K', 'Cold_P_Pa'])
            
            # Data Rows
            # Assuming profiles are aligned by index (from marching solver)
            for h, c in zip(hot_data, cold_data):
                writer.writerow([
                    f"{h.x:.4f}", 
                    f"{h.T:.2f}", f"{h.P:.2f}",
                    f"{c.T:.2f}", f"{c.P:.2f}"
                ])