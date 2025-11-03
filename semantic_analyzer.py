class SemanticError(Exception):
    def __init__(self, message: str, line: int = None, column: int = None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column

class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = {}
        self.formation_patterns = {
            '4-3-3': {'GK': 1, 'LB': 1, 'CB': 2, 'RB': 1,  
                     'CM': 3, 'LW': 1, 'RW': 1, 'ST': 1},  
            '4-4-2': {'GK': 1, 'LB': 1, 'CB': 2, 'RB': 1,
                     'LM': 1, 'CM': 2, 'RM': 1, 'CF': 2}, 
            '4-2-3-1': {'GK': 1, 'LB': 1, 'CB': 2, 'RB': 1,
                       'CDM': 1, 'CM': 1, 'CAM': 1, 'LM': 1, 'RM': 1, 'ST': 1},
            '3-5-2': {'GK': 1, 'CB': 3, 'LWB': 1, 'CDM': 1, 'CM': 2, 'RWB': 1, 'CF': 2}
        }
    
    def analyze(self, program):
        """Perform semantic analysis on the program"""
        errors = []
        
        # Check formation validity
        formation_errors = self._validate_formation(program.formation)
        errors.extend(formation_errors)
        
        # Build symbol table
        self.symbol_table = program.formation.players
        
        # Check each play
        for play in program.plays:
            play_errors = self._validate_play(play)
            errors.extend(play_errors)
        
        if errors:
            error_messages = "\n".join([str(error) for error in errors])
            raise SemanticError(f"Semantic errors found:\n{error_messages}")
    
    def _validate_formation(self, formation):
        """Validate formation structure"""
        errors = []
        
        # Check if formation pattern is valid
        if formation.pattern not in self.formation_patterns:
            errors.append(f"Unknown formation pattern: {formation.pattern}")
            return errors
        
        expected_roles = self.formation_patterns[formation.pattern]
        actual_roles = {}
        
        # Count actual roles
        for role in formation.players.keys():
            # Remove numbers from role names (CB1 -> CB, CM2 -> CM)
            base_role = ''.join([c for c in role if not c.isdigit()])
            actual_roles[base_role] = actual_roles.get(base_role, 0) + 1
        
        # Check role counts
        for role, expected_count in expected_roles.items():
            actual_count = actual_roles.get(role, 0)
            if actual_count != expected_count:
                errors.append(f"Formation {formation.pattern} expects {expected_count} {role}(s), found {actual_count}")
        
        # Check for duplicate player names
        player_names = list(formation.players.values())
        if len(player_names) != len(set(player_names)):
            errors.append("Duplicate player names found in formation")
        
        return errors
    
    def _validate_play(self, play):
        """Validate play semantics"""
        errors = []
        
        for i, step in enumerate(play.steps):
            # Check if from_player exists
            if step.from_player not in self.symbol_table.values():
                errors.append(f"Play '{play.name}', step {i+1}: Unknown player '{step.from_player}'")
            
            # Check if to_player exists (if applicable)
            if step.to_player and step.to_player not in self.symbol_table.values():
                errors.append(f"Play '{play.name}', step {i+1}: Unknown player '{step.to_player}'")
            
            # Check role constraints (only for non-set-piece situations)
            if play.name != "SetPiece":  # Allow defenders to shoot in set pieces
                role_errors = self._check_role_constraints(step, play.name, i+1)
                errors.extend(role_errors)

        # Enforce continuity: the recipient of step i must start step i+1
        for i in range(len(play.steps) - 1):
            current_step = play.steps[i]
            next_step = play.steps[i + 1]
            if current_step.to_player is None:
                # A shot ends the sequence; no subsequent steps should follow
                errors.append(f"Play '{play.name}', step {i+1}: 'shoot' should be the final action; no steps should follow")
                break
            if current_step.to_player != next_step.from_player:
                errors.append(
                    f"Play '{play.name}', step {i+1}->{i+2}: Continuity error - pass to '{current_step.to_player}' must be followed by a step starting with '{current_step.to_player}'"
                )
        
        return errors
    
    def _check_role_constraints(self, step, play_name, step_num):
        """Check role-based constraints"""
        errors = []
        
        # Find role of from_player
        from_role = None
        for role, player in self.symbol_table.items():
            if player == step.from_player:
                from_role = role
                break
        
        if not from_role:
            return errors
        
        # GK cannot perform certain actions
        if from_role == 'GK' and step.action in ['shoot', 'cross']:
            errors.append(f"Play '{play_name}', step {step_num}: Goalkeeper cannot perform '{step.action}' action")
        
        # Defenders have restrictions (but allow in set pieces)
        base_role = ''.join([c for c in from_role if not c.isdigit()])
        if base_role in ['CB', 'LB', 'RB'] and step.action == 'shoot':
            errors.append(f"Play '{play_name}', step {step_num}: Defender {step.from_player} should not shoot from open play")
        
        return errors