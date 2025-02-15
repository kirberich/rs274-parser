from typing import get_args

from rs274_parser.types import (
    BINARY_OPERATOR,
    L1_OPERATOR,
    L2_OPERATOR,
    L3_OPERATOR,
    UNARY_OPERATOR,
    WordInfo,
)

L1_OPERATORS: list[L1_OPERATOR] = ["+", "-", "and", "or", "xor"]
L2_OPERATORS: list[L2_OPERATOR] = ["*", "/"]
L3_OPERATORS: list[L3_OPERATOR] = ["**"]
BINARY_OPERATORS: list[BINARY_OPERATOR] = [
    "+",
    "-",
    "and",
    "or",
    "xor",
    "*",
    "/",
    "**",
]
UNARY_OPERATORS: list[UNARY_OPERATOR] = list(get_args(UNARY_OPERATOR))


# NOTE: There are some assumptions and probably some inaccuracies in the order of execution here,
# the spec is a bit confusing

# These letters are generally arguments to words like "X" "I", "F" etc, rather than commands in their own right
# However, the words F<something>, S<something> and T<something> can be executed on their own and do act like G/M words - they don't count as modal, even though they
# change the machine state, so they all go into modal group 0 until someone tells me otherwise

# Note that having an ordering for arguments doesn't really make sense
LETTERS = {
    "F": WordInfo(name="Set feedrate", modal_group=0, ordering=30),
    "S": WordInfo(name="Set spindle RPM", modal_group=0, ordering=40),
    "T": WordInfo(name="Select tool", modal_group=0, ordering=50),
    # Axes
    "X": WordInfo(name="X coordinate", modal_group=0, ordering=999),
    "Y": WordInfo(name="Y coordinate", modal_group=0, ordering=999),
    "Z": WordInfo(name="Z coordinate", modal_group=0, ordering=999),
    "A": WordInfo(name="A coordinate", modal_group=0, ordering=999),
    "B": WordInfo(name="B coordinate", modal_group=0, ordering=999),
    "C": WordInfo(name="C coordinate", modal_group=0, ordering=999),
    # Tool compensation
    "D": WordInfo(name="Tool compensation radius", modal_group=0, ordering=999),
    "H": WordInfo(name="Tool length offset index", modal_group=0, ordering=999),
    # Arcs
    "I": WordInfo(name="X-axis offset for arcs or G87 canned cycles", modal_group=0, ordering=999),
    "J": WordInfo(name="Y-axis offset for arcs or G87 canned cycles", modal_group=0, ordering=999),
    "K": WordInfo(name="Z-axis offset for arcs or G87 canned cycles", modal_group=0, ordering=999),
    # Misc/general
    "G": WordInfo(name="General function", modal_group=0, ordering=999),
    "L": WordInfo(
        name="Number of repetetitions of canned cycle, key used in G10",
        modal_group=0,
        ordering=999,
    ),
    "M": WordInfo(name="Miscellaneous", modal_group=0, ordering=999),
    "P": WordInfo(
        name="Dwell time in canned cycles or G4, key used in G10",
        modal_group=0,
        ordering=999,
    ),
    "Q": WordInfo(name="Feed increment in G83 canned cycle", modal_group=0, ordering=999),
    "R": WordInfo(name="Arc radius, canned cycle plane", modal_group=0, ordering=999),
}

# NOTE: the orderings are defined with space in between to leave room for other dialects to put commands in between
WORDS = {
    # Non-modal
    "G4": WordInfo(name="dwell", modal_group=0, ordering=100),
    "G10": WordInfo(name="Cordinate system or tool table data", modal_group=0, ordering=190),
    "G28": WordInfo(name="Go/set predefined Position", modal_group=0, ordering=190),
    "G30": WordInfo(name="Go/set predefined Position", modal_group=0, ordering=190),
    "G53": WordInfo(name="Move in machine moordinates", modal_group=0, ordering=200),
    "G92": WordInfo(name="Coordinate system offset", modal_group=0, ordering=190),
    "G92.1": WordInfo(name="Reset G92 offsets", modal_group=0, ordering=190),
    "G92.2": WordInfo(name="Reset G92 offsets", modal_group=0, ordering=190),
    "G92.3": WordInfo(name="Restore G92 offsets", modal_group=0, ordering=190),
    # GCode modal group 1
    "G0": WordInfo(name="Rapid move", modal_group=1, ordering=210),
    "G1": WordInfo(name="Linear move", modal_group=1, ordering=210),
    "G2": WordInfo(name="Clockwise arc", modal_group=1, ordering=210),
    "G3": WordInfo(name="Counterclockwise arc", modal_group=1, ordering=210),
    "G38.2": WordInfo(name="Straight probe (towards piece with alarm)", modal_group=1, ordering=210),
    "G80": WordInfo(name="Cancel canned cycle", modal_group=1, ordering=210),
    "G81": WordInfo(name="Drilling cycle", modal_group=1, ordering=210),
    "G82": WordInfo(name="Drilling cycle, dwell", modal_group=1, ordering=210),
    "G83": WordInfo(name="Drilling cycle, peck", modal_group=1, ordering=210),
    "G84": WordInfo(name="Right-hand tapping cycle, dwell", modal_group=1, ordering=210),
    "G85": WordInfo(name="Boring cycle, feed Out", modal_group=1, ordering=210),
    "G86": WordInfo(name="Boring cycle, dwell", modal_group=1, ordering=210),
    "G87": WordInfo(name="Back boring cycle", modal_group=1, ordering=210),
    "G88": WordInfo(name="Boring cycle, dwell", modal_group=1, ordering=210),
    "G89": WordInfo(name="Boring cycle, dwell", modal_group=1, ordering=210),
    # GCode modal group 2
    "G17": WordInfo(name="Select XY plane", modal_group=2, ordering=110),
    "G18": WordInfo(name="Select ZX plane", modal_group=2, ordering=110),
    "G19": WordInfo(name="Select YZ plane", modal_group=2, ordering=110),
    # GCode modal group 3
    "G90": WordInfo(name="Absolute distance mode", modal_group=3, ordering=170),
    "G91": WordInfo(name="Incremental distance mode", modal_group=3, ordering=170),
    # GCode modal group 5
    "G93": WordInfo(name="Inverse time mode", modal_group=5, ordering=20),
    "G94": WordInfo(name="Units per minute mode", modal_group=5, ordering=20),
    # GCode modal group 6
    "G20": WordInfo(name="Use inches", modal_group=6, ordering=120),
    "G21": WordInfo(name="Use mm", modal_group=6, ordering=120),
    # GCode modal group 7
    "G40": WordInfo(name="Cutter radius compensation off", modal_group=7, ordering=130),
    "G41": WordInfo(name="Cutter compensation (left of path)", modal_group=7, ordering=130),
    "G42": WordInfo(name="Cutter compensation (right of path)", modal_group=7, ordering=130),
    # GCode modal group 8
    "G43": WordInfo(name="Tool length offset", modal_group=8, ordering=140),
    "G49": WordInfo(name="Cancel tool length compensation", modal_group=8, ordering=140),
    # GCode modal group 10
    "G98": WordInfo(name="Canned cycle return level", modal_group=10, ordering=180),
    "G99": WordInfo(name="Canned cycle return level", modal_group=10, ordering=180),
    # GCode modal group 12
    "G54": WordInfo(name="Select coordinate system 1", modal_group=12, ordering=150),
    "G55": WordInfo(name="Select coordinate system 2", modal_group=12, ordering=150),
    "G56": WordInfo(name="Select coordinate system 3", modal_group=12, ordering=150),
    "G57": WordInfo(name="Select coordinate system 4", modal_group=12, ordering=150),
    "G58": WordInfo(name="Select coordinate system 5", modal_group=12, ordering=150),
    "G59": WordInfo(name="Select coordinate system 6", modal_group=12, ordering=150),
    "G59.1": WordInfo(name="Select coordinate system 7", modal_group=12, ordering=150),
    "G59.2": WordInfo(name="Select coordinate system 8", modal_group=12, ordering=150),
    "G59.3": WordInfo(name="Select coordinate system 9", modal_group=12, ordering=150),
    # GCode modal group 13
    "G61": WordInfo(name="Exact path mode", modal_group=13, ordering=160),
    "G61.1": WordInfo(name="Exact stop mode", modal_group=13, ordering=160),
    "G64": WordInfo(name="Path blending", modal_group=13, ordering=160),
    # MCode modal group 4
    "M0": WordInfo(name="Pause", modal_group=4, ordering=220),
    "M1": WordInfo(name="Optional stop", modal_group=4, ordering=220),
    "M2": WordInfo(name="Program end", modal_group=4, ordering=220),
    "M30": WordInfo(name="Program end, exchange pallet shuttles", modal_group=4, ordering=220),
    # MCode modal group 6
    "M6": WordInfo(name="Change tool", modal_group=6, ordering=60),
    # MCode modal group 7
    "M3": WordInfo(name="Spindle clockwise", modal_group=7, ordering=70),
    "M4": WordInfo(name="Spindle counterclockwise", modal_group=7, ordering=70),
    "M5": WordInfo(name="Stop spindle", modal_group=7, ordering=70),
    # MCode modal group 8
    "M7": WordInfo(name="Mist coolant on", modal_group=8, ordering=80),
    "M8": WordInfo(name="Flood coolant on", modal_group=8, ordering=80),
    "M9": WordInfo(name="Coolant off", modal_group=8, ordering=80),
    # MCode modal group 9
    "M48": WordInfo(name="Enable override controls", modal_group=9, ordering=90),
    "M49": WordInfo(name="Disable override controls", modal_group=9, ordering=90),
}
