import re
import json
from enum import Enum
from typing import List, Dict, Any, Optional

# All token classes
class TokenType(Enum):
    FORMATION = "FORMATION"
    PLAY = "PLAY"
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    ROLE = "ROLE"
    PLAYER_NAME = "PLAYER_NAME"
    ARROW = "ARROW"
    ACTION = "ACTION"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    COLON = "COLON"
    COMMA = "COMMA"
    EOF = "EOF"

# Valid roles in football formations
VALID_ROLES = {
    'GK', 'LB', 'CB1', 'CB2', 'CB3', 'RB', 'LWB', 'RWB',
    'CDM', 'CM1', 'CM2', 'CM3', 'CAM', 'LM', 'RM',
    'LW', 'RW', 'ST', 'CF1', 'CF2'
}

# Valid actions in plays
VALID_ACTIONS = {
    'pass', 'through_pass', 'cross', 'long_ball', 'dribble',
    'shoot', 'tackle', 'intercept', 'clear', 'save'
}

class Token:
    def __init__(self, type: TokenType, value: str, line: int, column: int):
        self.type = type
        self.value = value
        self.line = line
        self.column = column
    
    def __repr__(self):
        return f"Token({self.type}, '{self.value}', line={self.line}, column={self.column})"

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.current_char = self.text[0] if text else None
    
    def error(self, message: str):
        raise Exception(f"Lexer error at line {self.line}, column {self.column}: {message}")
    
    def advance(self):
        """Move to the next character"""
        if self.current_char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
            
        self.pos += 1
        if self.pos >= len(self.text):
            self.current_char = None
        else:
            self.current_char = self.text[self.pos]
    
    def skip_whitespace(self):
        """Skip whitespace and comments"""
        while self.current_char is not None and self.current_char.isspace():
            self.advance()
    
    def parse_identifier(self):
        """Parse identifiers and keywords"""
        result = ''
        start_column = self.column
        
        while (self.current_char is not None and 
               (self.current_char.isalnum() or self.current_char == '_')):
            result += self.current_char
            self.advance()
        
        # Check if it's a keyword
        if result == 'formation':
            return Token(TokenType.FORMATION, result, self.line, start_column)
        elif result == 'play':
            return Token(TokenType.PLAY, result, self.line, start_column)
        elif result in VALID_ROLES:
            return Token(TokenType.ROLE, result, self.line, start_column)
        elif result in VALID_ACTIONS:
            return Token(TokenType.ACTION, result, self.line, start_column)
        else:
            # Check if it's a formation pattern (e.g., 4-3-3)
            if re.match(r'^\d+-\d+-\d+$', result):
                return Token(TokenType.NUMBER, result, self.line, start_column)
            else:
                return Token(TokenType.PLAYER_NAME, result, self.line, start_column)
    
    def get_next_token(self):
        """Get the next token from the input"""
        while self.current_char is not None:
            if self.current_char.isspace():
                self.skip_whitespace()
                continue
            
            # Identifiers and keywords
            if self.current_char.isalpha() or self.current_char == '_':
                return self.parse_identifier()
            
            # Numbers (for formation patterns)
            if self.current_char.isdigit():
                start_column = self.column
                result = ''
                while (self.current_char is not None and 
                       (self.current_char.isdigit() or self.current_char == '-')):
                    result += self.current_char
                    self.advance()
                return Token(TokenType.NUMBER, result, self.line, start_column)
            
            # Special characters
            if self.current_char == ':':
                token = Token(TokenType.COLON, ':', self.line, self.column)
                self.advance()
                return token
            
            if self.current_char == '{':
                token = Token(TokenType.LBRACE, '{', self.line, self.column)
                self.advance()
                return token
            
            if self.current_char == '}':
                token = Token(TokenType.RBRACE, '}', self.line, self.column)
                self.advance()
                return token
            
            if self.current_char == '[':
                token = Token(TokenType.LBRACKET, '[', self.line, self.column)
                self.advance()
                return token
            
            if self.current_char == ']':
                token = Token(TokenType.RBRACKET, ']', self.line, self.column)
                self.advance()
                return token
            
            if self.current_char == ',':
                token = Token(TokenType.COMMA, ',', self.line, self.column)
                self.advance()
                return token
            
            # Arrow (->)
            if self.current_char == '-':
                start_column = self.column
                self.advance()
                if self.current_char == '>':
                    self.advance()
                    return Token(TokenType.ARROW, '->', self.line, start_column)
                else:
                    self.error("Expected '>' after '-'")
            
            self.error(f"Unexpected character: '{self.current_char}'")
        
        return Token(TokenType.EOF, '', self.line, self.column)

class ASTNode:
    """Abstract Syntax Tree Node"""
    pass

class Formation(ASTNode):
    def __init__(self, pattern: str, players: Dict[str, str]):
        self.pattern = pattern
        self.players = players  # role -> player_name
    
    def __repr__(self):
        return f"Formation({self.pattern}, {self.players})"

class PlayStep(ASTNode):
    def __init__(self, from_player: str, to_player: Optional[str], action: str):
        self.from_player = from_player
        self.to_player = to_player
        self.action = action
    
    def __repr__(self):
        if self.to_player:
            return f"PlayStep({self.from_player} -> {self.to_player} [{self.action}])"
        else:
            return f"PlayStep({self.from_player} -> {self.action})"

class Play(ASTNode):
    def __init__(self, name: str, steps: List[PlayStep]):
        self.name = name
        self.steps = steps
    
    def __repr__(self):
        return f"Play({self.name}, steps={self.steps})"

class Program(ASTNode):
    def __init__(self, formation: Formation, plays: List[Play]):
        self.formation = formation
        self.plays = plays
    
    def __repr__(self):
        return f"Program(formation={self.formation}, plays={self.plays})"

class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()
    
    def error(self, message: str, token: Token = None):
        if token is None:
            token = self.current_token
        raise Exception(f"Parser error at line {token.line}, column {token.column}: {message}")
    
    def eat(self, token_type: TokenType):
        """Consume a token of expected type"""
        if self.current_token.type == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            self.error(f"Expected {token_type}, got {self.current_token.type}")
    
    def parse_formation(self):
        """Parse formation definition"""
        self.eat(TokenType.FORMATION)
        pattern_token = self.current_token
        self.eat(TokenType.NUMBER)
        
        players = {}
        while self.current_token.type == TokenType.ROLE:
            role = self.current_token.value
            self.eat(TokenType.ROLE)
            self.eat(TokenType.COLON)
            player_name = self.current_token.value
            self.eat(TokenType.PLAYER_NAME)
            players[role] = player_name
        
        return Formation(pattern_token.value, players)
    
    def parse_play_step(self):
        """Parse a single play step"""
        from_player = self.current_token.value
        self.eat(TokenType.PLAYER_NAME)
        self.eat(TokenType.ARROW)
        
        # Check if it's a shoot action (no target player)
        if self.current_token.type == TokenType.ACTION and self.current_token.value == 'shoot':
            action = self.current_token.value
            self.eat(TokenType.ACTION)
            return PlayStep(from_player, None, action)
        else:
            to_player = self.current_token.value
            self.eat(TokenType.PLAYER_NAME)
            
            # Check for action in brackets
            if self.current_token.type == TokenType.LBRACKET:
                self.eat(TokenType.LBRACKET)  # Eat '['
                action = self.current_token.value
                self.eat(TokenType.ACTION)
                self.eat(TokenType.RBRACKET)  # Eat ']'
            else:
                action = 'pass'  # Default action
            
            return PlayStep(from_player, to_player, action)
    
    def parse_play(self):
        """Parse a play definition"""
        self.eat(TokenType.PLAY)
        play_name = self.current_token.value
        self.eat(TokenType.PLAYER_NAME)  # Play name is treated as identifier
        self.eat(TokenType.LBRACE)
        
        steps = []
        while (self.current_token.type == TokenType.PLAYER_NAME and 
               self.current_token.value not in ['formation', 'play']):
            step = self.parse_play_step()
            steps.append(step)
        
        self.eat(TokenType.RBRACE)
        return Play(play_name, steps)
    
    def parse(self):
        """Parse the entire program"""
        formation = self.parse_formation()
        
        plays = []
        while self.current_token.type == TokenType.PLAY:
            play = self.parse_play()
            plays.append(play)
        
        self.eat(TokenType.EOF)
        return Program(formation, plays)