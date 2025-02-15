"""Types used in the GCode grammars"""

from dataclasses import dataclass, field
from typing import Literal

NamedParameter = str
ParameterIndex = int

L1_OPERATOR = Literal["+", "-", "and", "or", "xor"]
L2_OPERATOR = Literal["*", "/"]
L3_OPERATOR = Literal["**"]
BINARY_OPERATOR = L1_OPERATOR | L2_OPERATOR | L3_OPERATOR
UNARY_OPERATOR = Literal[
    "abs",
    "acos",
    "asin",
    "atan",
    "cos",
    "exp",
    "fix",
    "fup",
    "ln",
    "round",
    "sin",
    "sqrt",
    "tan",
]

TNumber = int | float


@dataclass(slots=True, frozen=True)
class WordInfo:
    """Meta information about a word."""

    modal_group: int = field(kw_only=True)
    name: str = field(kw_only=True, compare=False)
    # Note: the ordering is denormalized onto each instantiated word, because it's needed for sorting the words in a line
    ordering: int = field(kw_only=True)


@dataclass(slots=True, frozen=True)
class Word:
    """A word is a single letter specifying the command (G/M) or argument (X/Y/I/J etc) and a single number.

    The letter can represent a command or a parameter,
    and the same letter can mean different things in different contexts.

    Note: the specification states that line number specifiers (N10 etc), are not words.
    """

    letter: str
    number: TNumber
    ordering: int = field(kw_only=True)

    def __lt__(self, other: "Word"):
        """Make words sortable by their position in the order of execution"""
        return self.ordering < other.ordering

    def __str__(self):
        return f"{self.letter.upper()}{self.number}"


@dataclass(slots=True, frozen=True)
class Line:
    words: list[Word]
    comments: list[str] = field(default_factory=list)
    line_number: int | None = None

    def __str__(self):
        s = ""

        if self.line_number is not None:
            s += f"N{self.line_number}"

        s += " ".join([str(word) for word in self.words] + [f"({comment})" for comment in self.comments])

        return s
