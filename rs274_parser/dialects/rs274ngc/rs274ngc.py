import math
from copy import deepcopy
from itertools import batched
from pathlib import Path
from typing import Iterable, Literal, cast

from arpeggio import NonTerminal, PTNodeVisitor, Terminal, visit_parse_tree
from arpeggio.cleanpeg import ParserPEG

from rs274_parser import exceptions, types
from rs274_parser.math_utils import to_deg, to_rad
from rs274_parser.types import Line, TNumber, Word

from .constants import LETTERS, UNARY_OPERATORS, WORDS

CURRENT_DIR = Path(__file__).parent


# FIXME: missing two-parameter atan


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


class Visitor(PTNodeVisitor):
    machine_state: MachineState

    def __init__(
        self,
        machine_state: MachineState,
        defaults=True,
        **kwargs,
    ):
        super().__init__(defaults, **kwargs)
        self.machine_state = machine_state

    def visit_integer(self, node: Terminal, children) -> int:
        value = node.value
        assert isinstance(value, str)
        return int("".join(value.split()))

    def visit_float(self, node: Terminal, children) -> float:
        value = node.value
        assert isinstance(value, str)
        return float("".join(value.split()))

    def visit_numeric_parameter(self, node, children: list[TNumber]):
        assert len(children) == 1
        parameter_index = children[0]

        if isinstance(parameter_index, float) and not parameter_index.is_integer():
            raise exceptions.ExpectedInteger(f"Expected integer for numeric parameter index, got {parameter_index}")

        return self.machine_state.get_parameter_value(int(parameter_index))

    def visit_operand(self, node, children: list[Literal["+", "-"] | TNumber]) -> TNumber:
        assert isinstance(children[-1], TNumber)
        if len(children) == 2 and children[0] == "-":
            return -children[-1]
        return children[-1]

    def _chunk_binary_op_children(
        self, children: list[TNumber | types.BINARY_OPERATOR]
    ) -> Iterable[tuple[types.BINARY_OPERATOR, TNumber]]:
        for operator, operand in batched(children, 2):
            assert isinstance(operator, str)
            assert isinstance(operand, TNumber)
            yield (operator, operand)

    def visit_unary_operation(self, node, children: list[types.UNARY_OPERATOR | TNumber]):
        operator = children[0]
        value = children[1]
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

    def _visit_binary_operation(self, node, children: list[TNumber | types.BINARY_OPERATOR]):
        """Process all binary operations.

        Note that this is called from three separate visit_ methods because
        the three different levels of operator precedence require separate rules
        """
        assert len(children) > 0
        assert isinstance(children[0], TNumber)
        value = children[0]

        for operator, operand in self._chunk_binary_op_children(children[1:]):
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

    visit_l1_operation = _visit_binary_operation
    visit_l2_operation = _visit_binary_operation
    visit_l3_operation = _visit_binary_operation

    def visit_word_number(self, node, children: list[Literal["+", "-"] | TNumber]) -> TNumber:
        if children[0] == "-":
            assert isinstance(children[-1], TNumber)
            return -children[-1]

        assert isinstance(children[0], TNumber)
        return children[0]

    def visit_word(self, node: NonTerminal, children: list[str | TNumber]) -> Word:
        letter = children[0]
        number = children[1]
        assert isinstance(letter, str)
        assert isinstance(number, TNumber)

        return word(letter, number)

    def visit_parameter_setting(self, node, children: list[TNumber]):
        parameter_index = children[0]
        parameter_value = children[1]
        assert isinstance(parameter_index, int)

        self.machine_state.set_parameter_value(parameter_index, parameter_value)

    def visit_line(self, node, children: list[Literal["/"] | int | Word | str]) -> Line:
        if len(children) > 0 and children[0] == "/":
            if self.machine_state.is_block_delete_switch_enabled:
                return Line([], comments=[node.flat_str()])
            children = children[1:]

        line_number = children[0] if (len(children) > 0 and isinstance(children[0], int)) else None

        words_and_commands = cast(
            list[Word | str],
            children[1:] if line_number is not None else children,
        )
        words: list[Word] = []
        comments: list[str] = []
        for word_or_comment in words_and_commands:
            if isinstance(word_or_comment, Word):
                words.append(word_or_comment)
            else:
                comments.append(word_or_comment)

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

        return Line(line_number=line_number, words=sorted(words), comments=comments)


class Parser:
    GRAMMAR_FILE = CURRENT_DIR / "rs274ngc.peg"
    machine_state: MachineState

    def parser(self, root_rule: str):
        with open(self.GRAMMAR_FILE) as f:
            return ParserPEG(f.read(), root_rule, ignore_case=True)

    def _parse_rule(self, content: str, *, root_rule: str):
        """Parse a specific part of the GCode grammar, starting at the given root rule.

        This will return whatever type the visitor returns for that given rule.
        """
        return visit_parse_tree(
            self.parser(root_rule).parse(content),
            Visitor(machine_state=self.machine_state),
        )

    def parse(self, content: str) -> list[Line]:
        """Parse raw GCode from a string into a list of Line objects.

        machine_state reflects the parameters and other settings of the machine - this will get mutated.

        The line objects contain all comments and GCode words in the correct execution order.
        To parse just specific parts of the GCode grammar, pass in a rule name (see rs274ngc.peg) other than 'line'
        """
        return self._parse_rule(content, root_rule="line")

    def __init__(self, initial_machine_state: MachineState | None = None):
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
        self.machine_state = initial_machine_state.clone() if initial_machine_state is not None else MachineState()
