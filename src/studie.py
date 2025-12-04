def run_parametric_study(
    builder_factory,      # Function that returns a fresh HXBuilder
    parameter_grid: dict, # { 'tube_od': [0.5, 1.0], ... }
    fixed_config: dict,   # Constants
    fluids: tuple,        # (hot_in, cold_in)
    reporters: list       # List of [PandasCollector, etc.]
):
    """
    Orchestrates a multi-run study.
    1. Generates combinations from parameter_grid.
    2. configures Builder.
    3. Runs Solve.
    4. Feeds result to Reporters.
    """
    pass