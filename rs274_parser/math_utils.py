import math

from .types import TNumber


def to_deg(radians: TNumber) -> float:
    return radians * 180 / math.pi


def to_rad(degrees: TNumber) -> float:
    return degrees * math.pi / 180
