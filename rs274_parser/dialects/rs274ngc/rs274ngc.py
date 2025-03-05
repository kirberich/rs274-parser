import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Sequence, cast

import pe
from pe._constants import Flag
from pe._grammar import Grammar
from pe._parse import loads
from pe.actions import Action, Capture, Pack
from pe.machine import MachineParser
from pe.patterns import DEFAULT_IGNORE

from rs274_parser import exceptions
from rs274_parser.math_utils import to_deg, to_rad
from rs274_parser.types import (
    BINARY_OPERATOR,
    UNARY_OPERATOR,
    Line,
    NumericParameterAssignment,
    TNumber,
    Word,
)

from .constants import LETTERS, UNARY_OPERATORS, WORDS
from .rs274ngc_grammar import GRAMMAR

CURRENT_DIR = Path(__file__).parent


# FIXME: missing two-parameter atan


def batched(iterable, n=1):
    length = len(iterable)
    for ndx in range(0, length, n):
        yield iterable[ndx : min(ndx + n, length)]


def word(letter: str, number: TNumber) -> Word:
    letter = letter.upper()
    word_str = f"{letter}{number}"

    if word_str in WORDS:
        word_info = WORDS[word_str]
    elif letter in LETTERS:
        word_info = LETTERS[letter]
    else:
        raise RuntimeError(f"FIXME: what to do when word is unknown ({letter=} {number=})")

    return Word(letter=letter, number=number, ordering=word_info.ordering)


class MachineState:
    parameter_values: dict[int, TNumber]
    _pending_parameter_values: dict[int, TNumber]
    is_block_delete_switch_enabled: bool

    def __init__(
        self,
        *,
        initial_parameter_values: dict[int, TNumber] | None = None,
        is_block_delete_switch_enabled: bool = False,
    ) -> None:
        self._pending_parameter_values = (
            deepcopy(initial_parameter_values) if initial_parameter_values is not None else {}
        )
        self.commit_parameter_values()
        self.is_block_delete_switch_enabled = is_block_delete_switch_enabled

    def clone(self) -> "MachineState":
        return MachineState(
            initial_parameter_values=self.parameter_values,
            is_block_delete_switch_enabled=self.is_block_delete_switch_enabled,
        )

    def commit_parameter_values(self):
        """Setting new parameters only takes effect after any other actions involving parameters on the current line have run.
        So, it's safest to just save updated parameters separately as they're being updated, then refresh the state of the saved
        parameters at the end of the line by calling this method.
        """
        self.parameter_values = deepcopy(self._pending_parameter_values)

    def get_parameter_value(self, parameter_index: int) -> TNumber:
        if parameter_index not in self.parameter_values:
            raise exceptions.UndefinedParameter(f"Parameter #{parameter_index} is undefined.")
        return self.parameter_values[parameter_index]

    def set_parameter_value(self, parameter_index: int, parameter_value: TNumber):
        """Set a new (pending) parameter value.

        Has to be commited with commit_parameter_values() before the parameter is actually updated.
        """
        self._pending_parameter_values[parameter_index] = parameter_value


class LineAction(Action):
    func: Callable[[str, Sequence[Any]], Line]

    def __init__(self, func):
        self.func = func

    def __call__(self, s: str, pos: int, end: int, args: Sequence, kwargs: dict | None) -> tuple[tuple[Line], None]:
        return ((self.func(s, args),), None)


class Rs274:
    start_rule: str
    extra_rule: str | None
    machine_state: MachineState
    _parser: pe.Parser | None = None

    def transform_float(self, s: str):
        return float("".join(s.split()))

    def transform_integer(self, s: str):
        return int("".join(s.split()))

    def transform_operand(self, items: list[Literal["+", "-"] | TNumber]) -> TNumber:
        assert isinstance(items[-1], TNumber)
        if items[0] == "-":
            return -items[-1]
        return items[-1]

    def transform_unary_operation(self, items: list[UNARY_OPERATOR | TNumber]):
        operator = str(items[0]).lower()
        value = items[1]
        assert isinstance(value, TNumber)
        assert operator in UNARY_OPERATORS

        match operator:
            case "abs":
                return abs(value)
            case "acos":
                return to_deg(math.acos(value))
            case "asin":
                return to_deg(math.asin(value))
            case "atan":
                return to_deg(math.atan(value))
            case "cos":
                return math.cos(to_rad(value))
            case "exp":
                return math.e**value
            case "fix":
                return math.floor(value)
            case "fup":
                return math.ceil(value)
            case "ln":
                return math.log(value)
            case "round":
                return round(value)
            case "sin":
                return math.sin(to_rad(value))
            case "sqrt":
                return math.sqrt(value)
            case "tan":
                return math.tan(to_rad(value))

    def chunk_binary_op_items(
        self,
        items: list[TNumber | BINARY_OPERATOR],
    ) -> Iterable[tuple[BINARY_OPERATOR, TNumber]]:
        for operator, operand in batched(items, 2):
            assert isinstance(operator, str)
            assert isinstance(operand, TNumber)
            yield (operator, operand)

    def transform_numeric_parameter(self, parameter_index: int):
        return self.machine_state.get_parameter_value(int(parameter_index))

    def transform_parameter_setting(self, items: list[TNumber]):
        assert len(items) == 2
        parameter_index = items[0]
        parameter_value = items[1]
        assert isinstance(parameter_index, int)

        self.machine_state.set_parameter_value(parameter_index, parameter_value)
        return NumericParameterAssignment(index=parameter_index, value=parameter_value)

    def transform_binary_operation(self, items: list[TNumber | BINARY_OPERATOR]):
        """Process all binary operations.

        Note that this is called from three separate visit_ methods because
        the three different levels of operator precedence require separate rules
        """
        assert len(items) > 0
        assert isinstance(items[0], TNumber)
        value = items[0]

        for operator, operand in self.chunk_binary_op_items(items[1:]):
            match operator:
                # L1
                case "+":
                    value += operand
                case "-":
                    value -= operand
                case "and":
                    value = int(value != 0 and operand != 0)
                case "or":
                    value = int(value != 0 or operand != 0)
                case "xor":
                    value = int((value != 0) ^ (operand != 0))

                # L2
                case "*":
                    value *= operand
                case "/":
                    value = float(value / operand)

                # L3
                case "**":
                    value = value**operand

        return value

    def transform_word_number(self, items: list[Literal["+", "-"] | TNumber]) -> TNumber:
        if items[0] == "-":
            assert isinstance(items[-1], TNumber)
            return -items[-1]

        assert isinstance(items[1], TNumber)
        return items[1]

    def transform_word(self, items: list[str | TNumber]):
        letter = items[0]
        number = items[1]
        assert isinstance(letter, str)
        assert isinstance(number, TNumber)

        return word(letter, number)

    def transform_line(
        self,
        s: str,
        items: list[Literal["/"] | int | Word | str | NumericParameterAssignment],
    ) -> Line:
        if len(items) > 0 and items[0] == "/":
            if self.machine_state.is_block_delete_switch_enabled:
                return Line([], comments=[s])
            items = items[1:]

        line_number = items[0] if (len(items) > 0 and isinstance(items[0], int)) else None

        statements = cast(
            list[Word | str | NumericParameterAssignment],
            items[1:] if line_number is not None else items,
        )
        words: list[Word] = []
        comments: list[str] = []
        numeric_assignments: dict[int, TNumber] = {}
        for statement in statements:
            if isinstance(statement, Word):
                words.append(statement)
            elif isinstance(statement, NumericParameterAssignment):
                # Transform any numeric parameter assignments - note that later assignments in the same line
                # overwrite previous ones
                numeric_assignments[statement.index] = statement.value
            else:
                comments.append(statement)

        # Everything has been processed, it's now safe to updated the saved parameter values
        self.machine_state.commit_parameter_values()

        # M30 side effects
        # Change from Auto mode to MDI mode.
        # Origin offsets are set to the default (like G54).
        # Selected plane is set to XY plane (like G17).
        # Distance mode is set to absolute mode (like G90).
        # Feed rate mode is set to units per minute (like G94).
        # Feed and speed overrides are set to ON (like M48).
        # Cutter compensation is turned off (like G40).
        # The spindle is stopped (like M5).
        # The current motion mode is set to feed (like G1).
        # Coolant is turned off (like M9).

        return Line(
            line_number=line_number,
            words=sorted(words),
            comments=comments,
            numeric_assignments=numeric_assignments,
        )

    def _parse_rule(self, content: str):
        """Parse a specific part of the GCode grammar, starting at the given root rule.

        This will return whatever type the visitor returns for that given rule.
        """
        match = self.parser.match(content, flags=Flag.STRICT)
        assert match
        return match.value()

    def parse(self, content: str) -> list[Line]:
        """Parse raw GCode from a string into a list of Line objects.

        machine_state reflects the parameters and other settings of the machine - this will get mutated.

        The line objects contain all comments and GCode words in the correct execution order.
        To parse just specific parts of the GCode grammar, pass in a rule name (see rs274ngc.peg) other than 'line'
        """
        lines = []

        for line in content.splitlines():
            lines.append(self._parse_rule(line))
        return lines

    @property
    def grammar_str(self) -> str:
        return GRAMMAR

    @property
    def parser(self):
        if self._parser is not None:
            return self._parser

        grammar_str = self.grammar_str
        if self.extra_rule:
            grammar_str = self.extra_rule + "\n" + grammar_str

        _, defmap = loads(grammar_str)
        g = Grammar(defmap, actions=self.actions(), start=self.start_rule)
        self._parser = MachineParser(g, ignore=DEFAULT_IGNORE, flags=Flag.OPTIMIZE)

        return self._parser

    def __init__(
        self,
        initial_machine_state: MachineState | None = None,
        start_rule: str = "line",
        extra_rule: str | None = None,
    ):
        """Create a new parser.

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
        self.start_rule = start_rule
        self.extra_rule = extra_rule
        self.machine_state = initial_machine_state.clone() if initial_machine_state is not None else MachineState()

    def actions(self):
        return {
            "float": Capture(self.transform_float),  # type: ignore
            "integer": Capture(self.transform_integer),  # type: ignore
            "word_number": Pack(self.transform_word_number),
            "word": Pack(self.transform_word),
            "operand": Pack(self.transform_operand),
            "unary_operation": Pack(self.transform_unary_operation),
            "l1_operation": Pack(self.transform_binary_operation),
            "l2_operation": Pack(self.transform_binary_operation),
            "l3_operation": Pack(self.transform_binary_operation),
            "numeric_parameter": self.transform_numeric_parameter,
            "parameter_setting": Pack(self.transform_parameter_setting),
            "line": LineAction(self.transform_line),
        }
