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
    show_plots: bool = False
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

class CsvExportReporter(SimulationReporter):
    """
    Exports the Hot and Cold stream profiles to a CSV file.
    """
    def __init__(self, config: ReportConfig = ReportConfig()):
        self.config = config
        os.makedirs(self.config.output_dir, exist_ok=True)

    def report(self, hx_assembly: Any, run_meta: dict = None):
        filename = f"{hx_assembly.name.replace(' ', '_')}_results.csv"
        filepath = os.path.join(self.config.output_dir, filename)
        
        print(f"   > Exporting CSV to {filepath}...")
        
        hot_prof = hx_assembly.hot_stream.profile
        cold_prof = hx_assembly.cold_stream.profile
        
        with open(filepath, mode='w', newline='') as f:
            writer = csv.writer(f, delimiter=self.config.csv_delimiter)
            
            # Write Header
            header = ["Node", "Hot_T_K", "Hot_P_Pa", "Cold_T_K", "Cold_P_Pa"]
            writer.writerow(header)
            
            # Write Rows
            for i in range(min(len(hot_prof), len(cold_prof))):
                h = hot_prof[i]
                c = cold_prof[i]
                
                # Safely get attributes (works if state is object or dict)
                h_T = getattr(h, 'T', 0)
                h_P = getattr(h, 'P', 0)
                c_T = getattr(c, 'T', 0)
                c_P = getattr(c, 'P', 0)
                
                writer.writerow([i, f"{h_T:.2f}", f"{h_P:.0f}", f"{c_T:.2f}", f"{c_P:.0f}"])

class MatplotlibReporter(SimulationReporter):
    """
    Generates engineering plots for Temperature and Pressure vs Length.
    """
    def __init__(self, config: ReportConfig = ReportConfig()):
        self.config = config
        os.makedirs(self.config.output_dir, exist_ok=True)

    def report(self, hx_assembly: Any, run_meta: dict = None):
        print(f"   > Generating plots for {hx_assembly.name}...")
        
        # 1. Unpack Profiles
        hot_prof = hx_assembly.hot_stream.profile
        cold_prof = hx_assembly.cold_stream.profile
        
        hot_T = [getattr(s, 'T', 0) for s in hot_prof]
        cold_T = [getattr(s, 'T', 0) for s in cold_prof]
        hot_P = [getattr(s, 'P', 0) for s in hot_prof]
        cold_P = [getattr(s, 'P', 0) for s in cold_prof]
        
        # 2. Reconstruct X-Axis (Physical Position)
        # We try to map the flat profile list back to the physical zones.
        x_axis = [0.0] # Inlet is at x=0
        current_x = 0.0
        
        # Check if profile length matches our geometric expectation
        # (Assumes 1 solver step per column in the zone)
        expected_steps = sum(getattr(z, 'n_cols', 0) for z in hx_assembly.zones)
        actual_steps = len(hot_prof) - 1 # Minus inlet
        
        use_physical_x = False
        
        if actual_steps == expected_steps and expected_steps > 0:
            use_physical_x = True
            for zone in hx_assembly.zones:
                n_cols = getattr(zone, 'n_cols', 0)
                s_l = getattr(zone, 'S_L', 0)
                origin = getattr(zone, 'origin_x', current_x)
                
                # Generate X points for this zone
                for i in range(n_cols):
                    pos = origin + (i + 1) * s_l
                    x_axis.append(pos)
                
                current_x = origin + n_cols * s_l
        else:
            # Fallback if counts don't match (e.g. adaptive steps used)
            if expected_steps > 0:
                print(f"   [Warning] Profile points ({actual_steps}) != Geometry columns ({expected_steps}). Plotting by Index.")
            x_axis = list(range(len(hot_prof)))

        # 3. Plot Temperature Profile
        self._plot_temperature(hx_assembly, x_axis, hot_T, cold_T, use_physical_x)

        # 4. Plot Pressure Drop
        self._plot_pressure(hx_assembly, x_axis, hot_P, cold_P, use_physical_x)

    def _plot_temperature(self, hx, x, hot, cold, physical_x):
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(x, hot, 'r-', label='Hot Stream (Gas)', linewidth=2)
        ax.plot(x, cold, 'b-', label='Cold Stream (Coolant)', linewidth=2)
        
        xlabel = 'Position [m]' if physical_x else 'Simulation Node Index'
        ax.set_xlabel(xlabel)
        ax.set_ylabel('Temperature [K]')
        ax.set_title(f'Temperature Profile: {hx.name}')
        ax.grid(True, which='both', linestyle='--', alpha=0.7)
        ax.legend(loc='best')
        
        # Add Zone Boundaries
        if physical_x:
            self._add_zone_markers(ax, hx, hot, cold)

        # Target Line
        if getattr(hx, 'target_T_out', None):
            ax.axhline(y=hx.target_T_out, color='g', linestyle=':', label='Target Out')
            ax.legend()

        self._save(fig, f"{hx.name}_temp_profile.png")

    def _plot_pressure(self, hx, x, hot, cold, physical_x):
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        xlabel = 'Position [m]' if physical_x else 'Simulation Node Index'
        color = 'tab:red'
        ax1.set_xlabel(xlabel)
        ax1.set_ylabel('Hot Stream Pressure [Pa]', color=color)
        ax1.plot(x, hot, color=color, linestyle='--')
        ax1.tick_params(axis='y', labelcolor=color)

        ax2 = ax1.twinx()  
        color = 'tab:blue'
        ax2.set_ylabel('Cold Stream Pressure [Pa]', color=color) 
        ax2.plot(x, cold, color=color, linestyle='--')
        ax2.tick_params(axis='y', labelcolor=color)
        
        plt.title(f'Pressure Drop: {hx.name}')
        
        if physical_x:
             # Just draw vertical lines, no text to avoid clutter
            for zone in hx.zones:
                ax1.axvline(x=zone.origin_x, color='k', linestyle=':', alpha=0.2)

        self._save(fig, f"{hx.name}_pressure_profile.png")

    def _add_zone_markers(self, ax, hx, hot, cold):
        """Draws vertical lines for zone boundaries."""
        y_min, y_max = min(min(hot), min(cold)), max(max(hot), max(cold))
        y_mid = (y_min + y_max) / 2
        
        for zone in hx.zones:
            ax.axvline(x=zone.origin_x, color='k', linestyle=':', alpha=0.4)
            ax.text(zone.origin_x, y_mid, f" {zone.name}", rotation=90, verticalalignment='center', alpha=0.5)

    def _save(self, fig, filename):
        if self.config.save_plots:
            path = os.path.join(self.config.output_dir, filename.replace(" ", "_"))
            plt.savefig(path)
            print(f"     Saved: {path}")
        if self.config.show_plots:
            plt.show()
        plt.close(fig)