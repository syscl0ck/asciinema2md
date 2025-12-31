"""Hybrid approach: terminal emulator + event tracking."""

import re
from typing import List, Tuple
from .terminal import Terminal
from .ansi import strip_ansi


class HybridExtractor:
    """Extract commands using terminal emulator with snapshots."""
    
    def __init__(self, width: int, height: int):
        self.terminal = Terminal(width, height)
        self.prompt_pattern = re.compile(r'┌──\([^\)]+\)\-\[[^\]]+\]\r?\n└─[#\$]\s*')
        self.commands: List[Tuple[str, str]] = []
        
        # Track state
        self.last_prompt_pos = -1
        self.snapshots: List[Tuple[int, str]] = []  # (event_index, terminal_state)
        
    def process_events(self, events: List[Tuple[float, str, str]]) -> List[Tuple[str, str]]:
        """Process events and extract commands."""
        
        for i, (timestamp, event_type, text) in enumerate(events):
            if event_type != 'o':
                continue
            
            # Check for prompt
            if self.prompt_pattern.search(text):
                # Take snapshot before processing this prompt
                if i > 0:
                    snapshot = self.terminal.get_output()
                    self.snapshots.append((i, snapshot))
                
                self.last_prompt_pos = i
            
            # Process through terminal
            self.terminal.process_text(text)
            
            # Check if Enter was pressed (look for \r\r\n or cursor down + \r)
            if '\r\r\n' in text or '\u001b[1B\r' in text:
                # Take snapshot to capture command
                snapshot = self.terminal.get_output()
                self.snapshots.append((i, snapshot))
        
        # Final snapshot
        final_snapshot = self.terminal.get_output()
        self.snapshots.append((len(events), final_snapshot))
        
        # Extract commands from snapshots
        return self._extract_commands()
    
    def _extract_commands(self) -> List[Tuple[str, str]]:
        """Extract commands from snapshots."""
        commands = []
        
        # Process final terminal state
        final_output = self.terminal.get_output()
        final_output = strip_ansi(final_output)
        
        # Extract all commands from final output
        lines = final_output.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for prompt
            if self.prompt_pattern.search(line):
                # Extract command from next line or same line
                cmd = None
                
                # Check if command is on same line
                match = re.search(r'└─[#\$]\s*(.+)$', line)
                if match:
                    cmd = match.group(1).strip()
                elif i + 1 < len(lines):
                    # Command might be on next line
                    next_line = lines[i + 1]
                    # Check if it's a command (not another prompt)
                    if not self.prompt_pattern.search(next_line):
                        cmd = next_line.strip()
                
                if cmd:
                    # Clean command
                    cmd = re.sub(r'[^\x20-\x7E]', '', cmd)
                    cmd = cmd.strip()
                    
                    if cmd and len(cmd) < 500:
                        # Find output (until next prompt)
                        output_lines = []
                        start_idx = i + 2 if match else i + 1
                        j = start_idx
                        while j < len(lines):
                            if self.prompt_pattern.search(lines[j]):
                                break
                            output_lines.append(lines[j])
                            j += 1
                        
                        output_text = '\n'.join(output_lines)
                        output_text = self._clean_output(output_text)
                        
                        commands.append((cmd, output_text))
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
            if re.match(r'^".*"\s+\d+L,\s+\d+B', line):
                continue
            cleaned.append(line)
        
        while cleaned and not cleaned[0].strip():
            cleaned.pop(0)
        while cleaned and not cleaned[-1].strip():
            cleaned.pop()
        
        return '\n'.join(cleaned)

