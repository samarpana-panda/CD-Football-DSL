import unittest
from football_dsl_lexer_parser import Lexer, Parser
from semantic_analyzer import SemanticAnalyzer, SemanticError


VALID_433 = """
formation 4-3-3
GK: A
LB: B
CB1: C
CB2: D
RB: E
CM1: F
CM2: G
CM3: H
LW: I
RW: J
ST: K

play Attack {
  I -> K [cross]
  K -> shoot
}
"""

INVALID_FORMATION = """
formation 4-3-3
GK: A
LB: B
CB1: C
CB2: D
RB: E
CM1: F
CM2: G
LW: I
RW: J
ST: K

play Attack {
  I -> K [cross]
  K -> shoot
}
"""


class TestSemanticAnalyzer(unittest.TestCase):
    def test_valid_formation(self):
        ast = Parser(Lexer(VALID_433)).parse()
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)  # should not raise

    def test_invalid_formation(self):
        ast = Parser(Lexer(INVALID_FORMATION)).parse()
        analyzer = SemanticAnalyzer()
        with self.assertRaises(SemanticError):
            analyzer.analyze(ast)


if __name__ == '__main__':
    unittest.main()


