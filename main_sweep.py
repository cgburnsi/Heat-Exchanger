from src.studies import run_parametric_study
from src.reporting import PandasCollector

# 1. Setup
physics = TariqModel()
collector = PandasCollector() # Captures data instead of printing it

ranges = {
    'tube_od': [0.5, 0.75, 1.0, 1.25],
    'fin_density': [1.0, 2.0, 4.0]
}

# 2. Run Sweep
df = run_parametric_study(
    builder_factory=lambda: HXBuilder("Sweep", physics),
    parameter_grid=ranges,
    # ... inputs ...
    reporters=[collector] # Inject the collector
)

# 3. Analyze
print(df)
df.to_csv("trade_study.csv")