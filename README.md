# Football Playbook DSL – Developer Guide

This repository contains a working Football Playbook DSL toolchain with:
- A lexer and parser for a domain-specific language (DSL)
- Semantic analysis with formation- and play-level rules
- JSON IR (Intermediate Representation) generation
- A Pygame visualizer to simulate plays on a pitch
- A Tkinter GUI for authoring DSL scripts and viewing compilation outputs

## Quick Start (Windows)

- Launch GUI:
  - Open PowerShell in the project folder
  - Run: `py ui.py`
- Save IR JSON from the GUI, then visualize:
  - Click “Open Visualizer” in the GUI, or run: `py visualizer.py`
- Run tests:
  - `py -m unittest discover -s tests -p "test_*.py"`

Dependencies: Python 3.9+ (pygame, tkinter is included with Python on Windows).

---

## Architecture Overview

DSL Script → Lexer → Parser → Semantic Analyzer → IR Generator → Visualizer

- `football_dsl_lexer_parser.py`: Tokens, AST nodes, Lexer, and Parser
- `semantic_analyzer.py`: Validates formations, players, and play semantics
- `ir_generator.py`: Converts AST to JSON IR
- `compiler.py`: Orchestrates all compilation phases and produces intermediates for the UI
- `visualizer.py`: Pygame simulation (reads IR JSON)
- `ui.py`: Tkinter GUI for authoring DSL and viewing outputs

---

## File-by-File Walkthrough (block-by-block)

### football_dsl_lexer_parser.py

- Imports and constants
  - `re`, `json`, `Enum`, `typing` utilities
  - `TokenType(Enum)`: Defines all token classes used by the lexer and parser: `FORMATION`, `PLAY`, `IDENTIFIER`, `NUMBER`, `ROLE`, `PLAYER_NAME`, `ARROW`, `ACTION`, `LBRACE`, `RBRACE`, `LBRACKET`, `RBRACKET`, `COLON`, `COMMA`, `EOF`.
  - `VALID_ROLES`: Set of supported roles across formations (e.g., GK, LB, CB1, …, ST).
  - `VALID_ACTIONS`: Set of allowed actions in play steps (pass, through_pass, cross, shoot, …).

- Token
  - `class Token`: holds `type`, `value`, `line`, `column` and `__repr__` for debugging.

- Lexer
  - `class Lexer`:
    - Keeps `text`, `pos`, `line`, `column`, `current_char`.
    - `error(message)`: raises a descriptive exception.
    - `advance()`: moves cursor (tracks newlines and columns).
    - `skip_whitespace()`: skips whitespace.
    - `parse_identifier()`: reads an alnum/underscore run and classifies:
      - `formation` → `TokenType.FORMATION`
      - `play` → `TokenType.PLAY`
      - matches `VALID_ROLES` → `ROLE`
      - matches `VALID_ACTIONS` → `ACTION`
      - matches `^\d+-\d+-\d+$` → `NUMBER` (formation pattern)
      - fallback → `PLAYER_NAME`
    - `get_next_token()`: main scanner loop
      - Skips whitespace
      - Routes to `parse_identifier()` or number/arrow/punctuation handlers
      - Emits tokens including `{ } [ ] : ,` and `ARROW (->)`
      - Yields `EOF` at end

- AST node classes
  - `Formation(pattern, players)` with `__repr__`
  - `PlayStep(from_player, to_player|None, action)` with `__repr__`
  - `Play(name, steps)` with `__repr__`
  - `Program(formation, plays)` with `__repr__`

- Parser
  - `class Parser(lexer)`: maintains `current_token`
    - `error(message, token=None)`: throws parser error with position
    - `eat(token_type)`: consumes expected token or errors
    - `parse_formation()`: `formation` NUMBER, followed by multiple `ROLE : PLAYER_NAME` lines, returns `Formation`
    - `parse_play_step()`: `PLAYER_NAME -> (PLAYER_NAME [ACTION]? | shoot)`; if no `[]`, action defaults to `pass`
    - `parse_play()`: `play` name `{` steps `}`; name token is treated as `PLAYER_NAME`
    - `parse()`: `formation` + zero or more `play` blocks → `Program`


### semantic_analyzer.py

- `class SemanticError(Exception)`: carries message and optional position
- `class SemanticAnalyzer`:
  - `formation_patterns`: map formations (e.g., `4-3-3`, `4-4-2`, `4-2-3-1`, `3-5-2`) to expected role counts by base-role category
  - `analyze(program)`: orchestrates checks
    - `_validate_formation(formation)`: verifies known pattern, expected role counts (strips digits from role names), and duplicate player names
    - Builds `symbol_table = program.formation.players` (role→player)
    - For each `play`: `_validate_play(play)`
  - `_validate_play(play)`: per-step checks
    - Player existence for `from_player` and `to_player`
    - Role constraints via `_check_role_constraints(step, play_name, step_num)` (e.g., GK cannot `shoot` or `cross` in open play; defenders shouldn’t `shoot` from open play unless set piece)
    - Continuity rule (added): for each consecutive step, the `to_player` of step i must equal the `from_player` of step i+1; if a step is a `shoot`, it must be the last step.
  - `_check_role_constraints(step, play_name, step_num)`: base-role derived from role name; applies restrictions


### ir_generator.py

- `class IRGenerator` with static `generate(program)`:
  - Produces JSON-serializable IR:
    - `formation: { pattern, players }`
    - `plays: [ { name, steps: [ { from, action, to? } ] } ]`


### compiler.py

- Orchestrates compilation and prepares intermediates for UI:
  - Members: `lexer`, `parser`, `semantic_analyzer`, `ir_generator`, `log`
  - `_log(msg)`: records phase messages for UI
  - `tokenize(source)`: streams tokens from `Lexer` and returns
    - `tokens`: list of `{type, value, line, column}` in exact lexer order
    - `token_classes`: map of `TokenType.value -> [lexemes]` (all, including punctuation; `EOF` omitted)
  - `parse(source)`: runs `Parser` and returns AST
  - `_ast_to_dict(node)`: JSON-friendly conversion of AST
  - `_ast_to_tree(node)`: ASCII tree for display in UI
  - `semantic_check(ast)`: runs `SemanticAnalyzer.analyze(ast)`; returns `{ ok, errors[], symbol_table }`
  - `compile(source)`: end-to-end pipeline returning a dict of intermediates: `tokens`, `token_classes`, `ast`, `ast_dict`, `ast_tree`, `symbol_table`, `semantic_errors`, `ir`, `ir_json`, and `log`


### visualizer.py

- `class FootballPitchVisualizer`:
  - Initializes Pygame window and pitch geometry/colors
  - Computes base `formation_positions` per formation
  - Builds `players` dict: position, role, color, possession, original position, target position, base speed
  - Animation parameters and timers (including `hold_until_ms` to pause after shots)
  - Key rendering methods: `draw_pitch()`, `draw_players()`, `draw_play_info()`, `draw_animation_line()`
  - Play execution loop: `run()` dispatches events and ticks `update_animation()`
  - Step logic:
    - `execute_current_step()` → `start_animation(from, to, action)`
    - For `pass`/`through_pass`/`cross`, ball target and player run targets are set; for `cross`, attackers flood the box; weak-side winger attacks far post
    - For `shoot`, target is goal; shooter attacks the ball/end-point; hold-after-shot keeps the scene visible
    - `complete_animation()` updates possession/colors and advances step indexing with proper holds before transitioning plays
  - `main()` can accept an IR path argument; otherwise reads `playbook_ir.json`


### ui.py

- Templates (`TEMPLATES`): sample DSL scripts for `4-3-3`, `4-4-2`, `4-2-3-1` (single CM), `3-5-2`
- `class DSLGUI(tk.Tk)`:
  - Menu: New/Open/Save/Save As, and Templates chooser
  - Toolbar buttons: Validate, Generate IR (JSON), Save IR JSON, Open Visualizer
  - Editor: `tk.Text` with basic highlighting (keywords, roles, actions, arrows)
  - Output tabs: Tokens, AST (JSON), Symbol Table (now lexeme→token class table in lexer order), Semantic Results, IR JSON, AST Tree (ASCII)
  - Actions:
    - `_validate()`: compiles source and shows all intermediates
    - `_generate_ir()`: same as validate, plus highlights IR JSON
    - `_save_ir()`: compiles source; if IR is available, prompts for save path and writes JSON
    - `_open_visualizer()`: launches `visualizer.py` via `subprocess.Popen`; if a recent IR path is known, passes it as an argument
  - Helper methods: `_show_results(result)`, `_set_text(widget, text)`, `_highlight()` token highlighting; file open/save helpers

---

## What Each Button Runs

- Validate
  - Calls: `FootballDSLCompiler.compile(dsl_text)`
  - Internally runs: `tokenize` → `parse` → `semantic_check` (no IR generation if semantics fail)
  - UI updates: Tokens, AST (JSON), AST Tree, Symbol Table (lexeme→token class table), Semantic Results, Log

- Generate IR (JSON)
  - Calls: `FootballDSLCompiler.compile(dsl_text)`
  - Internally runs: `tokenize` → `parse` → `semantic_check`; if OK → `IRGenerator.generate(ast)`
  - UI updates: all from Validate plus IR JSON tab is populated

- Save IR JSON
  - Calls: `FootballDSLCompiler.compile(dsl_text)`; if `ir_json` present → opens save dialog; writes JSON to chosen path; stores `last_saved_ir_path`

- Open Visualizer
  - Spawns: `subprocess.Popen([sys.executable, visualizer.py, last_saved_ir_path?], cwd=project_dir)`
  - `visualizer.py` loads the IR JSON (provided path or `playbook_ir.json`) and starts the simulation loop

---

## DSL Recap

- Formation
```
formation 4-3-3
GK: Alisson
LB: Robertson
CB1: VanDijk
...
```
- Play
```
play CounterAttack {
  Salah -> Nunez [through_pass]
  Nunez -> Diaz [cross]
  Diaz -> shoot
}
```
- Actions: default `pass` if brackets omitted; `shoot` has no target.
- Semantic continuity: `to` of step i must be `from` of step i+1; `shoot` must be the final step.

---

## IR Structure (reference)

```
{
  "formation": {
    "pattern": "4-3-3",
    "players": { "GK": "Alisson", ... }
  },
  "plays": [
    {
      "name": "CounterAttack",
      "steps": [
        { "from": "Salah", "to": "Nunez", "action": "through_pass" },
        { "from": "Nunez", "to": "Diaz", "action": "cross" },
        { "from": "Diaz", "action": "shoot" }
      ]
    }
  ]
}
```

---

## Troubleshooting

- Python not found on Windows: use `py` instead of `python` or install Python and check “Add Python to PATH”.
- Permission denied when saving IR: choose a writable folder (Documents or project directory) when prompted.
- Visualizer shows missing IR: Save IR from the GUI first, or pass the explicit path to `visualizer.py`.

---

## Tests

- `tests/test_lexer_parser.py`: token basics and parse program
- `tests/test_semantic_analyzer.py`: formation validity and invalid cases; continuity rules
- `tests/test_integration.py`: full pipeline success and syntax error detection

Run all: `py -m unittest discover -s tests -p "test_*.py"`
