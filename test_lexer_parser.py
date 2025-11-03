import unittest
from football_dsl_lexer_parser import Lexer, Parser, TokenType


VALID_DSL = """
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

play P {
  I -> K [cross]
  K -> shoot
}
"""


class TestLexerParser(unittest.TestCase):
    def test_lexer_tokens(self):
        lexer = Lexer("formation 4-3-3")
        t1 = lexer.get_next_token()
        self.assertEqual(t1.type, TokenType.FORMATION)
        t2 = lexer.get_next_token()
        self.assertEqual(t2.type, TokenType.NUMBER)

    def test_parse_program(self):
        parser = Parser(Lexer(VALID_DSL))
        program = parser.parse()
        self.assertEqual(program.formation.pattern, "4-3-3")
        self.assertEqual(len(program.plays), 1)
        self.assertEqual(program.plays[0].name, "P")


if __name__ == '__main__':
    unittest.main()


