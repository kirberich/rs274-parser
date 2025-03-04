from copy import deepcopy
from pathlib import Path
from typing import Literal

from pe.actions import Pack

from rs274_parser import exceptions
from rs274_parser.dialects import rs274ngc
from rs274_parser.types import Line, NamedParameterAssignment, NumericParameterAssignment, TNumber, Word

from .linuxcnc_grammar import GRAMMAR

word = rs274ngc.word

from . import constants

LETTERS = constants.LETTERS
WORDS = constants.WORDS

CURRENT_DIR = Path(__file__).parent


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
            deepcopy(initial_named_parameter_values) if initial_named_parameter_values is not None else {}
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
            raise exceptions.UndefinedParameter(f"Named parameter #<{parameter_index}> is undefined.")
        return self.named_parameter_values[parameter_index]

    def set_parameter_value(self, parameter_index: int | str, parameter_value: TNumber):
        """Set a new (pending) parameter value.

        Has to be commited with commit_parameter_values() before the parameter is actually updated.
        """
        if isinstance(parameter_index, int):
            return super().set_parameter_value(parameter_index, parameter_value)

        self._pending_named_parameter_values[parameter_index] = parameter_value


class LinuxCNC(rs274ngc.Rs274):
    machine_state: MachineState  # type: ignore[reportIncompatibleVariableOverride]

    @property
    def grammar_str(self) -> str:
        return GRAMMAR

    def __init__(
        self,
        initial_machine_state: MachineState | None = None,
        start_rule: str = "line",
        extra_rule: str | None = None,
    ):
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
        super().__init__(initial_machine_state, start_rule=start_rule, extra_rule=extra_rule)

    def transform_named_parameter(self, parameter_name: str):
        return self.machine_state.get_parameter_value(parameter_name)

    def transform_named_parameter_setting(self, items: list[str | TNumber]):
        assert len(items) == 2
        parameter_name = items[0]
        parameter_value = items[1]
        assert isinstance(parameter_name, str)
        assert isinstance(parameter_value, TNumber)

        self.machine_state.set_parameter_value(parameter_name, parameter_value)
        return NamedParameterAssignment(name=parameter_name, value=parameter_value)

    def transform_line(  # type: ignore[reportIncompatibleVariableOverride]
        self,
        s: str,
        items: list[Literal["/"] | int | Word | str | NumericParameterAssignment | NamedParameterAssignment],
    ) -> Line:
        rs274_items: list[Literal["/"] | int | Word | str | NumericParameterAssignment] = []

        named_parameter_assignments: dict[str, TNumber] = {}
        for item in items:
            if isinstance(item, NamedParameterAssignment):
                named_parameter_assignments[item.name] = item.value
            else:
                rs274_items.append(item)

        line = super().transform_line(s, rs274_items)
        line.named_assignments = named_parameter_assignments

        # Updated named parameters after the line has been processed
        self.machine_state.commit_parameter_values()

        return line

    def actions(self):
        rs274_actions = super().actions()
        return {
            "named_parameter": self.transform_named_parameter,
            "named_parameter_setting": Pack(self.transform_named_parameter_setting),
            **rs274_actions,
        }
