"""Process asciinema events to extract commands and output."""

import re
from typing import List, Tuple, Optional
from .ansi import strip_ansi


class EventProcessor:
    """Process events to extract commands and their outputs."""
    
    def __init__(self):
        self.prompt_pattern = re.compile(r'┌──\([^\)]+\)\-\[[^\]]+\]\r?\n└─[#\$]\s*')
        self.commands: List[Tuple[str, str]] = []  # (command, output)
        self.current_command_buffer = []  # Characters being typed
        self.current_output = []
        self.in_prompt = False
        self.command_entered = False
        
    def process_events(self, events: List[Tuple[float, str, str]]) -> List[Tuple[str, str]]:
        """Process all events and return list of (command, output) tuples."""
        
        for timestamp, event_type, text in events:
            if event_type != 'o':
                continue
            
            # Check for prompt
            if self.prompt_pattern.search(text):
                # New prompt detected
                if self.command_entered:
                    # Save previous command
                    cmd = self._extract_command()
                    if cmd:
                        output = '\n'.join(self.current_output).strip()
                        output = self._clean_output(output)
                        self.commands.append((cmd, output))
                
                # Reset for new command
                self.current_command_buffer = []
                self.current_output = []
                self.in_prompt = True
                self.command_entered = False
                continue
            
            clean_text = strip_ansi(text)
            
            if self.in_prompt and not self.command_entered:
                # We're in a prompt, tracking command input
                
                # Check if Enter was pressed (\r\r\n or \r\n after typing)
                if '\r\r\n' in text or (self.current_command_buffer and '\r\n' in text and not clean_text.startswith('┌──')):
                    # Enter pressed - command is complete
                    self.command_entered = True
                    self.in_prompt = False
                    # Don't add the newline to output yet
                    continue
                
                # Check if this is a complete command string (shell echo)
                # Complete commands usually appear as one string without control chars
                if (len(clean_text) > 5 and 
                    not any(c in clean_text for c in '\x1b\r\n\b') and
                    re.search(r'^[a-zA-Z][a-zA-Z0-9_/\-\.\s\$"\'=:;]+$', clean_text.strip())):
                    # This looks like a complete command
                    self.current_command_buffer = [clean_text.strip()]
                    self.command_entered = True
                    self.in_prompt = False
                    continue
                
                # Track individual characters (handle backspaces)
                for char in text:
                    if char == '\b':
                        # Backspace - remove last character
                        if self.current_command_buffer:
                            self.current_command_buffer.pop()
                    elif char not in '\x1b\r\n':
                        # Regular character (skip ANSI start, but we already stripped)
                        # Only add printable characters
                        if 32 <= ord(char) <= 126:  # Printable ASCII
                            self.current_command_buffer.append(char)
            else:
                # This is output
                if clean_text.strip() and not clean_text.startswith('┌──'):
                    self.current_output.append(clean_text)
        
        # Don't forget last command
        if self.command_entered:
            cmd = self._extract_command()
            if cmd:
                output = '\n'.join(self.current_output).strip()
                output = self._clean_output(output)
                self.commands.append((cmd, output))
        
        return self.commands
    
    def _extract_command(self) -> str:
        """Extract final command from buffer."""
        cmd = ''.join(self.current_command_buffer).strip()
        # Remove any remaining ANSI artifacts
        cmd = re.sub(r'[^\x20-\x7E]', '', cmd)
        return cmd.strip()
    
    def _clean_output(self, text: str) -> str:
        """Clean output text."""
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            # Remove vim artifacts
            if line.strip() == '~':
                continue
            if '-- INSERT --' in line or '-- REPLACE --' in line:
                continue
            if re.match(r'^\d+,\d+.*All', line):
                continue
            if line.strip() in ['▽', 'zz']:
                continue
            cleaned.append(line)
        
        # Remove leading/trailing empty lines
        while cleaned and not cleaned[0].strip():
            cleaned.pop(0)
        while cleaned and not cleaned[-1].strip():
            cleaned.pop()
        
        return '\n'.join(cleaned)

