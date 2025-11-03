import unittest
from compiler import FootballDSLCompiler


VALID = """
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

SYNTAX_ERR = """
formation 4-3-3
GK: A
play P {
  I -> K [cross]
  K -> shoot
"""  # missing closing brace and formation players


class TestIntegration(unittest.TestCase):
    def test_full_pipeline_success(self):
        comp = FootballDSLCompiler()
        res = comp.compile(VALID)
        self.assertTrue(res["success"])  # no semantic errors
        self.assertIsNotNone(res["ir_json"])  # IR generated

    def test_syntax_error(self):
        comp = FootballDSLCompiler()
        res = comp.compile(SYNTAX_ERR)
        self.assertFalse(res["success"])  # parse should fail
        self.assertIsNone(res.get("ir_json"))


if __name__ == '__main__':
    unittest.main()


