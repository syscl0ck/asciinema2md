"""Improved command extraction using terminal emulator snapshots."""

import re
from typing import List, Tuple, Optional
from .terminal import Terminal
from .ansi import strip_ansi


class ImprovedExtractor:
    """Extract commands by taking terminal snapshots at key moments."""
    
    def __init__(self, width: int, height: int):
        self.terminal = Terminal(width, height)
        self.prompt_pattern = re.compile(r'┌──\([^\)]+\)\-\[[^\]]+\]\r?\n└─[#\$]\s*')
        self.commands: List[Tuple[str, str, float]] = []
        
        # Track state
        self.last_prompt_idx = -1
        self.command_snapshots: List[Tuple[int, str, float]] = []  # (event_idx, terminal_state, timestamp)
        
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
                    self.command_snapshots.append((i, snapshot, timestamp))
                self.last_prompt_idx = i
            
            # Process through terminal
            self.terminal.process_text(text)
            
            # Check if Enter was pressed
            if '\r\r\n' in text or (i > 0 and '\u001b[1B\r' in text):
                # Take snapshot to capture command
                snapshot = self.terminal.get_output()
                self.command_snapshots.append((i, snapshot, timestamp))
        
        # Final snapshot
        final_snapshot = self.terminal.get_output()
        self.command_snapshots.append((len(events), final_snapshot, events[-1][0] if events else 0.0))
        
        # Extract commands from snapshots
        return self._extract_commands_from_snapshots()
    
    def _extract_commands_from_snapshots(self) -> List[Tuple[str, str]]:
        """Extract commands by analyzing terminal snapshots."""
        commands = []
        
        # Process each snapshot to find commands
        for i, (snapshot_idx, snapshot, timestamp) in enumerate(self.command_snapshots):
            snapshot_clean = strip_ansi(snapshot)
            lines = snapshot_clean.split('\n')
            
            # Look for prompts and extract commands
            for line_idx, line in enumerate(lines):
                if self.prompt_pattern.search(line):
                    # Found a prompt, look for command
                    # Command is usually on the same line after the prompt, or next line
                    cmd = None
                    
                    # Try to extract from same line
                    match = re.search(r'└─[#\$]\s*(.+)$', line)
                    if match:
                        cmd = match.group(1).strip()
                    elif line_idx + 1 < len(lines):
                        # Check next line
                        next_line = lines[line_idx + 1]
                        if not self.prompt_pattern.search(next_line):
                            cmd = next_line.strip()
                    
                    if cmd:
                        # Clean command
                        cmd = re.sub(r'[^\x20-\x7E]', '', cmd)
                        cmd = cmd.strip()
                        
                        # Filter valid commands
                        if (cmd and 
                            len(cmd) >= 2 and
                            not cmd.startswith('#') and
                            not cmd.startswith('~') and
                            cmd[0].isalpha() and
                            (len(cmd) > 10 or ' ' in cmd or cmd in ['cd', 'ls', 'cp', 'mv', 'rm', 'cat', 'vim', 'nano', 'exit', 'pwd'])):
                            
                            # Find output (until next prompt in this or next snapshot)
                            output = self._find_output_for_command(snapshot_idx, line_idx, lines, i)
                            
                            # Check if we already have this command
                            if not any(c == cmd for c, _, _ in commands):
                                commands.append((cmd, output, timestamp))
        
        # Sort by timestamp
        commands.sort(key=lambda x: x[2])
        return [(cmd, output) for cmd, output, _ in commands]
    
    def _find_output_for_command(self, snapshot_idx: int, line_idx: int, lines: List[str], snapshot_num: int) -> str:
        """Find output for a command."""
        output_lines = []
        
        # Look in current snapshot
        start_idx = line_idx + 2  # Skip prompt line and command line
        for i in range(start_idx, len(lines)):
            if self.prompt_pattern.search(lines[i]):
                break
            output_lines.append(lines[i])
        
        # Also check next snapshot if available
        if snapshot_num + 1 < len(self.command_snapshots):
            next_snapshot = self.command_snapshots[snapshot_num + 1][1]
            next_clean = strip_ansi(next_snapshot)
            next_lines = next_clean.split('\n')
            
            for line in next_lines:
                if self.prompt_pattern.search(line):
                    break
                output_lines.append(line)
        
        return self._clean_output('\n'.join(output_lines))
    
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
            if re.match(r'^\d+,\d+.*written', line):
                continue
            if len(line.strip()) <= 2 and line.strip().isalpha():
                # Skip very short lines that are likely typing artifacts
                continue
            if line.strip().startswith('[') and ('?25' in line or '?1' in line):
                continue
            
            cleaned.append(line)
        
        # Remove leading/trailing empty lines
        while cleaned and not cleaned[0].strip():
            cleaned.pop(0)
        while cleaned and not cleaned[-1].strip():
            cleaned.pop()
        
        return '\n'.join(cleaned)

