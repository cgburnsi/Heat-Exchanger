# builders.py
from utils import convert as cv
from src.assembly import HeatExchanger
from src.fluids import FluidStream
from src.zones import PipeFlowZone, TubeBankZone, PlateFinZone

_ZONE_REGISTRY = {}

def register_zone(kind):
    def deco(fn):
        _ZONE_REGISTRY[kind] = fn
        return fn
    return deco

def _req(cfg, key):
    if key not in cfg:
        raise KeyError(f"Missing required key '{key}' in zone config: {cfg}")
    return cfg[key]

def _in_to_m(x):  # tiny unit adapter keeps cv.convert out of your business logic
    return cv.convert(x, "in", "m")

@register_zone("pipe")
def make_pipe(name, cfg, model):
    return PipeFlowZone(
        name,
        length=_in_to_m(_req(cfg, "length_in")),
        diameter=_in_to_m(_req(cfg, "diameter_in")),
        roughness=cfg.get("roughness", 15e-6),
    )

@register_zone("bare")
def make_bare(name, cfg, model):
    zone = TubeBankZone(
        name=name,
        height=_in_to_m(_req(cfg, "width_in")),   # (see note below)
        width=_in_to_m(_req(cfg, "width_in")),
        tube_dia=_in_to_m(_req(cfg, "tube_od_in")),
        R_p=cfg.get("Rp", 1.5),
        n_cols=int(_req(cfg, "tubes_deep")),
        stagger=cfg.get("stagger", True),
        model=model,
    )
    if "S_T_in" in cfg: zone.S_T = _in_to_m(cfg["S_T_in"])
    if "S_L_in" in cfg: zone.S_L = _in_to_m(cfg["S_L_in"])
    return zone

@register_zone("finned")
def make_finned(name, cfg, model):
    p_fin_in = 1.0 / cfg.get("fpi", 1.0)
    return PlateFinZone(
        name=name,
        height=_in_to_m(_req(cfg, "width_in")),
        width=_in_to_m(_req(cfg, "width_in")),
        tube_dia=_in_to_m(_req(cfg, "tube_od_in")),
        R_p=cfg.get("Rp", 2.0),
        n_cols=int(_req(cfg, "tubes_deep")),
        fin_pitch=_in_to_m(p_fin_in),
        fin_thickness=_in_to_m(cfg.get("fin_thick_in", 0.012)),
        stagger=cfg.get("stagger", True),
        model=model,
    )

def build_hx(name, physics_model, zone_config_list, hot_inlet, cold_inlet):
    hx = HeatExchanger(
        name,
        FluidStream(hot_inlet.copy()),
        FluidStream(cold_inlet.copy()),
    )

    for i, cfg in enumerate(zone_config_list):
        kind = cfg.get("type", "bare").lower()
        zname = cfg.get("name", f"Zone_{i}")

        try:
            maker = _ZONE_REGISTRY[kind]
        except KeyError:
            raise ValueError(f"Unknown zone type '{kind}'. Valid: {sorted(_ZONE_REGISTRY)}")

        hx.add_zone(maker(zname, cfg, physics_model))

    return hx
