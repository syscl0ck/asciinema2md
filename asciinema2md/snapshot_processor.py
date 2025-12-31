"""Process events by taking snapshots at key moments."""

import re
from typing import List, Tuple, Optional
from .terminal import Terminal
from .ansi import strip_ansi


class SnapshotProcessor:
    """Take snapshots of terminal state to extract commands."""
    
    def __init__(self, width: int, height: int):
        self.terminal = Terminal(width, height)
        self.prompt_pattern = re.compile(r'┌──\([^\)]+\)\-\[[^\]]+\]\r?\n└─[#\$]\s*')
        self.commands: List[Tuple[str, str]] = []
        self.snapshots: List[Tuple[float, str]] = []  # (timestamp, terminal_state)
        
    def process_events(self, events: List[Tuple[float, str, str]]) -> List[Tuple[str, str]]:
        """Process events and extract commands."""
        
        last_prompt_time = None
        last_snapshot_time = None
        
        for timestamp, event_type, text in events:
            if event_type != 'o':
                continue
            
            # Process through terminal
            self.terminal.process_text(text)
            
            # Check for prompt
            if self.prompt_pattern.search(text):
                # Take snapshot before this prompt (captures previous command's final state)
                if last_prompt_time is not None:
                    snapshot = self.terminal.get_output()
                    self.snapshots.append((last_prompt_time, snapshot))
                
                last_prompt_time = timestamp
                continue
            
            # Check if Enter was pressed (\r\r\n or \r\n after some typing)
            if '\r\r\n' in text or (last_snapshot_time and timestamp - last_snapshot_time > 0.1 and '\r\n' in text):
                # Take snapshot to capture command
                snapshot = self.terminal.get_output()
                self.snapshots.append((timestamp, snapshot))
                last_snapshot_time = timestamp
        
        # Process snapshots to extract commands
        return self._extract_commands_from_snapshots()
    
    def _extract_commands_from_snapshots(self) -> List[Tuple[str, str]]:
        """Extract commands from snapshots."""
        # For now, use the last snapshot which should have the final state
        # This is a simplified version - in practice we'd compare snapshots
        if not self.snapshots:
            return []
        
        # Get final terminal state
        final_output = self.terminal.get_output()
        final_output = strip_ansi(final_output)
        
        # Extract commands using pattern matching
        return self._extract_from_output(final_output)
    
    def _extract_from_output(self, output: str) -> List[Tuple[str, str]]:
        """Extract commands from terminal output."""
        commands = []
        lines = output.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for prompt
            if self.prompt_pattern.search(line):
                # Found prompt, next line should have command
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # Extract command (everything after prompt end marker)
                    match = re.search(r'└─[#\$]\s*(.+)$', next_line)
                    if not match:
                        # Command might be on same line
                        match = re.search(r'└─[#\$]\s*(.+)$', line)
                    
                    if match:
                        command = match.group(1).strip()
                        command = re.sub(r'[^\x20-\x7E]', '', command)  # Clean
                        
                        if command and len(command) < 200:  # Reasonable length
                            # Find output (until next prompt)
                            output_lines = []
                            j = i + 2
                            while j < len(lines):
                                if self.prompt_pattern.search(lines[j]):
                                    break
                                output_lines.append(lines[j])
                                j += 1
                            
                            output_text = '\n'.join(output_lines)
                            output_text = self._clean_output(output_text)
                            
                            commands.append((command, output_text))
                            i = j - 1
            i += 1
        
        return commands
    
    def _clean_output(self, text: str) -> str:
        """Clean output text."""
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            if line.strip() == '~':
                continue
            if '-- INSERT --' in line or '-- REPLACE --' in line:
                continue
            if re.match(r'^\d+,\d+.*All', line):
                continue
            if line.strip() in ['▽', 'zz']:
                continue
            cleaned.append(line)
        
        while cleaned and not cleaned[0].strip():
            cleaned.pop(0)
        while cleaned and not cleaned[-1].strip():
            cleaned.pop()
        
        return '\n'.join(cleaned)

