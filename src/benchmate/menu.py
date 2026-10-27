"""Configurable development menu. D2 must freeze the physical frequency limit."""
from dataclasses import dataclass, asdict
import numpy as np
from .physics import Acquisition


@dataclass(frozen=True)
class MenuConfig:
    min_hz: float = 1.0
    max_hz: float = 100.0
    frequency_count: int = 6
    hardware_validated: bool = False

    def __post_init__(self):
        if not 1 <= self.min_hz < self.max_hz <= 500 or self.frequency_count != 6:
            raise ValueError("Development menu needs six frequencies between 1 and 500 Hz")
        if self.hardware_validated:
            raise ValueError("A frequency configuration alone cannot certify hardware")

    def to_dict(self):
        return {**asdict(self), "frequencies_hz": np.geomspace(self.min_hz, self.max_hz, 6).tolist(),
                "status": "provisional_synthetic_grid_pending_D2"}


def measurement_menu(config=MenuConfig()):
    menu = {}
    for shunt in (0, 1000):
        for load in (None, 10000, 4700):
            suffix = f"s{shunt}_l{load or 0}"
            for amplitude in (.2, .5):
                menu[f"step_a{amplitude}_{suffix}"] = Acquisition(amplitude_v=amplitude, shunt_ohm=shunt, load_ohm=load)
            for index, frequency in enumerate(np.geomspace(config.min_hz, config.max_hz, 6)):
                for amplitude in (.2, 1.0):
                    menu[f"sine_f{index}_a{amplitude}_{suffix}"] = Acquisition(
                        kind="sine", frequency_hz=float(frequency), amplitude_v=amplitude,
                        shunt_ohm=shunt, load_ohm=load, duration_s=2/float(frequency),
                        sample_period_s=1/max(500, 50*float(frequency)), step_at_s=.001)
    menu["shunt_dc_pair"] = Acquisition(kind="dc_pair", shunt_ohm=1000, amplitude_v=1)
    return menu


def mounting_instruction(settings):
    series = "1 kΩ 션트" if settings.shunt_ohm else "0 Ω 점퍼"
    load = "제거" if settings.load_ohm is None else f"{settings.load_ohm:g} Ω 연결"
    return f"DRIVE–IN: {series}. OUT–REF: 부하 {load}. 장착 후 정착을 확인합니다."
