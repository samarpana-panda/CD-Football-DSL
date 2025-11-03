import json
from typing import Dict, Any

class IRGenerator:
    """Generate Intermediate Representation (JSON)"""
    
    @staticmethod
    def generate(program) -> Dict[str, Any]:
        """Generate JSON IR from the program"""
        ir = {
            "formation": {
                "pattern": program.formation.pattern,
                "players": program.formation.players
            },
            "plays": []
        }
        
        for play in program.plays:
            play_ir = {
                "name": play.name,
                "steps": []
            }
            
            for step in play.steps:
                step_ir = {
                    "from": step.from_player,
                    "action": step.action
                }
                
                if step.to_player:
                    step_ir["to"] = step.to_player
                
                play_ir["steps"].append(step_ir)
            
            ir["plays"].append(play_ir)
        
        return ir