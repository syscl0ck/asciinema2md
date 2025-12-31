"""Terminal state emulator to reconstruct output from events."""

from typing import List
from .ansi import strip_ansi


class Terminal:
    """Simple terminal emulator to reconstruct output."""
    
    def __init__(self, width: int = 80, height: int = 24):
        self.width = width
        self.height = height
        self.lines: List[str] = ['']
        self.scrollback: List[str] = []  # Keep scrollback buffer
        self.current_line = 0
        self.cursor_x = 0
        self.scrollback_size = 10000  # Keep last 10000 lines
        
    def process_text(self, text: str) -> str:
        """
        Process text output and update terminal state.
        Returns the visible text that was written.
        """
        i = 0
        
        while i < len(text):
            char = text[i]
            
            # Handle escape sequences
            if char == '\x1b':
                i += 1
                if i >= len(text):
                    break
                    
                if text[i] == '[':
                    # ANSI CSI sequence
                    i += 1
                    params = []
                    param_str = ''
                    
                    # Parse parameters
                    while i < len(text) and text[i] not in 'ABCDEFGHJKSTfmsu':
                        if text[i] == ';':
                            if param_str:
                                params.append(param_str)
                            param_str = ''
                        else:
                            param_str += text[i]
                        i += 1
                    
                    if param_str:
                        params.append(param_str)
                    
                    if i < len(text):
                        cmd = text[i]
                        i += 1
                        
                        # Handle cursor movement commands
                        if cmd == 'A':  # Cursor up
                            try:
                                n = int(params[0]) if params and params[0].isdigit() else 1
                                self.current_line = max(0, self.current_line - n)
                            except (ValueError, IndexError):
                                pass
                        elif cmd == 'B':  # Cursor down
                            try:
                                n = int(params[0]) if params and params[0].isdigit() else 1
                                self.current_line = min(len(self.lines) - 1, self.current_line + n)
                            except (ValueError, IndexError):
                                pass
                        elif cmd == 'C':  # Cursor right
                            try:
                                n = int(params[0]) if params and params[0].isdigit() else 1
                                self.cursor_x += n
                            except (ValueError, IndexError):
                                pass
                        elif cmd == 'D':  # Cursor left
                            try:
                                n = int(params[0]) if params and params[0].isdigit() else 1
                                self.cursor_x = max(0, self.cursor_x - n)
                            except (ValueError, IndexError):
                                pass
                        elif cmd == 'H' or cmd == 'f':  # Cursor position
                            try:
                                row = int(params[0]) - 1 if params and params[0].isdigit() else 0
                                col = int(params[1]) - 1 if len(params) > 1 and params[1].isdigit() else 0
                                self.current_line = max(0, min(row, len(self.lines) - 1))
                                self.cursor_x = max(0, col)
                            except (ValueError, IndexError):
                                pass
                        elif cmd == 'K':  # Erase from cursor to end of line
                            self._clear_to_eol()
                        elif cmd == 'J':  # Erase display
                            if params and params[0] == '2':
                                # Clear entire screen
                                self.lines = ['']
                                self.current_line = 0
                                self.cursor_x = 0
                            else:
                                # Clear from cursor to end
                                self._clear_to_eol()
                                # Clear remaining lines
                                while self.current_line < len(self.lines) - 1:
                                    self.current_line += 1
                                    self.lines[self.current_line] = ''
                elif text[i] == ']':
                    # OSC sequence - skip until BEL
                    i += 1
                    while i < len(text) and text[i] != '\x07':
                        i += 1
                    if i < len(text):
                        i += 1
                else:
                    # Other escape sequence
                    i += 1
                continue
            
            # Handle control characters
            if char == '\r':
                # Carriage return - move to start of line
                self.cursor_x = 0
                i += 1
            elif char == '\n':
                # Newline
                # Save current line to scrollback if we're about to scroll off
                if self.current_line >= self.height - 1:
                    # Move top line to scrollback
                    if self.lines:
                        self.scrollback.append(self.lines[0])
                        self.lines = self.lines[1:]
                        # Trim scrollback if too large
                        if len(self.scrollback) > self.scrollback_size:
                            self.scrollback = self.scrollback[-self.scrollback_size:]
                else:
                    if self.current_line >= len(self.lines) - 1:
                        self.lines.append('')
                    self.current_line += 1
                self.cursor_x = 0
                i += 1
            elif char == '\b':
                # Backspace
                if self.cursor_x > 0:
                    self.cursor_x -= 1
                i += 1
            elif char == '\t':
                # Tab - convert to spaces
                spaces = 8 - (self.cursor_x % 8)
                for _ in range(spaces):
                    self._write_char(' ')
                i += 1
            else:
                # Regular character
                self._write_char(char)
                i += 1
        
        return ''  # We don't need to return visible text here
    
    def _write_char(self, char: str):
        """Write a character at the current cursor position."""
        # Ensure we have enough lines
        while self.current_line >= len(self.lines):
            self.lines.append('')
        
        # Extend line if needed
        line = list(self.lines[self.current_line])
        while len(line) <= self.cursor_x:
            line.append(' ')
        
        # Write character (overwrite if position exists)
        if self.cursor_x < len(line):
            line[self.cursor_x] = char
        else:
            line.append(char)
        
        self.lines[self.current_line] = ''.join(line)
        self.cursor_x += 1
        
        # Auto-wrap if needed
        if self.cursor_x >= self.width:
            self.cursor_x = 0
            if self.current_line < len(self.lines) - 1:
                self.current_line += 1
            else:
                self.lines.append('')
                self.current_line = len(self.lines) - 1
    
    def _clear_to_eol(self):
        """Clear from cursor to end of line."""
        if self.current_line < len(self.lines):
            line = list(self.lines[self.current_line])
            # Truncate at cursor position
            if self.cursor_x < len(line):
                self.lines[self.current_line] = ''.join(line[:self.cursor_x])
    
    def get_output(self) -> str:
        """Get the current terminal output as a string."""
        # Combine scrollback and current lines
        all_lines = self.scrollback + self.lines
        # Remove trailing empty lines
        while all_lines and not all_lines[-1].strip():
            all_lines.pop()
        return '\n'.join(all_lines)
    
    def reset(self):
        """Reset terminal state."""
        self.lines = ['']
        self.current_line = 0
        self.cursor_x = 0

