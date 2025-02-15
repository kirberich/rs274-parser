import math

import pytest
from arpeggio import NoMatch

from rs274_parser import exceptions
from rs274_parser.dialects.rs274ngc.rs274ngc import MachineState, Parser, word
from rs274_parser.types import Line, TNumber, Word


@pytest.mark.parametrize(
    "input,expected_output",
    [
        (" -1", -1),
        ("1", 1),
        ("-1.0", -1.0),
        ("00001.0100", 1.01),
    ],
)
def test_numbers(input: str, expected_output: TNumber):
    assert Parser()._parse_rule(input, root_rule="number") == expected_output


@pytest.mark.parametrize(
    "input,expected_output",
    [
        # L1 operators
        ("1", 1),
        ("1+1", 2),
        ("100+[10-1]", 109),
        ("-1 - -1", 0),
        ("0 or 0", 0),
        ("100 or 1", 1),
        ("0 or 0.001", 1),
        ("1 and 1", 1),
        ("0 and 1", 0),
        ("1 xor 1", 0),
        ("1 xor 0", 1),
        # L2 operators
        ("2 * 2", 4),
        ("-2 *-5", 10),
        ("1/2*4", 2),
        ("1/[2*4]", 1 / 8),
        # L3 operators
        ("-2 ** 10", 1024),
        # Unary operands
        ("-abs[-1]", -1),
        ("acos[1]", 0),
        ("asin[1]", 90),
        ("atan[1]", 45),
        ("COS[60]", 0.5),
        ("exp[2]", math.e**2),
        ("fix[-0.2]", -1),
        ("fup[-0.9]", 0),
        ("ln[5]", math.log(5)),
        ("round[5.49]", 5),
        ("sin[-90]", -1),
        ("sqrt[16]", 4),
        ("tan[45]", 1),
        # Chained expressions
        ("1 and 1 and 1 and 1 and 1 and 1", 1),
        ("1 + 10 + 100", 111),
        ("-[1]", -1),
        ("-[-1]", 1),
        ("sin[asin[sin[90]]]", 1),
        ("1 + sin[90]", 2),
        # Parameters within operands
        ("1 + #1", 2),
        ("1 + [#1 + 1]", 3),
        # Examples from the spec (with #3 set to 1)
        ("1 + acos[0] - [#3 ** [4.0/2]]", 1 + 90 - (1 ** (4 / 2))),
        ("2.0 / 3 * 1.5 - 5.5 / 11.0", 0.5),
    ],
)
def test_operation(input: str, expected_output: int | float):
    assert pytest.approx(expected_output) == Parser(MachineState(initial_parameter_values={3: 1, 1: 1}))._parse_rule(
        input, root_rule="l1_operation"
    )


@pytest.mark.parametrize(
    "input,expected_output",
    [("#123", 123), ("#[122+1]", 123)],
)
def test_numeric_parameters(input: str, expected_output: int | float | type[Exception]):
    assert (
        pytest.approx(
            Parser(MachineState(initial_parameter_values={123: 123}))._parse_rule(input, root_rule="numeric_parameter")
        )
        == expected_output
    )


@pytest.mark.parametrize(
    "input,expected_exception",
    [
        ("#999", exceptions.UndefinedParameter),
        ("#123.01", exceptions.ExpectedInteger),
        ("#banana", NoMatch),
    ],
)
def test_numeric_parameters__error(input: str, expected_exception: type[Exception]):
    with pytest.raises(expected_exception):
        Parser(MachineState(initial_parameter_values={123: 123}))._parse_rule(input, root_rule="numeric_parameter")


@pytest.mark.parametrize(
    "input,expected_output",
    [
        ("G0", word("g", 0)),
        ("X-[1]", word("X", -1)),
        (
            "X[#1 - [#2 * abs[#2 - 4]]]",
            word("X", -3),
        ),
        (
            "X-#[#1 - [#2 * abs[#2] - 4]]",
            word(letter="X", number=-1),
        ),
    ],
)
def test_word(input: str, expected_output: Word):
    assert Parser(MachineState(initial_parameter_values={1: 1, 2: 2}))._parse_rule(
        input, root_rule="word"
    ) == pytest.approx(expected_output)


@pytest.mark.parametrize(
    "input,expected_output,expected_parameters",
    [
        ("G0", Line(words=[word("g", 0)]), None),
        ("", Line(words=[]), None),
        ("N10", Line(line_number=10, words=[]), None),
        (
            "N99 G1",
            Line(line_number=99, words=[word("g", 1)]),
            None,
        ),
        (
            # Example of unusual but legal input from the spec
            "g0x 0. 1234y 7",
            Line(words=[word("g", 0), word("X", 0.1234), word("Y", 7)]),
            None,
        ),
        (
            "G0 (first comment) X1 (second comment)",
            Line(
                words=[word("g", 0), word("X", 1)],
                comments=["first comment", "second comment"],
            ),
            None,
        ),
        # Parameter setting
        (
            "#10 = 10",
            Line(words=[]),
            {10: 10, 1: 1000},
        ),
        (
            "#1 = 1 G0 X#1",
            Line(words=[word("g", 0), word("X", 1000)]),
            {1: 1},
        ),
        (
            # The rightmost parameter should have precedence
            "#1 = 1 G0 X#1 #1 = 2",
            Line(words=[word("g", 0), word("X", 1000)]),
            {1: 2},
        ),
    ],
)
def test_line(
    input: str,
    expected_output: Line,
    expected_parameters: dict[int, TNumber] | None,
):
    initial_machine_state = MachineState(initial_parameter_values={1: 1000})
    parser = Parser(initial_machine_state)

    assert pytest.approx(parser._parse_rule(input, root_rule="line")) == expected_output

    if expected_parameters is not None:
        # The initial state should not change
        assert initial_machine_state.parameter_values == {1: 1000}
        # The parsers state does change
        assert parser.machine_state.parameter_values == expected_parameters


def test_block_delete():
    line = "/ M2"

    assert Parser()._parse_rule(line, root_rule="line") == Line([word("m", 2)])
    assert Parser(MachineState(is_block_delete_switch_enabled=True))._parse_rule(line, root_rule="line") == Line(
        [], comments=["/M2"]
    )
