from src.builders import HXBuilder
from src.models import TariqModel
from src.reporting import ConsoleSummaryReporter, MatplotlibReporter

# 1. Select your Strategy (Dependency Injection)
physics = TariqModel() 
reporters = [ConsoleSummaryReporter(), MatplotlibReporter()]

# 2. Configure the Builder
builder = HXBuilder("Vacuum_Design_1", physics)
builder.add_inlet(12, 12)
builder.add_core_zone(16, 12, 1.0)

# 3. Run
hx = builder.build(hot_in, cold_in)
hx.solve()

# 4. Output
for rep in reporters:
    rep.report(hx)