# Python library for parsing RS274/NGC-based GCode

The aim of this project is very narrowly to, as correctly as possible, parse and evaluate RS274 GCode into a simple-to-use format for use in simulation/visualisation, etc.

* Uses [arpeggio](https://textx.github.io/Arpeggio/2.0/getting_started/) to create and evalulate the GCode.
* Evalulates each line of GCode to turn expressions, parameters etc into numeric values.
* Uses a simple `MachineState` object to allow passing in, and keeping track of, any machine state that affects evaluation of GCode.
* Orders resulting GCode words in each line according to their order of execution.
* Returns a simple structure of `list[Word]` that can then be used further.

This library does _not_
* Calculate how a machine running the GCode would move.
* Validate that moves make sense.
* Group words that belong together to perform an action (though this might get added)
* Keep track of machine state or side effects that don't affect the evaluation of GCode expressions, like motion modes, coordinate systems etc (though this might get added).

## Usage

To parse GCode, either a single line or multiple lines at once, first instantiate a parser of the appropriate dialect, optionally with an initial machine state if needed:

```python
from rs274_parser.dialects.linuxcnc import Parser, MachineState

initial_machine_state = MachineState(
    initial_named_parameter_values={"defined": 10, "param": 1}
)
parser = Parser(initial_machine_state)
```

Then call `parse` to get the parsed GCode back as a list of `Line` objects:

```python
gcode = """\
#<named_var> = 1
#1 = 0
#1 = 1 G0 X#1 Y#<named_var> (silly but legal) #1 = 2 ; will evaluate to G0 X0 Y1
G[#[#1-sin[90]]] X[1 * 1/1 - 1 ** 1 + LN[1]] ; will evaluate to G0 X0

"""
lines = parser.parse(gcode)

for line in lines:
    print(line)

# Should result in
# G0 X0 Y1 (silly but legal) (will evaluate to G0 X0 Y1)
# G2 X0.0 (will evaluate to G0 X0)
```

The GCode words within each returned line will be in execution order, which may be different from the order they appear in within the line.

The line objects themselves are very simple and just contain

```python
class Line:
    words: list[Word]
    comments: list[str]
    line_number: int | None
```

with Word being

```python
class Word:
    letter: str
    number: int | float
    ordering: int # Determines the execution order
```

## Supported dialects

* RS274/NGC, according to the [V3 spec](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=823374)
    * Missing two-parameter ATAN
    * Missing machine parameters that are defined by default
* LinuxCNC see [difference to RS274/NGC](http://linuxcnc.org/docs/stable/html/gcode/rs274ngc.html)
    * Missing oWords
    * Missing numeric and named global parameters that are defined by default
