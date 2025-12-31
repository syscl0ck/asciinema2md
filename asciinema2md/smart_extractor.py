"""Smart extractor that properly tracks typed commands vs autocomplete."""

import re
from typing import List, Tuple
from .terminal import Terminal
from .ansi import strip_ansi


class SmartExtractor:
    """Extract commands by tracking what's actually typed, not autocomplete."""
    
    def __init__(self, width: int, height: int):
        self.terminal = Terminal(width, height)
        self.prompt_pattern = re.compile(r'┌──\([^\)]+\)\-\[[^\]]+\]\r?\n└─[#\$]\s*')
        self.commands: List[Tuple[str, str, float]] = []
        
    def process_events(self, events: List[Tuple[float, str, str]]) -> List[Tuple[str, str]]:
        """Process events and extract commands."""
        
        last_prompt_time = 0.0
        last_prompt_idx = -1
        
        for i, (timestamp, event_type, text) in enumerate(events):
            if event_type != 'o':
                continue
            
            # Check for prompt
            if self.prompt_pattern.search(text):
                # Extract command from terminal state before this new prompt
                if i > 0 and last_prompt_idx >= 0:
                    cmd, output = self._extract_command_from_terminal(last_prompt_idx, i)
                    if cmd:
                        self.commands.append((cmd, output, last_prompt_time))
                
                last_prompt_time = timestamp
                last_prompt_idx = i
            
            # Process through terminal
            self.terminal.process_text(text)
            
            # Check if Enter was pressed
            if '\r\r\n' in text or '\u001b[1B\r' in text:
                # Take snapshot to capture command
                cmd, output = self._extract_command_from_terminal(last_prompt_idx, i)
                if cmd:
                    # Check if we already have this command
                    if not any(c == cmd for c, _, _ in self.commands):
                        self.commands.append((cmd, output, last_prompt_time))
        
        # Extract last command
        if last_prompt_idx >= 0:
            cmd, output = self._extract_command_from_terminal(last_prompt_idx, len(events))
            if cmd:
                if not any(c == cmd for c, _, _ in self.commands):
                    self.commands.append((cmd, output, last_prompt_time))
        
        # Sort by timestamp
        self.commands.sort(key=lambda x: x[2])
        return [(cmd, output) for cmd, output, _ in self.commands]
    
    def _extract_command_from_terminal(self, prompt_start: int, prompt_end: int) -> Tuple[str, str]:
        """Extract command from terminal state between two prompts."""
        # Get current terminal output
        output = self.terminal.get_output()
        output_clean = strip_ansi(output)
        lines = output_clean.split('\n')
        
        # Find the prompt and command
        for i, line in enumerate(lines):
            if self.prompt_pattern.search(line):
                # Extract command
                match = re.search(r'└─[#\$]\s*(.+)$', line)
                if match:
                    cmd = match.group(1).strip()
                    cmd = re.sub(r'[^\x20-\x7E]', '', cmd)
                    
                    # Filter valid commands
                    if (cmd and len(cmd) >= 2 and cmd[0].isalpha() and
                        (len(cmd) > 10 or ' ' in cmd or cmd in ['cd', 'ls', 'cp', 'mv', 'rm', 'cat', 'vim', 'nano', 'exit', 'pwd', 'mkdir'])):
                        
                        # Find output
                        output_lines = []
                        for j in range(i + 1, len(lines)):
                            if self.prompt_pattern.search(lines[j]):
                                break
                            output_lines.append(lines[j])
                        
                        output_text = self._clean_output('\n'.join(output_lines))
                        return (cmd, output_text)
        
        return ("", "")
    
    def _clean_output(self, text: str) -> str:
        """Clean output text - remove typing artifacts and vim noise."""
        lines = text.split('\n')
        cleaned = []
        prev_line = None
        
        for line in lines:
            line_stripped = line.strip()
            
            # Remove vim artifacts
            if line_stripped == '~':
                continue
            if '-- INSERT --' in line or '-- REPLACE --' in line:
                continue
            if re.match(r'^\d+,\d+.*All', line):
                continue
            if line_stripped in ['▽', 'zz']:
                continue
            if re.match(r'^".*"\s+\d+L,\s+\d+B', line):
                continue
            if re.match(r'^\d+,\d+.*written', line):
                continue
            
            # Remove very short lines (likely typing artifacts)
            if len(line_stripped) <= 2:
                if line_stripped.lower() not in ['ok', 'no', 'yes', 'id', 'ip']:
                    continue
            
            # Remove lines that are just single characters
            if len(line_stripped) == 1 and line_stripped.isalpha():
                continue
            
            # Remove progressive character sequences (typing artifacts)
            if prev_line and len(line_stripped) > len(prev_line) and prev_line in line_stripped:
                prev_line = line_stripped
                continue
            
            # Remove autocomplete suggestion messages
            if 'Completing' in line and 'executable file' in line:
                continue
            
            # Remove ANSI escape sequences
            if line_stripped.startswith('[') and ('?25' in line or '?1' in line or '?2004' in line):
                continue
            if re.match(r'^\[.*\]$', line_stripped):
                continue
            if line_stripped.startswith('E486') or line_stripped.startswith('E387'):
                continue
            if re.match(r'^\s*\d+\s*$', line_stripped):
                continue
            
            # Remove lines that are just punctuation
            if len(line_stripped) > 0 and not any(c.isalnum() for c in line_stripped):
                continue
            
            # Remove partial words being typed
            if len(line_stripped) < 4 and line_stripped.isalpha():
                if prev_line and line_stripped in prev_line:
                    prev_line = line_stripped
                    continue
            
            prev_line = line_stripped
            cleaned.append(line)
        
        # Remove leading/trailing empty lines
        while cleaned and not cleaned[0].strip():
            cleaned.pop(0)
        while cleaned and not cleaned[-1].strip():
            cleaned.pop()
        
        return '\n'.join(cleaned)

