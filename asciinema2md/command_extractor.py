"""Event-driven command extraction from asciinema events."""

import re
from typing import List, Tuple, Optional
from .ansi import strip_ansi


class CommandExtractor:
    """Extract commands by tracking events in real-time."""
    
    def __init__(self):
        self.prompt_pattern = re.compile(r'┌──\([^\)]+\)\-\[[^\]]+\]\r?\n└─[#\$]\s*')
        self.commands: List[Tuple[str, str, float]] = []  # (command, output, timestamp)
        
        # State tracking
        self.current_command_chars = []  # Characters being typed
        self.current_output_lines = []
        self.in_prompt = False
        self.command_entered = False
        self.last_prompt_time = 0.0
        self.last_event_was_typing = False
        
    def process_events(self, events: List[Tuple[float, str, str]]) -> List[Tuple[str, str]]:
        """Process all events and return list of (command, output) tuples."""
        
        for timestamp, event_type, text in events:
            if event_type != 'o':
                continue
            
            # Check for new prompt
            if self.prompt_pattern.search(text):
                self._handle_new_prompt(timestamp)
                continue
            
            # Process the event
            if self.in_prompt and not self.command_entered:
                self._process_command_input(text, timestamp)
            else:
                self._process_output(text)
        
        # Don't forget the last command
        self._finalize_current_command()
        
        # Return commands without timestamps
        return [(cmd, output) for cmd, output, _ in self.commands]
    
    def _handle_new_prompt(self, timestamp: float):
        """Handle when a new prompt appears."""
        # If we were tracking a command, finalize it
        if self.command_entered or self.current_command_chars:
            self._finalize_current_command()
        
        # Reset for new command
        self.current_command_chars = []
        self.current_output_lines = []
        self.in_prompt = True
        self.command_entered = False
        self.last_prompt_time = timestamp
        self.last_event_was_typing = False
    
    def _process_command_input(self, text: str, timestamp: float):
        """Process input while in a prompt (command being typed)."""
        clean_text = strip_ansi(text)
        
        # Check if this is a complete command string (shell echo)
        # These appear as single events with the full command
        # Examples: "nmap -p -sV 10.10.11.99 -oA VersionScan" at line 307
        #           "vim /etc/hosts" at line 453
        if (len(clean_text) > 5 and 
            len(clean_text) < 500 and
            not any(c in clean_text for c in '\x1b') and
            '\r' not in clean_text and '\n' not in clean_text and
            re.match(r'^[a-zA-Z0-9_/\-\.\s\$"\'=:;\[\]{}()]+$', clean_text.strip())):
            # This looks like a complete command string
            cmd = clean_text.strip()
            # Filter out things that are clearly not commands
            if (not cmd.startswith('#') and  # Not a comment
                ' ' in cmd or len(cmd) > 3):  # Has space or is substantial
                self.current_command_chars = list(cmd)
                self.command_entered = True
                self.in_prompt = False
                self.last_event_was_typing = False
                return
        
        # Check if Enter was pressed
        # Enter sequences: \r\r\n, \r\n, or \r\r followed by prompt
        if '\r\r\n' in text:
            self.command_entered = True
            self.in_prompt = False
            self.last_event_was_typing = False
            return
        
        # Check for \r\r pattern (part of Enter sequence)
        if '\r\r' in text and self.current_command_chars:
            # This is likely Enter being pressed
            self.command_entered = True
            self.in_prompt = False
            self.last_event_was_typing = False
            return
        
        # Check for cursor movement that might indicate Enter
        # \u001b[1B\r is cursor down + carriage return (Enter)
        if '\u001b[1B\r' in text and self.current_command_chars:
            self.command_entered = True
            self.in_prompt = False
            self.last_event_was_typing = False
            return
        
        # Process character-by-character input
        # First, extract visible characters from the text
        # Remove ANSI codes but keep the actual characters
        visible_chars = []
        i = 0
        while i < len(text):
            char = text[i]
            
            # Skip ANSI escape sequences
            if char == '\x1b':
                i += 1
                if i < len(text) and text[i] == '[':
                    # Skip until command letter
                    i += 1
                    while i < len(text) and text[i] not in 'ABCDEFGHJKSTfmsu':
                        i += 1
                    if i < len(text):
                        i += 1
                elif i < len(text) and text[i] == ']':
                    # OSC sequence
                    i += 1
                    while i < len(text) and text[i] != '\x07':
                        i += 1
                    if i < len(text):
                        i += 1
                continue
            
            # Handle control characters
            if char == '\b':
                # Backspace - remove last character from buffer
                if self.current_command_chars:
                    self.current_command_chars.pop()
            elif 32 <= ord(char) <= 126:  # Printable ASCII
                # Regular character - add to buffer
                self.current_command_chars.append(char)
            elif char == '\r':
                # Carriage return - might be part of Enter
                pass
            elif char == '\n':
                # Newline - Enter might be pressed
                if self.current_command_chars:
                    # Command is complete
                    self.command_entered = True
                    self.in_prompt = False
                    break
            
            i += 1
        
        # If we added characters, mark as typing
        if self.current_command_chars:
            self.last_event_was_typing = True
    
    def _process_output(self, text: str):
        """Process output (after command entered)."""
        clean_text = strip_ansi(text)
        
        # Skip prompts in output
        if self.prompt_pattern.search(clean_text):
            return
        
        # Skip empty or whitespace-only
        if clean_text.strip():
            self.current_output_lines.append(clean_text)
    
    def _finalize_current_command(self):
        """Finalize the current command and add it to the list."""
        if not self.current_command_chars and not self.command_entered:
            return
        
        # Extract command
        command = ''.join(self.current_command_chars).strip()
        
        # Clean command
        command = re.sub(r'[^\x20-\x7E]', '', command)  # Remove non-printable
        command = command.strip()
        
        # Filter out obviously wrong commands
        if not command:
            return
        if len(command) > 500:  # Too long
            return
        if command.count(' ') > 100:  # Too many spaces
            return
        # Filter out file content that might be mistaken for commands
        if command.startswith('#') and 'following' in command.lower():
            return
        
        # Clean output
        output = '\n'.join(self.current_output_lines)
        output = self._clean_output(output)
        
        # Only add if we have a valid command
        if command:
            self.commands.append((command, output, self.last_prompt_time))
    
    def _clean_output(self, text: str) -> str:
        """Clean output text - remove vim artifacts and noise."""
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
            # Remove vim status lines
            if re.match(r'^".*"\s+\d+L,\s+\d+B', line):
                continue
            if re.match(r'^\d+,\d+.*written', line):
                continue
            # Remove lines that are just prompt-like but not actual prompts
            if line.strip().startswith('┌──') and '└─' not in line:
                continue
            
            cleaned.append(line)
        
        # Remove leading/trailing empty lines
        while cleaned and not cleaned[0].strip():
            cleaned.pop(0)
        while cleaned and not cleaned[-1].strip():
            cleaned.pop()
        
        return '\n'.join(cleaned)

