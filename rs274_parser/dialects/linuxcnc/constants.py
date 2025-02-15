from rs274_parser.dialects import rs274ngc
from rs274_parser.types import WordInfo

LETTERS = rs274ngc.LETTERS


LINUXCNC_WORDS = {
    "G5": WordInfo(name="Cubic spline", modal_group=1, ordering=210),  # Group and ordering not in the docs
    "G5.1": WordInfo(name="Quadratic spline", modal_group=1, ordering=210),  # Group and ordering not in the docs
    "G5.2": WordInfo(name="NURBS block", modal_group=1, ordering=210),
    "G5.3": WordInfo(name="NURBS block", modal_group=1, ordering=210),
    "G7": WordInfo(name="Lathe diameter mode", modal_group=15, ordering=170),  # Ordering not in docs
    "G8": WordInfo(name="Lathe radius mode", modal_group=15, ordering=170),  # Ordering not in docs
    "G17.1": WordInfo(name="Select UV plane", modal_group=2, ordering=110),
    "G18.1": WordInfo(name="Select WU plane", modal_group=2, ordering=110),
    "G19.1": WordInfo(name="Select WU plane", modal_group=2, ordering=110),
    "G33": WordInfo(name="Spindle synchronized motion", modal_group=1, ordering=210),
    "G33.1": WordInfo(name="Rigid tapping", modal_group=1, ordering=210),
    "G38.3": WordInfo(name="Straight probe (towards piece without alarm)", modal_group=1, ordering=210),
    "G38.4": WordInfo(name="Straight probe (away from piece with alarm)", modal_group=1, ordering=210),
    "G38.5": WordInfo(name="Straight probe (away from piece without alarm)", modal_group=1, ordering=210),
    "G41.1": WordInfo(name="Dynamic cutter compensation (left of path)", modal_group=7, ordering=130),
    "G42.1": WordInfo(name="Dynamic cutter compensation (right of path)", modal_group=7, ordering=130),
    "G43.1": WordInfo(name="Dynamic tool length offset", modal_group=8, ordering=140),
    "G43.2": WordInfo(name="Apply additional tool length offset", modal_group=8, ordering=140),
    "G52": WordInfo(name="Local coordinate system offset", modal_group=0, ordering=190),
    "G73": WordInfo(name="Drilling cycle with chip breaking", modal_group=1, ordering=210),
    "G74": WordInfo(name="Left-hand tapping cycle, dwell", modal_group=1, ordering=210),
    "G76": WordInfo(name="Threading cycle", modal_group=1, ordering=210),
    "G90.1": WordInfo(name="Arc absolute distance mode", modal_group=4, ordering=170),
    "G91.1": WordInfo(name="Arc incremental distance mode", modal_group=4, ordering=170),
    "G95": WordInfo(name="Units per revolution mode", modal_group=5, ordering=20),
    "G96": WordInfo(name="Spindle constant surface speed mode", modal_group=14, ordering=170),  # Ordering is a guess
    "G97": WordInfo(name="Spindle RPM mode", modal_group=14, ordering=170),  # Ordering is a guess
    "M50": WordInfo(name="Feed override control", modal_group=9, ordering=90),
    "M51": WordInfo(name="Spindle speed override control", modal_group=9, ordering=90),
    "M52": WordInfo(name="Adaptive feed control", modal_group=9, ordering=90),
    "M53": WordInfo(name="Feed stop control", modal_group=9, ordering=90),
    "M61": WordInfo(name="Set current tool", modal_group=6, ordering=60),
    "M62": WordInfo(name="Digital output control", modal_group=5, ordering=55),
    "M63": WordInfo(name="Digital output control", modal_group=5, ordering=55),
    "M64": WordInfo(name="Digital output control", modal_group=5, ordering=55),
    "M65": WordInfo(name="Digital output control", modal_group=5, ordering=55),
    "M66": WordInfo(name="Wait on input", modal_group=5, ordering=55),
    "M67": WordInfo(name="Analog output, synchronized", modal_group=5, ordering=55),
    "M68": WordInfo(name="Analog output, immediate", modal_group=5, ordering=55),
    "M70": WordInfo(name="Save modal state", modal_group=10, ordering=75),  # Unsure about the group
    "M71": WordInfo(name="Save modal state", modal_group=10, ordering=75),  # Unsure about the group
    "M72": WordInfo(name="Save modal state", modal_group=10, ordering=75),  # Unsure about the group
}
# LinuxCNC supports all words from RS274, except for G84 and G87
SUPPORTED_RS274_WORDS = {word_str: word for word_str, word in rs274ngc.WORDS.items() if word_str not in ["G84", "G87"]}
WORDS = SUPPORTED_RS274_WORDS | LINUXCNC_WORDS


# G(95, name="Units per revolution mode", modal_group=5, ordering=2),
