from copy import deepcopy
from pathlib import Path

from arpeggio import visit_parse_tree

from rs274_parser import exceptions
from rs274_parser.types import Line, TNumber, Word

from rs274_parser.dialects.rs274ngc import rs274ngc

# FIXME: add missing words and letters
word = rs274ngc.word
WORDS = rs274ngc.WORDS
LETTERS = rs274ngc.LETTERS

CURRENT_DIR = Path(__file__).parent


#     G(17.1, name="Select UV plane", modal_group=2, ordering=11),
#     G(17.1, name="Select UV plane", modal_group=2, ordering=11),
#     G(17.1, name="Select UV plane", modal_group=2, ordering=11),

#     G(
#         38.3,
#         name="Straight probe (towards piece without alarm)",
#         modal_group=1,
#         ordering=21,
#     ),
#     G(
#         38.4,
#         name="Straight probe (away from piece with alarm)",
#         modal_group=1,
#         ordering=21,
#     ),
#     G(
#         38.5,
#         name="Straight probe (away from piece without alarm)",
#         modal_group=1,
#         ordering=21,
#     ),

# G41.1
# G42.1
# G43.2

# m50
# m51
# m52
# m53

# m61

# G(95, name="Units per revolution mode", modal_group=5, ordering=2),


class MachineState(rs274ngc.MachineState):
    named_parameter_values: dict[str, int | float]
    _pending_named_parameter_values: dict[str, int | float]

    def __init__(
        self,
        *,
        initial_parameter_values: dict[int, TNumber] | None = None,
        initial_named_parameter_values: dict[str, TNumber] | None = None,
        is_block_delete_switch_enabled: bool = False,
    ) -> None:
        self._pending_named_parameter_values = (
            deepcopy(initial_named_parameter_values)
            if initial_named_parameter_values is not None
            else {}
        )

        super().__init__(
            initial_parameter_values=initial_parameter_values,
            is_block_delete_switch_enabled=is_block_delete_switch_enabled,
        )

    def clone(self) -> "MachineState":
        return MachineState(
            initial_parameter_values=self.parameter_values,
            initial_named_parameter_values=self.named_parameter_values,
            is_block_delete_switch_enabled=self.is_block_delete_switch_enabled,
        )

    def commit_parameter_values(self):
        """Setting new parameters only takes effect after any other actions involving parameters on the current line have run.
        So, it's safest to just save updated parameters separately as they're being updated, then refresh the state of the saved
        parameters at the end of the line by calling this method.
        """
        super().commit_parameter_values()
        self.named_parameter_values = deepcopy(self._pending_named_parameter_values)

    def get_parameter_value(self, parameter_index: int | str) -> TNumber:
        if isinstance(parameter_index, int):
            return super().get_parameter_value(parameter_index)

        if parameter_index not in self.named_parameter_values:
            raise exceptions.UndefinedParameter(
                f"Named parameter #<{parameter_index}> is undefined."
            )
        return self.named_parameter_values[parameter_index]

    def set_parameter_value(self, parameter_index: int | str, parameter_value: TNumber):
        """Set a new (pending) parameter value.

        Has to be commited with commit_parameter_values() before the parameter is actually updated.
        """
        if isinstance(parameter_index, int):
            return super().set_parameter_value(parameter_index, parameter_value)

        self._pending_named_parameter_values[parameter_index] = parameter_value


class Visitor(rs274ngc.Visitor):
    machine_state: MachineState  # type: ignore[reportIncompatibleVariableOverride] Oh no my Liskov substitution principle!

    def __init__(
        self,
        machine_state: MachineState,
        defaults=True,
        **kwargs,
    ):
        super().__init__(machine_state, defaults, **kwargs)

    def visit_named_parameter(self, node, children: list[str]):
        parameter_name = children[0]
        return self.machine_state.get_parameter_value(parameter_name)

    def visit_named_parameter_setting(self, node, children: list[str | TNumber]):
        parameter_name = children[0]
        parameter_value = children[1]
        assert isinstance(parameter_name, str)
        assert isinstance(parameter_value, TNumber)

        self.machine_state.set_parameter_value(parameter_name, parameter_value)

    def visit_line(self, node, children: list[int | Word | str]) -> Line:
        line = super().visit_line(node, children)

        # Updated named parameters after the line has been processed
        self.machine_state.commit_parameter_values()

        return line


class Parser(rs274ngc.Parser):
    GRAMMAR_FILE = CURRENT_DIR / "linuxcnc.peg"
    machine_state: MachineState  # type: ignore[reportIncompatibleVariableOverride]

    def _parse_rule(self, content: str, *, root_rule: str):
        """Parse a specific part of the GCode grammar, starting at the given root rule.

        This will return whatever type the visitor returns for that given rule.
        """
        return visit_parse_tree(
            self.parser(root_rule).parse(content),
            Visitor(machine_state=self.machine_state),
        )

    def __init__(self, initial_machine_state: MachineState | None = None):
        """Create a new LinuxCNC GCode parser.

        The parser is stateful and keeps an internal machine state which gets updated as lines of gcode are parsed.

        initial_machine_state is used to populate the initial machine state, and is not mutated.
        initial_machine_state is copied to the internal machine_state attribute, which _does_ get mutated.

        Multiple calls to parser.parse() may result in different behaviour as the internal state is updated.
        This is to allow continuous parsing of lines of GCode with a consistent machine state.

        Example:
            parser = Parser(MachineState(initial_parameter_values={123: 0}))
            parser.parse('#123 = 1 G0 X#123') # X123 evaluates to X0
            parser.parse('#123 = 1 G0 X#123') # X123 evaluates to X123
        """
        super().__init__(initial_machine_state)
