"""Final improved extractor that tracks commands properly."""

import re
from typing import List, Tuple
from .terminal import Terminal
from .ansi import strip_ansi


class FinalExtractor:
    """Extract commands by tracking terminal state and command completion."""
    
    def __init__(self, width: int, height: int):
        self.terminal = Terminal(width, height)
        self.prompt_pattern = re.compile(r'┌──\([^\)]+\)\-\[[^\]]+\]\r?\n└─[#\$]\s*')
        self.commands: List[Tuple[str, str, float]] = []
        
        # Track command state
        self.current_command_line = ""
        self.last_prompt_time = 0.0
        self.last_prompt_idx = -1
        self.snapshots: List[Tuple[int, str, float]] = []
        
    def process_events(self, events: List[Tuple[float, str, str]]) -> List[Tuple[str, str]]:
        """Process events and extract commands."""
        
        for i, (timestamp, event_type, text) in enumerate(events):
            if event_type != 'o':
                continue
            
            # Check for prompt
            if self.prompt_pattern.search(text):
                # Save previous command if we have one
                if self.current_command_line:
                    cmd = self.current_command_line.strip()
                    if cmd:
                        output = self._get_output_for_command(i)
                        self.commands.append((cmd, output, self.last_prompt_time))
                
                # Reset for new command
                self.current_command_line = ""
                self.last_prompt_time = timestamp
                self.last_prompt_idx = i
                # Take snapshot
                snapshot = self.terminal.get_output()
                self.snapshots.append((i, snapshot, timestamp))
            
            # Process through terminal
            self.terminal.process_text(text)
            
            # Track command being typed (extract from terminal state)
            # Get current line that has the prompt
            current_output = self.terminal.get_output()
            current_clean = strip_ansi(current_output)
            lines = current_clean.split('\n')
            
            # Find the line with the current prompt
            for line in reversed(lines[-5:]):  # Check last few lines
                if self.prompt_pattern.search(line):
                    # Extract command from this line
                    match = re.search(r'└─[#\$]\s*(.+)$', line)
                    if match:
                        potential_cmd = match.group(1).strip()
                        # Only update if it's longer (user is typing)
                        if len(potential_cmd) > len(self.current_command_line):
                            # Filter out autocomplete (gray text appears but isn't part of actual command yet)
                            # The actual command is what's on the line after prompt
                            self.current_command_line = potential_cmd
            
            # Check if Enter was pressed
            if '\r\r\n' in text or '\u001b[1B\r' in text:
                # Command entered - finalize it
                if self.current_command_line:
                    cmd = self.current_command_line.strip()
                    cmd = re.sub(r'[^\x20-\x7E]', '', cmd)
                    if cmd:
                        output = self._get_output_for_command(i)
                        self.commands.append((cmd, output, self.last_prompt_time))
                    self.current_command_line = ""
        
        # Don't forget last command
        if self.current_command_line:
            cmd = self.current_command_line.strip()
            cmd = re.sub(r'[^\x20-\x7E]', '', cmd)
            if cmd:
                output = self._get_output_for_command(len(events))
                self.commands.append((cmd, output, self.last_prompt_time))
        
        # Also extract from final terminal state
        final_output = strip_ansi(self.terminal.get_output())
        final_commands = self._extract_from_output(final_output)
        
        # Merge commands
        commands_dict = {cmd: (cmd, output) for cmd, output, _ in self.commands}
        for cmd, output in final_commands:
            if cmd not in commands_dict:
                commands_dict[cmd] = (cmd, output)
        
        # Sort and return
        result = list(commands_dict.values())
        result.sort(key=lambda x: x[0])  # Sort by command for now
        
        return result
    
    def _extract_from_output(self, output: str) -> List[Tuple[str, str]]:
        """Extract commands from terminal output."""
        commands = []
        lines = output.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            if self.prompt_pattern.search(line):
                # Extract command
                match = re.search(r'└─[#\$]\s*(.+)$', line)
                if match:
                    cmd = match.group(1).strip()
                    cmd = re.sub(r'[^\x20-\x7E]', '', cmd)
                    
                    if (cmd and len(cmd) >= 2 and cmd[0].isalpha() and
                        (len(cmd) > 10 or ' ' in cmd or cmd in ['cd', 'ls', 'cp', 'mv', 'rm', 'cat', 'vim', 'nano', 'exit', 'pwd', 'mkdir'])):
                        
                        # Find output
                        output_lines = []
                        j = i + 1
                        while j < len(lines):
                            if self.prompt_pattern.search(lines[j]):
                                break
                            output_lines.append(lines[j])
                            j += 1
                        
                        output_text = self._clean_output('\n'.join(output_lines))
                        commands.append((cmd, output_text))
                        i = j - 1
            i += 1
        
        return commands
    
    def _get_output_for_command(self, event_idx: int) -> str:
        """Get output for a command."""
        # Look ahead for output until next prompt
        # This is simplified - in practice we'd track this better
        return ""
    
    def _clean_output(self, text: str) -> str:
        """Clean output text."""
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            if line.strip() == '~':
                continue
            if '-- INSERT --' in line:
                continue
            if re.match(r'^\d+,\d+.*All', line):
                continue
            if len(line.strip()) <= 2 and line.strip().isalpha():
                continue
            cleaned.append(line)
        
        while cleaned and not cleaned[0].strip():
            cleaned.pop(0)
        while cleaned and not cleaned[-1].strip():
            cleaned.pop()
        
        return '\n'.join(cleaned)

