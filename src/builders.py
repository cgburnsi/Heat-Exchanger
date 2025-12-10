# src/builders.py
from src.assembly import HeatExchanger
from src.zones import PipeFlowZone, PlateFinZone, TubeBankZone
from src.fluids import FluidStream

class HXBuilder:
    """
    Production Builder: Converts configuration dictionaries into a HeatExchanger assembly.
    
    IMPORTANT: This builder assumes ALL geometry values in the config dictionaries
    are already converted to Base Units (Meters) before being passed in.
    """
    def __init__(self, name, physics_model):
        self.name = name
        self.model = physics_model
        self.zones = []
        
        self._creators = {
            'pipe':   self._add_pipe,
            'bare':   self._add_bare,
            'finned': self._add_finned
        }

    def add_zones_from_config(self, config_list):
        for cfg in config_list:
            z_type = cfg.get('type', 'bare').lower()
            name = cfg.get('name', f"Zone_{len(self.zones)}")
            
            creator = self._creators.get(z_type)
            if creator:
                creator(name, cfg)
            else:
                raise ValueError(f"Unknown zone type: {z_type}")
        return self

    def _add_pipe(self, name, cfg):
        # Expects: 'length', 'diameter' (in meters)
        self.zones.append(PipeFlowZone(
            name,
            length=cfg['length'],
            diameter=cfg['diameter'],
            roughness=cfg.get('roughness', 15e-6)
        ))

    def _add_bare(self, name, cfg):
        # Expects: 'width', 'height', 'tube_od' (in meters)
        zone = TubeBankZone(
            name=name,
            height=cfg.get('height', cfg['width']), # Default to square if height missing
            width=cfg['width'],
            tube_dia=cfg['tube_od'],
            R_p=cfg.get('Rp', 1.5),
            n_cols=int(cfg['tubes_deep']),
            stagger=cfg.get('stagger', True),
            model=self.model
        )
        # Explicit Geometry Overrides (in meters)
        if 'S_T' in cfg: zone.S_T = cfg['S_T']
        if 'S_L' in cfg: zone.S_L = cfg['S_L']
        
        self.zones.append(zone)

    def _add_finned(self, name, cfg):
        # Expects: 'fin_pitch', 'fin_thickness' (in meters)
        
        # Helper: Calculate height from width if not provided (Square Duct assumption)
        height = cfg.get('height', cfg['width'])
        
        self.zones.append(PlateFinZone(
            name=name,
            height=height,
            width=cfg['width'],
            tube_dia=cfg['tube_od'],
            R_p=cfg.get('Rp', 2.0),
            n_cols=int(cfg['tubes_deep']),
            fin_pitch=cfg['fin_pitch'],
            fin_thickness=cfg['fin_thickness'],
            stagger=cfg.get('stagger', True),
            model=self.model
        ))

    def build(self, hot_in, cold_in):
        hx = HeatExchanger(self.name, FluidStream(hot_in.copy()), FluidStream(cold_in.copy()))
        for z in self.zones: hx.add_zone(z)
        return hx