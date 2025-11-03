import pygame
import json
import math
import sys

class FootballPitchVisualizer:
    def __init__(self, ir_data):
        self.ir_data = ir_data
        self.current_play_index = 0
        self.current_step_index = 0
        self.animation_speed = 2  # seconds per step
        
        # Pygame setup
        pygame.init()
        self.width, self.height = 1000, 700
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Football Playbook Simulator")
        
        # Colors
        self.GREEN = (34, 139, 34)
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.RED = (255, 0, 0)
        self.BLUE = (0, 0, 255)
        self.YELLOW = (255, 255, 0)
        self.ORANGE = (255, 165, 0)
        
        # Player positions based on formation
        self.formation_positions = self._calculate_formation_positions()
        self.players = {}
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        self.last_step_time = pygame.time.get_ticks()
        self.hold_until_ms = 0
        self.pending_next_play = False
        
        # Animation state
        self.animation_in_progress = False
        self.animation_start_time = 0
        self.animation_duration = 1.0  # seconds
        self.moving_player = None
        self.start_pos = None
        self.end_pos = None
        self.ball_pos = None
        self.hold_until_ms = 0
    
    def _calculate_formation_positions(self):
        """Calculate player positions based on formation pattern"""
        positions = {}
        pattern = self.ir_data["formation"]["pattern"]
        
        # Base positions for different formations
        if pattern == "4-3-3":
            positions = {
                "GK": (100, 350),
                "LB": (250, 100), "CB1": (250, 250), "CB2": (250, 450), "RB": (250, 600),
                "CM1": (450, 200), "CM2": (450, 350), "CM3": (450, 500),
                "LW": (700, 150), "ST": (700, 350), "RW": (700, 550)
            }
        elif pattern == "4-4-2":
            positions = {
                "GK": (100, 350),
                "LB": (250, 150), "CB1": (250, 300), "CB2": (250, 400), "RB": (250, 550),
                "LM": (450, 150), "CM1": (450, 300), "CM2": (450, 400), "RM": (450, 550),
                "CF1": (700, 300), "CF2": (700, 400)
            }
        elif pattern == "4-2-3-1":
            positions = {
                "GK": (100, 350),
                "LB": (250, 150), "CB1": (250, 300), "CB2": (250, 400), "RB": (250, 550),
                "CDM": (400, 350), "CM1": (500, 250), "CM2": (500, 450),
                "CAM": (600, 350),
                "LM": (700, 200), "RM": (700, 500), "ST": (800, 350)
            }
        elif pattern == "3-5-2":
            positions = {
                "GK": (100, 350),
                "CB1": (250, 250), "CB2": (250, 350), "CB3": (250, 450),
                "LWB": (400, 200), "RWB": (400, 500),
                "CDM": (500, 350),
                "CM1": (600, 250), "CM2": (600, 450),
                "CF1": (750, 300), "CF2": (750, 400)
            }
        else:  # Default to 4-3-3
            positions = {
                "GK": (100, 350),
                "LB": (250, 100), "CB1": (250, 250), "CB2": (250, 450), "RB": (250, 600),
                "CM1": (450, 200), "CM2": (450, 350), "CM3": (450, 500),
                "LW": (700, 150), "ST": (700, 350), "RW": (700, 550)
            }
        
        return positions
    
    def initialize_players(self):
        """Initialize player positions and colors"""
        formation_data = self.ir_data["formation"]
        for role, player_name in formation_data["players"].items():
            if role in self.formation_positions:
                self.players[player_name] = {
                    "position": list(self.formation_positions[role]),
                    "role": role,
                    "color": self.BLUE,
                    "has_ball": False,
                    "original_position": list(self.formation_positions[role]),
                    "target_position": list(self.formation_positions[role]),
                    "base_speed": 2.0,
                    "speed": 2.0
                }
        
        # Give ball to first player in first play
        if self.ir_data["plays"]:
            first_play = self.ir_data["plays"][0]
            if first_play["steps"]:
                first_player = first_play["steps"][0]["from"]
                if first_player in self.players:
                    self.players[first_player]["has_ball"] = True
                    self.players[first_player]["color"] = self.RED
                    self.ball_pos = self.players[first_player]["position"][:]
    
    def draw_pitch(self):
        """Draw the football pitch"""
        # Green background
        self.screen.fill(self.GREEN)
        
        # Pitch outline
        pygame.draw.rect(self.screen, self.WHITE, (50, 50, 900, 600), 3)
        
        # Center line and circle
        pygame.draw.line(self.screen, self.WHITE, (500, 50), (500, 650), 2)
        pygame.draw.circle(self.screen, self.WHITE, (500, 350), 70, 2)
        pygame.draw.circle(self.screen, self.WHITE, (500, 350), 5, 2)  # Center spot
        
        # Penalty areas
        pygame.draw.rect(self.screen, self.WHITE, (50, 200, 150, 300), 2)  # Left
        pygame.draw.rect(self.screen, self.WHITE, (800, 200, 150, 300), 2)  # Right
        
        # Goal areas
        pygame.draw.rect(self.screen, self.WHITE, (50, 275, 50, 150), 2)  # Left
        pygame.draw.rect(self.screen, self.WHITE, (900, 275, 50, 150), 2)  # Right
        
        # Goals
        pygame.draw.rect(self.screen, self.WHITE, (40, 300, 10, 100), 2)   # Left goal
        pygame.draw.rect(self.screen, self.WHITE, (950, 300, 10, 100), 2)  # Right goal
        
        # Penalty spots
        pygame.draw.circle(self.screen, self.WHITE, (150, 350), 5)  # Left
        pygame.draw.circle(self.screen, self.WHITE, (850, 350), 5)  # Right
    
    def draw_players(self):
        """Draw players on the pitch"""
        for player_name, player_data in self.players.items():
            pos = player_data["position"]
            color = player_data["color"]
            
            # Draw player circle
            pygame.draw.circle(self.screen, color, (int(pos[0]), int(pos[1])), 20)
            pygame.draw.circle(self.screen, self.BLACK, (int(pos[0]), int(pos[1])), 20, 2)  # Outline
            
            # Draw player name
            name_surface = self.small_font.render(player_name, True, self.WHITE)
            name_rect = name_surface.get_rect(center=(int(pos[0]), int(pos[1])))
            self.screen.blit(name_surface, name_rect)
            
            # Draw role
            role_surface = self.small_font.render(player_data["role"], True, self.WHITE)
            role_rect = role_surface.get_rect(center=(int(pos[0]), int(pos[1]) + 30))
            self.screen.blit(role_surface, role_rect)
        
        # Draw ball separately (so it appears on top)
        if self.ball_pos:
            pygame.draw.circle(self.screen, self.WHITE, (int(self.ball_pos[0]), int(self.ball_pos[1])), 8)
            pygame.draw.circle(self.screen, self.BLACK, (int(self.ball_pos[0]), int(self.ball_pos[1])), 8, 1)
    
    def draw_play_info(self):
        """Display current play and step information"""
        if not self.ir_data["plays"]:
            return
        
        current_play = self.ir_data["plays"][self.current_play_index]
        play_name = current_play["name"]
        total_steps = len(current_play["steps"])
        current_step = self.current_step_index
        
        # Play info
        info_text = f"Play: {play_name} | Step: {current_step + 1}/{total_steps}"
        info_surface = self.font.render(info_text, True, self.WHITE)
        self.screen.blit(info_surface, (20, 20))
        
        # Current step action
        if current_step < total_steps:
            step = current_play["steps"][current_step]
            action_text = f"Action: {step['from']} "
            if 'to' in step:
                action_text += f"-> {step['to']} [{step['action']}]"
            else:
                action_text += f"-> {step['action']}"
            
            action_surface = self.font.render(action_text, True, self.YELLOW)
            self.screen.blit(action_surface, (20, 50))
        
        # Formation info
        formation_text = f"Formation: {self.ir_data['formation']['pattern']}"
        formation_surface = self.font.render(formation_text, True, self.WHITE)
        self.screen.blit(formation_surface, (20, 80))
        
        # Controls info
        controls_text = "Controls: SPACE=Next Step, R=Reset, ESC=Quit"
        controls_surface = self.small_font.render(controls_text, True, self.WHITE)
        self.screen.blit(controls_surface, (20, 650))
    
    def draw_animation_line(self):
        """Draw a line showing the pass/shot trajectory"""
        if self.animation_in_progress and self.start_pos and self.end_pos:
            current_time = pygame.time.get_ticks()
            elapsed = (current_time - self.animation_start_time) / 1000.0
            progress = min(elapsed / self.animation_duration, 1.0)
            
            # Calculate current ball position
            ball_x = self.start_pos[0] + (self.end_pos[0] - self.start_pos[0]) * progress
            ball_y = self.start_pos[1] + (self.end_pos[1] - self.start_pos[1]) * progress
            self.ball_pos = [ball_x, ball_y]
            
            # Draw trajectory line
            pygame.draw.line(self.screen, self.YELLOW, 
                           (int(self.start_pos[0]), int(self.start_pos[1])),
                           (int(self.end_pos[0]), int(self.end_pos[1])), 2)
            
            # Draw progress dot
            pygame.draw.circle(self.screen, self.ORANGE, (int(ball_x), int(ball_y)), 6)
            
            # Check if animation is complete
            if progress >= 1.0:
                self.animation_in_progress = False
                self.complete_animation()
    
    def start_animation(self, from_player, to_player, action):
        """Start pass/shot animation"""
        if from_player in self.players and (to_player is None or to_player in self.players):
            self.animation_in_progress = True
            self.animation_start_time = pygame.time.get_ticks()
            self.moving_player = from_player
            
            self.start_pos = self.players[from_player]["position"][:]
            
            if to_player:
                # Advanced movement based on action
                if action == "cross":
                    target = self._box_target_for_player(to_player)
                    self.end_pos = target[:]
                    self._set_player_target(to_player, target)
                    self._set_temp_speed(to_player, 3.0)
                    # Supporting runs
                    self._apply_crossing_runs(from_player, to_player)
                elif action == "through_pass":
                    target = self._advance_towards_goal(self.players[to_player]["position"], 80)
                    self.end_pos = target[:]
                    self._set_player_target(to_player, target)
                    self._set_temp_speed(to_player, 3.5)
                    # Passer supports
                    self._set_player_target(from_player, self._advance_towards_goal(self.start_pos, 25))
                else:
                    # Default pass behavior
                    self.end_pos = self.players[to_player]["position"][:]
                    self._set_player_target(to_player, self._advance_towards_goal(self.end_pos, 30))
                    self._set_player_target(from_player, self._advance_towards_goal(self.start_pos, 20))
            else:
                # For shots, aim towards goal
                # Fix: if on right half, shoot to RIGHT goal; else to LEFT goal
                if self.start_pos[0] > 500:
                    self.end_pos = [950, 350]
                else:
                    self.end_pos = [50, 350]
                # Shooter attacks the ball/end point so the shot is visible
                self._set_player_target(from_player, self.end_pos)
            
            self.ball_pos = self.start_pos[:]
            
            print(f"Animation: {from_player} -> {to_player if to_player else 'GOAL'} [{action}]")
    
    def complete_animation(self):
        """Complete the animation and update player states"""
        current_play = self.ir_data["plays"][self.current_play_index]
        step = current_play["steps"][self.current_step_index]
        
        from_player = step["from"]
        to_player = step.get("to")
        action = step["action"]
        
        # Reset all player colors and ball possession
        for player_data in self.players.values():
            player_data["color"] = self.BLUE
            player_data["has_ball"] = False
            # Reset temporary speeds
            player_data["speed"] = player_data.get("base_speed", 2.0)
        
        # Update ball possession
        if to_player and to_player in self.players:
            self.players[to_player]["has_ball"] = True
            self.players[to_player]["color"] = self.RED
            self.ball_pos = self.players[to_player]["position"][:]
        elif action == "shoot":
            # For shots, keep shooter highlighted and hold the frame briefly
            self.players[from_player]["color"] = self.RED
            self.ball_pos = None
            self.hold_until_ms = pygame.time.get_ticks() + 1500
        
        # Highlight involved players (keep shooter red if it was a shot)
        if action != "shoot":
            self.players[from_player]["color"] = self.ORANGE
        if to_player and to_player in self.players:
            self.players[to_player]["color"] = self.YELLOW

        # Advance step index after animation completes
        self.current_step_index += 1
        if self.current_step_index >= len(current_play["steps"]):
            # Defer play transition until any hold window expires
            self.pending_next_play = True
    
    def update_animation(self):
        """Update automatic animation progression"""
        if not self.animation_in_progress:
            current_time = pygame.time.get_ticks()
            # Pause advancement if we're holding after a shot
            if self.hold_until_ms and current_time < self.hold_until_ms:
                self._update_player_movement()
                return
            else:
                self.hold_until_ms = 0
            
            # Transition to next play if scheduled
            if self.pending_next_play and self.hold_until_ms == 0:
                self.current_step_index = 0
                self.current_play_index = (self.current_play_index + 1) % len(self.ir_data["plays"])
                self.reset_players()
                self.pending_next_play = False
                self.last_step_time = current_time
            elif current_time - self.last_step_time > self.animation_speed * 1000:
                if self.current_step_index < len(self.ir_data["plays"][self.current_play_index]["steps"]):
                    self.execute_current_step()
                    self.last_step_time = current_time
        # Always update player movement towards targets
        self._update_player_movement()
    
    def execute_current_step(self):
        """Execute the current play step"""
        current_play = self.ir_data["plays"][self.current_play_index]
        step = current_play["steps"][self.current_step_index]
        
        from_player = step["from"]
        to_player = step.get("to")
        action = step["action"]
        
        # Start animation for this step
        self.start_animation(from_player, to_player, action)
    
    def reset_players(self):
        """Reset players to initial formation positions"""
        for player_name, player_data in self.players.items():
            player_data["position"] = player_data["original_position"][:]
            player_data["color"] = self.BLUE
            player_data["has_ball"] = False
            player_data["target_position"] = player_data["original_position"][:]
        
        # Give ball to first player in current play
        if self.ir_data["plays"]:
            current_play = self.ir_data["plays"][self.current_play_index]
            if current_play["steps"]:
                first_player = current_play["steps"][0]["from"]
                if first_player in self.players:
                    self.players[first_player]["has_ball"] = True
                    self.players[first_player]["color"] = self.RED
                    self.ball_pos = self.players[first_player]["position"][:]

    def _set_player_target(self, player_name, target_pos):
        if player_name in self.players:
            self.players[player_name]["target_position"] = [
                max(50, min(950, target_pos[0])),
                max(50, min(650, target_pos[1]))
            ]

    def _advance_towards_goal(self, pos, distance):
        # Assume attacking towards right goal (increasing x)
        return [min(950, pos[0] + distance), pos[1]]

    def _set_temp_speed(self, player_name, speed):
        if player_name in self.players:
            self.players[player_name]["speed"] = speed

    def _box_point(self, slot="penalty_spot", upper=False):
        # Common box reference points for right-side attack
        if slot == "near_post":
            return [900, 300 if upper else 400]
        if slot == "far_post":
            return [900, 400 if upper else 300]
        if slot == "six_top":
            return [920, 320]
        if slot == "six_bottom":
            return [920, 380]
        if slot == "edge":
            return [800, 350]
        # penalty spot default
        return [850, 350]

    def _box_target_for_player(self, player_name):
        role = self.players[player_name]["role"]
        upper = self.players[player_name]["position"][1] < 350
        base = ''.join([c for c in role if not c.isdigit()])
        if base in ["ST", "CF"]:
            return self._box_point("near_post" if upper else "far_post", upper=upper)
        if base in ["RW", "LW"]:
            return self._box_point("six_top" if upper else "six_bottom")
        if base in ["CAM"]:
            return self._box_point("penalty_spot")
        if base in ["CM", "CDM"]:
            return self._box_point("edge")
        return self._box_point("penalty_spot")

    def _apply_crossing_runs(self, from_player, to_player):
        # Passer supports towards corner of box
        self._set_player_target(from_player, self._advance_towards_goal(self.players[from_player]["position"], 30))
        # Move attackers into the box
        for name, pdata in self.players.items():
            if name in [from_player, to_player]:
                continue
            role = pdata["role"]
            base = ''.join([c for c in role if not c.isdigit()])
            if base in ["ST", "CF", "CAM", "CM"]:
                target = self._box_target_for_player(name)
                self._set_player_target(name, target)
                self._set_temp_speed(name, 2.8)
        # Ensure weak-side winger attacks the far post relative to crosser
        from_base = ''.join([c for c in self.players[from_player]["role"] if not c.isdigit()])
        if from_base in ["LW", "LM", "LWB"]:
            # Right winger runs to far post
            for name, pdata in self.players.items():
                base = ''.join([c for c in pdata["role"] if not c.isdigit()])
                if base == "RW":
                    self._set_player_target(name, self._box_point("far_post", upper=self.players[name]["position"][1] < 350))
                    self._set_temp_speed(name, 3.2)
        elif from_base in ["RW", "RM", "RWB"]:
            # Left winger runs to far post
            for name, pdata in self.players.items():
                base = ''.join([c for c in pdata["role"] if not c.isdigit()])
                if base == "LW":
                    self._set_player_target(name, self._box_point("far_post", upper=self.players[name]["position"][1] < 350))
                    self._set_temp_speed(name, 3.2)

    def _update_player_movement(self):
        # Smoothly move players towards their targets
        for pdata in self.players.values():
            tx, ty = pdata.get("target_position", pdata["position"])
            x, y = pdata["position"]
            dx = tx - x
            dy = ty - y
            dist = (dx*dx + dy*dy) ** 0.5
            if dist > 0.5:
                speed = max(0.5, float(pdata.get("speed", 2.0)))
                step = min(speed, dist)
                pdata["position"][0] = x + dx / dist * step
                pdata["position"][1] = y + dy / dist * step
    
    def run(self):
        """Main visualization loop"""
        self.initialize_players()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        # Manual step advance
                        if not self.animation_in_progress:
                            if self.current_step_index < len(self.ir_data["plays"][self.current_play_index]["steps"]):
                                self.execute_current_step()
                                self.current_step_index += 1
                                self.last_step_time = pygame.time.get_ticks()
                            else:
                                self.current_step_index = 0
                                self.current_play_index = (self.current_play_index + 1) % len(self.ir_data["plays"])
                                self.reset_players()
                    elif event.key == pygame.K_r:
                        # Reset animation
                        self.current_step_index = 0
                        self.current_play_index = 0
                        self.reset_players()
                        self.animation_in_progress = False
                    elif event.key == pygame.K_ESCAPE:
                        running = False
            
            self.update_animation()
            self.draw_pitch()
            self.draw_players()
            
            if self.animation_in_progress:
                self.draw_animation_line()
            
            self.draw_play_info()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()

def main():
    """Load IR and start visualizer"""
    try:
        # Allow passing an explicit IR path as the first argument
        ir_path = "playbook_ir.json"
        if len(sys.argv) > 1 and sys.argv[1]:
            ir_path = sys.argv[1]
        with open(ir_path, "r") as f:
            ir_data = json.load(f)
        
        print("Starting Football Playbook Visualizer...")
        print("Controls:")
        print("  SPACE - Advance to next step")
        print("  R     - Reset to beginning")
        print("  ESC   - Quit")
        print()
        
        visualizer = FootballPitchVisualizer(ir_data)
        visualizer.run()
    
    except FileNotFoundError:
        print("Error: IR JSON not found. Please save IR first from the GUI.")
        print("Expected file: playbook_ir.json (or pass a custom path as an argument)")
    except Exception as e:
        print(f"Error starting visualizer: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()