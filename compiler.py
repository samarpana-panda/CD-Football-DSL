from football_dsl_lexer_parser import Lexer, Parser
from semantic_analyzer import SemanticAnalyzer, SemanticError
from ir_generator import IRGenerator
import json

class FootballDSLCompiler:
    """Main compiler class that orchestrates all phases"""
    
    def __init__(self):
        self.lexer = None
        self.parser = None
        self.semantic_analyzer = SemanticAnalyzer()
        self.ir_generator = IRGenerator()
        self.log = []
    
    def _log(self, message: str):
        self.log.append(message)
    
    def tokenize(self, source_code: str):
        """Return full token stream including positions."""
        lexer = Lexer(source_code)
        tokens = []
        classes = {}
        while True:
            token = lexer.get_next_token()
            tokens.append({
                "type": token.type.value,
                "value": token.value,
                "line": token.line,
                "column": token.column,
            })
            # Build token class groupings per TokenType (include punctuation), skip EOF
            ttype = token.type.value
            if ttype != 'EOF':
                classes.setdefault(ttype, set()).add(token.value)
            if token.type.value == 'EOF':
                break
        # Convert sets to sorted lists for UI display
        classes_readable = {k: sorted(list(v)) for k, v in classes.items()}
        return tokens, classes_readable
    
    def parse(self, source_code: str):
        """Parse source code and return AST object."""
        lexer = Lexer(source_code)
        parser = Parser(lexer)
        ast = parser.parse()
        return ast
    
    def _ast_to_dict(self, node):
        """Convert AST objects to serializable dictionaries for display."""
        # Lazy import of classes to avoid circulars
        from football_dsl_lexer_parser import Program, Formation, Play, PlayStep
        if node is None:
            return None
        if isinstance(node, Program):
            return {
                "type": "Program",
                "formation": self._ast_to_dict(node.formation),
                "plays": [self._ast_to_dict(p) for p in node.plays],
            }
        if isinstance(node, Formation):
            return {
                "type": "Formation",
                "pattern": node.pattern,
                "players": node.players,
            }
        if isinstance(node, Play):
            return {
                "type": "Play",
                "name": node.name,
                "steps": [self._ast_to_dict(s) for s in node.steps],
            }
        if isinstance(node, PlayStep):
            return {
                "type": "PlayStep",
                "from": node.from_player,
                "to": node.to_player,
                "action": node.action,
            }
        # Fallback string
        return {"repr": repr(node)}
    
    def _ast_to_tree(self, node):
        """Return an ASCII tree for the AST for UI display."""
        from football_dsl_lexer_parser import Program, Formation, Play, PlayStep
        lines = []
        
        def add(prefix, text):
            lines.append(prefix + text)
        
        def walk(n, prefix="", is_last=True):
            connector = "└─ " if is_last else "├─ "
            child_prefix = prefix + ("   " if is_last else "│  ")
            if isinstance(n, Program):
                add(prefix + connector, "Program")
                # children: formation, plays
                children = [n.formation] + list(n.plays)
                for i, c in enumerate(children):
                    walk(c, child_prefix, i == len(children) - 1)
            elif isinstance(n, Formation):
                add(prefix + connector, f"Formation: {n.pattern}")
                roles = sorted(n.players.keys())
                for i, r in enumerate(roles):
                    add(child_prefix + ("└─ " if i == len(roles)-1 else "├─ "), f"{r}: {n.players[r]}")
            elif isinstance(n, Play):
                add(prefix + connector, f"Play: {n.name}")
                for i, s in enumerate(n.steps):
                    walk(s, child_prefix, i == len(n.steps)-1)
            elif isinstance(n, PlayStep):
                if n.to_player:
                    add(prefix + connector, f"Step: {n.from_player} -> {n.to_player} [{n.action}]")
                else:
                    add(prefix + connector, f"Step: {n.from_player} -> {n.action}")
            else:
                add(prefix + connector, repr(n))
        
        walk(node, prefix="", is_last=True)
        return "\n".join(lines)
    
    def semantic_check(self, ast):
        """Run semantic analysis and return report with errors and symbol table."""
        try:
            self.semantic_analyzer.analyze(ast)
            return {
                "errors": [],
                "symbol_table": dict(self.semantic_analyzer.symbol_table),
                "ok": True,
            }
        except SemanticError as e:
            # Collect symbol table even on error if available
            return {
                "errors": [str(e)],
                "symbol_table": dict(getattr(self.semantic_analyzer, 'symbol_table', {})),
                "ok": False,
            }
    
    def compile(self, source_code: str):
        """Compile DSL source code to IR JSON and return intermediates for display."""
        self.log = []
        try:
            # Phase 1: Lexical Analysis
            self._log("=== LEXICAL ANALYSIS ===")
            tokens, token_classes = self.tokenize(source_code)
            self._log(f"Token count: {len(tokens)}")
            
            # Phase 2: Syntax Analysis
            self._log("\n=== SYNTAX ANALYSIS ===")
            ast = self.parse(source_code)
            self._log("Syntax analysis completed successfully!")
            
            # Phase 3: Semantic Analysis
            self._log("\n=== SEMANTIC ANALYSIS ===")
            sem_report = self.semantic_check(ast)
            if sem_report["ok"]:
                self._log("Semantic analysis completed successfully!")
            else:
                self._log("Semantic analysis found issues.")
            
            # Phase 4: IR Generation (only if semantics ok)
            ir = None
            ir_json = None
            if sem_report["ok"]:
                self._log("\n=== INTERMEDIATE CODE GENERATION ===")
                ir = self.ir_generator.generate(ast)
                ir_json = json.dumps(ir, indent=2)
                self._log("IR generated successfully!")
            
            return {
                "success": sem_report["ok"],
                "tokens": tokens,
                "token_classes": token_classes,
                "ast": ast,
                "ast_dict": self._ast_to_dict(ast),
                "ast_tree": self._ast_to_tree(ast),
                "symbol_table": sem_report["symbol_table"],
                "semantic_errors": sem_report["errors"],
                "ir": ir,
                "ir_json": ir_json,
                "log": self.log,
            }
        except Exception as e:
            self._log(f"Compilation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tokens": [],
                "ast": None,
                "ast_dict": None,
                "symbol_table": {},
                "semantic_errors": [str(e)],
                "ir": None,
                "ir_json": None,
                "log": self.log,
            }

# Example usage and test
def test_compiler():
    """Test the compiler with example DSL code"""
    
    dsl_code = """
formation 4-3-3
GK: Alisson
LB: Robertson
CB1: VanDijk
CB2: Konate
RB: Trent
CM1: MacAllister
CM2: Szoboszlai
CM3: Jones
LW: Diaz
RW: Salah
ST: Nunez

play CounterAttack {
    Salah -> Nunez [through_pass]
    Nunez -> Diaz [cross]
    Diaz -> shoot
}

play SetPiece {
    Trent -> VanDijk [cross]
    VanDijk -> shoot
}
"""
    
    compiler = FootballDSLCompiler()
    result = compiler.compile(dsl_code)
    
    if result["success"]:
        print("\n=== GENERATED IR JSON ===")
        print(result["ir_json"])
        
        # Save IR to file for the visualizer
        with open("playbook_ir.json", "w") as f:
            f.write(result["ir_json"])
        print("\nIR saved to 'playbook_ir.json'")
    else:
        print(f"Compilation failed: {result['error']}")

if __name__ == "__main__":
    test_compiler()