"""Track commands as they're being typed in real-time."""

import re
from typing import List, Tuple, Optional


class CommandTracker:
    """Track commands being typed and detect when they're executed."""
    
    def __init__(self):
        self.current_command = []
        self.in_prompt = False
        self.prompt_pattern = re.compile(r'┌──\([^\)]+\)\-\[[^\]]+\]\r?\n└─[#\$] ')
        self.commands: List[Tuple[float, str, str]] = []  # (timestamp, command, output)
        self.current_output = []
        self.last_prompt_time = 0.0
        
    def process_event(self, timestamp: float, event_type: str, text: str) -> Optional[str]:
        """
        Process an event and return the command if one was just executed.
        
        Returns:
            Command string if a command was just executed, None otherwise
        """
        if event_type != 'o':
            return None
        
        # Check for prompt
        if self.prompt_pattern.search(text):
            # New prompt detected
            if self.in_prompt and self.current_command:
                # Previous command finished - extract it
                cmd = ''.join(self.current_command).strip()
                if cmd:
                    # Save previous command with its output
                    output = '\n'.join(self.current_output).strip()
                    self.commands.append((self.last_prompt_time, cmd, output))
                    self.current_output = []
                    self.current_command = []
                    self.in_prompt = False
                    return cmd
            
            # Start tracking new command
            self.in_prompt = True
            self.last_prompt_time = timestamp
            self.current_command = []
            self.current_output = []
            return None
        
        if self.in_prompt:
            # We're in a prompt, track the command
            # Remove ANSI codes for tracking
            clean_text = self._clean_for_tracking(text)
            
            # Check if this looks like command input (not output)
            # Commands are usually on one line and end with newline
            if '\n' in clean_text or '\r' in clean_text:
                # Command might be complete
                # Extract the line before the newline
                lines = clean_text.split('\n')
                if lines:
                    first_line = lines[0].strip()
                    if first_line and not first_line.startswith('┌──'):
                        # This might be the command
                        self.current_command.append(first_line)
                        
                        # Check if this is actually output (starts with prompt-like text)
                        if not self.prompt_pattern.match(first_line):
                            # It's output, not command
                            self.current_output.append(clean_text)
                            self.in_prompt = False
                            return None
            else:
                # Still typing
                # Filter out control characters and ANSI
                if clean_text and not clean_text.startswith('\x1b'):
                    # Check if it's backspace
                    if '\b' in clean_text:
                        # Handle backspace - remove last character
                        for char in clean_text:
                            if char == '\b' and self.current_command:
                                # Remove last character from last command part
                                if self.current_command:
                                    last = self.current_command[-1]
                                    if last:
                                        self.current_command[-1] = last[:-1]
                                    else:
                                        self.current_command.pop()
                            elif char not in '\x1b\r\n\b':
                                if not self.current_command:
                                    self.current_command.append('')
                                self.current_command[-1] += char
                    else:
                        # Regular typing
                        if not self.current_command:
                            self.current_command.append('')
                        self.current_command[-1] += clean_text
        else:
            # Not in prompt, this is output
            clean_text = self._clean_for_tracking(text)
            if clean_text.strip():
                self.current_output.append(clean_text)
        
        return None
    
    def _clean_for_tracking(self, text: str) -> str:
        """Clean text for command tracking."""
        # Remove most ANSI codes (keep basic structure)
        text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
        text = re.sub(r'\x1b\][^\x07]*\x07', '', text)
        return text
    
    def finalize(self):
        """Finalize and return all commands."""
        # Don't forget the last command
        if self.in_prompt and self.current_command:
            cmd = ''.join(self.current_command).strip()
            if cmd:
                output = '\n'.join(self.current_output).strip()
                self.commands.append((self.last_prompt_time, cmd, output))
        
        return self.commands

