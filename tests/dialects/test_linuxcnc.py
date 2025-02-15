import pytest
from arpeggio import NoMatch

from rs274_parser import exceptions
from rs274_parser.dialects.linuxcnc import MachineState, Parser, word
from rs274_parser.types import Line, TNumber


def test_named_parameters():
    machine_state = MachineState(initial_named_parameter_values={"defined": 123})
    assert Parser(machine_state)._parse_rule("#<defined>", root_rule="named_parameter") == 123


@pytest.mark.parametrize(
    "input,expected_exception",
    [
        ("#<undefined>", exceptions.UndefinedParameter),
        ("#banana", NoMatch),
    ],
)
def test_named_parameters__error(input: str, expected_exception: type[Exception]):
    machine_state = MachineState(initial_named_parameter_values={"defined": 123})

    with pytest.raises(expected_exception):
        Parser(machine_state)._parse_rule(input, root_rule="named_parameter")


@pytest.mark.parametrize(
    "input,expected_output,expected_named_parameters",
    [
        (
            # Semicolon comment taking up the whole line
            "; L10 G0 X0",
            Line([], comments=["L10 G0 X0"]),
            None,
        ),
        (
            # Semicolon comment as part of the line
            "G0 (first comment) X1 (second comment) ;semicolon comment (still)",
            Line(
                [word("g", 0), word("x", 1)],
                comments=[
                    "first comment",
                    "second comment",
                    "semicolon comment (still)",
                ],
            ),
            None,
        ),
        (
            # Set a named parameter
            "#<param> = #<defined> G0 X#<param>",
            Line([word("g", 0), word("x", 1)]),
            {"defined": 10, "param": 10},
        ),
    ],
)
def test_line(
    input: str,
    expected_output: Line,
    expected_named_parameters: dict[str, TNumber] | None,
):
    initial_machine_state = MachineState(initial_named_parameter_values={"defined": 10, "param": 1})
    parser = Parser(initial_machine_state)

    assert pytest.approx(expected_output) == parser._parse_rule(input, root_rule="line")

    if expected_named_parameters is not None:
        # The initial state should not change
        assert initial_machine_state.named_parameter_values == {
            "defined": 10,
            "param": 1,
        }
        # The parsers state does change
        assert parser.machine_state.named_parameter_values == expected_named_parameters


def test_program():
    """A small integration test trying to use the various language features together."""
    initial_machine_state = MachineState(initial_named_parameter_values={"defined": 10})
    parser = Parser(initial_machine_state)

    lines = [
        "#<first> = 1 #123 = 1 G0 X#<defined> G53",  # set G53, G0 X10, assign variables
        "N10 #123 = 2 G#<first> X#123 ; a comment",  # G1 X1
        "; another comment",
    ]

    processed_lines = [parser.parse(line) for line in lines]

    assert processed_lines == [
        Line([word("g", 53), word("g", 0), word("X", 10)]),
        Line([word("g", 1), word("x", 1)], line_number=10, comments=["a comment"]),
        Line([], comments=["another comment"]),
    ]

    assert parser.machine_state.parameter_values == {123: 2}
    assert parser.machine_state.named_parameter_values == {"first": 1, "defined": 10}
