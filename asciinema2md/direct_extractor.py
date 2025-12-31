"""Extract commands directly from events by finding complete command strings."""

import re
from typing import List, Tuple, Optional
from .ansi import strip_ansi


class DirectExtractor:
    """Extract commands by finding complete command strings in events."""
    
    def __init__(self):
        self.prompt_pattern = re.compile(r'┌──\([^\)]+\)\-\[[^\]]+\]\r?\n└─[#\$]\s*')
        self.commands: List[Tuple[str, str, int]] = []  # (command, output_start_idx, timestamp)
        self.events: List[Tuple[float, str, str]] = []
        
    def process_events(self, events: List[Tuple[float, str, str]]) -> List[Tuple[str, str]]:
        """Process events and extract commands."""
        self.events = events
        
        # Find complete command strings
        for i, (timestamp, event_type, text) in enumerate(events):
            if event_type != 'o':
                continue
            
            # Look for autocomplete suggestions (gray text with \u001b[38;2;153;153;153m)
            # These appear after typing part of a command
            if '\u001b[38;2;153;153;153m' in text:
                # Extract the autocomplete suggestion
                # Pattern: typed_part + gray_autocomplete
                # We need to look backwards to find what was typed
                autocomplete_match = re.search(r'\u001b\[38;2;153;153;153m([^\u001b]+)\u001b', text)
                if autocomplete_match:
                    autocomplete_text = autocomplete_match.group(1)
                    # Look backwards in events to find the command being typed
                    cmd_prefix = self._find_command_prefix(i)
                    if cmd_prefix:
                        full_cmd = cmd_prefix + autocomplete_text.strip()
                        # Clean and validate
                        full_cmd = re.sub(r'[^\x20-\x7E]', '', full_cmd).strip()
                        if (full_cmd and len(full_cmd) >= 3 and 
                            full_cmd[0].isalpha() and
                            (len(full_cmd) > 10 or ' ' in full_cmd)):
                            if full_cmd not in [c for c, _, _ in self.commands]:
                                output = self._find_output_for_command(i)
                                self.commands.append((full_cmd, output, timestamp))
            
            # Look for complete command strings (like "nmap -p -sV 10.10.11.99 -oA VersionScan")
            clean_text = strip_ansi(text)
            
            # Check if this looks like a complete command
            if (len(clean_text) > 5 and 
                len(clean_text) < 500 and
                not any(c in clean_text for c in '\x1b\r\n') and
                re.match(r'^[a-zA-Z0-9_/\-\.\s\$"\'=:;\[\]{}()]+$', clean_text.strip()) and
                (' ' in clean_text or len(clean_text) > 10)):  # Has space or is substantial
                
                cmd = clean_text.strip()
                # Filter out non-commands
                if (cmd and
                    len(cmd) >= 2 and  # At least 2 characters
                    not cmd.startswith('#') and  # Not a comment
                    not cmd.startswith('~') and  # Not vim indicator
                    not (cmd.startswith('E486') or cmd.startswith('E387')),  # Not vim error
                    len(cmd) > 0 and cmd[0].isalpha() and  # Starts with letter
                    (len(cmd) > 10 or ' ' in cmd)):  # Either substantial or has space
                    
                    # Find the output for this command
                    output = self._find_output_for_command(i)
                    self.commands.append((cmd, output, timestamp))
        
        # Also extract from prompts + following text
        self._extract_from_prompts()
        
        # Deduplicate and filter commands
        self._deduplicate_commands()
        
        # Sort by timestamp and return
        self.commands.sort(key=lambda x: x[2])
        return [(cmd, output) for cmd, output, _ in self.commands]
    
    def _deduplicate_commands(self):
        """Remove duplicate and invalid commands."""
        seen = set()
        filtered = []
        
        for cmd, output, timestamp in self.commands:
            # Skip very short commands (typing artifacts)
            if len(cmd) < 3:
                continue
            
            # Skip vim error messages
            if cmd.startswith('E486') or cmd.startswith('E387'):
                continue
            
            # Skip single words unless they're common commands
            if ' ' not in cmd and cmd not in ['cd', 'ls', 'cp', 'mv', 'rm', 'cat', 'vim', 'nano', 'exit', 'pwd', 'whoami']:
                continue
            
            # Skip if command looks like file content or error
            if cmd.startswith('The following') or 'desirable for' in cmd:
                continue
            
            # Skip if we've seen this exact command recently (within 2 seconds)
            skip = False
            for seen_cmd, seen_ts in seen:
                if seen_cmd == cmd and abs(seen_ts - timestamp) < 2.0:
                    skip = True
                    break
            if skip:
                continue
            
            seen.add((cmd, timestamp))
            filtered.append((cmd, output, timestamp))
        
        self.commands = filtered
    
    def _find_output_for_command(self, cmd_idx: int) -> str:
        """Find output that follows a command."""
        output_lines = []
        
        # Look ahead for output (until next prompt or next command)
        for i in range(cmd_idx + 1, min(cmd_idx + 100, len(self.events))):
            timestamp, event_type, text = self.events[i]
            if event_type != 'o':
                continue
            
            # Stop at next prompt
            if self.prompt_pattern.search(text):
                break
            
            # Stop at next complete command
            clean_text = strip_ansi(text)
            clean_stripped = clean_text.strip()
            if (len(clean_stripped) > 5 and 
                len(clean_stripped) < 500 and
                not any(c in clean_text for c in '\x1b\r\n') and
                ' ' in clean_stripped and
                len(clean_stripped) > 0 and clean_stripped[0].isalpha()):
                break
            
            # Collect output
            clean_text = strip_ansi(text)
            if clean_text.strip() and not clean_text.startswith('┌──'):
                output_lines.append(clean_text)
        
        return self._clean_output('\n'.join(output_lines))
    
    def _extract_from_prompts(self):
        """Extract commands that appear after prompts."""
        for i, (timestamp, event_type, text) in enumerate(self.events):
            if event_type != 'o':
                continue
            
            if self.prompt_pattern.search(text):
                # Look for command in next few events
                for j in range(i + 1, min(i + 50, len(self.events))):
                    ts, et, txt = self.events[j]
                    if et != 'o':
                        continue
                    
                    # Check if next prompt (command finished)
                    if self.prompt_pattern.search(txt):
                        break
                    
                    # Look for complete command string
                    clean_text = strip_ansi(txt)
                    clean_stripped = clean_text.strip()
                    if (len(clean_stripped) > 5 and 
                        len(clean_stripped) < 500 and
                        not any(c in clean_text for c in '\x1b\r\n') and
                        ' ' in clean_stripped and
                        len(clean_stripped) > 0 and clean_stripped[0].isalpha()):
                        
                        cmd = clean_text.strip()
                        if cmd not in [c for c, _, _ in self.commands]:
                            output = self._find_output_for_command(j)
                            self.commands.append((cmd, output, ts))
                        break
    
    def _find_command_prefix(self, event_idx: int) -> Optional[str]:
        """Find the command prefix that was typed before an autocomplete suggestion."""
        # Look backwards for the command being typed
        prefix_chars = []
        
        for i in range(max(0, event_idx - 20), event_idx):
            if i >= len(self.events):
                break
            timestamp, event_type, text = self.events[i]
            if event_type != 'o':
                continue
            
            clean_text = strip_ansi(text)
            
            # Look for typed characters (not autocomplete)
            # Autocomplete is gray, typed text is usually normal or underlined
            if '\u001b[38;2;153;153;153m' not in text:  # Not gray (autocomplete)
                # Extract visible characters
                for char in clean_text:
                    if 32 <= ord(char) <= 126:  # Printable ASCII
                        if char == '\b':
                            if prefix_chars:
                                prefix_chars.pop()
                        else:
                            prefix_chars.append(char)
                    elif char in '\r\n':
                        # Reset on newline
                        if prefix_chars:
                            return ''.join(prefix_chars).strip()
                        prefix_chars = []
        
        result = ''.join(prefix_chars).strip()
        return result if result else None
    
    def _clean_output(self, text: str) -> str:
        """Clean output text - remove typing artifacts and vim noise."""
        lines = text.split('\n')
        cleaned = []
        
        # Track progressive sequences (typing artifacts like "a", "as", "asc", "asciinema")
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
                # Keep only if it's a meaningful short string (like "OK", "No", etc.)
                if line_stripped.lower() not in ['ok', 'no', 'yes', 'id', 'ip']:
                    continue
            
            # Remove lines that are just single characters (typing artifacts)
            if len(line_stripped) == 1 and line_stripped.isalpha():
                continue
            
            # Remove progressive character sequences (typing artifacts)
            # e.g., "a", "as", "asc", "asciinema" - each is a prefix of the next
            if prev_line and len(line_stripped) > len(prev_line) and prev_line in line_stripped:
                # Current line contains previous line as prefix - likely typing artifact
                prev_line = line_stripped
                continue
            
            # Remove autocomplete suggestion messages
            if 'Completing' in line and 'executable file' in line:
                continue
            
            # Remove ANSI escape sequences that weren't stripped
            if line_stripped.startswith('[') and ('?25' in line or '?1' in line or '?2004' in line):
                continue
            # Remove lines that are just control sequences
            if re.match(r'^\[.*\]$', line_stripped):
                continue
            # Remove vim error messages
            if line_stripped.startswith('E486') or line_stripped.startswith('E387'):
                continue
            # Remove lines that are just numbers (vim line numbers)
            if re.match(r'^\s*\d+\s*$', line_stripped):
                continue
            
            # Remove lines that are just punctuation or special characters
            if len(line_stripped) > 0 and not any(c.isalnum() for c in line_stripped):
                continue
            
            # Remove lines that look like partial words being typed
            # (e.g., "a", "as", "asc" - but keep if it's a complete word)
            if len(line_stripped) < 4 and line_stripped.isalpha():
                # Check if this appears to be part of a progressive sequence
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
        
        # Additional pass: remove progressive sequences (typing artifacts)
        # e.g., "a", "as", "asc", "asciinema" where each is a prefix of the next
        final_cleaned = []
        i = 0
        while i < len(cleaned):
            line = cleaned[i]
            stripped = line.strip()
            
            # Check if this is part of a progressive sequence
            is_progressive = False
            if i > 0:
                prev_stripped = cleaned[i-1].strip()
                # If current line contains previous as prefix, it's progressive
                if prev_stripped and stripped.startswith(prev_stripped) and len(stripped) > len(prev_stripped):
                    is_progressive = True
            if i < len(cleaned) - 1:
                next_stripped = cleaned[i+1].strip()
                # If next line contains current as prefix, current is progressive
                if next_stripped and next_stripped.startswith(stripped) and len(next_stripped) > len(stripped):
                    is_progressive = True
            
            # Also check if this line is a prefix of a later line (progressive sequence)
            if not is_progressive and len(stripped) < 15:
                for j in range(i + 1, min(i + 10, len(cleaned))):
                    later_stripped = cleaned[j].strip()
                    if later_stripped.startswith(stripped) and len(later_stripped) > len(stripped) + 2:
                        is_progressive = True
                        break
            
            # Skip lines that are clearly typing artifacts
            if len(stripped) <= 2 and stripped.isalpha():
                # Check if next few lines are also short chars (typing)
                short_count = 0
                j = i
                while j < len(cleaned) and len(cleaned[j].strip()) <= 2 and cleaned[j].strip().isalpha():
                    short_count += 1
                    j += 1
                # If we have many short lines in a row, skip them (typing artifacts)
                if short_count > 2:
                    i = j
                    continue
            
            # Skip lines that are just ANSI sequences
            if stripped.startswith('[') and ('?25' in stripped or '?1' in stripped or '?2004' in stripped):
                i += 1
                continue
            # Also catch ANSI sequences that have numbers before them (vim line numbers)
            if re.match(r'^\s*\d+.*\[.*\?25', stripped):
                i += 1
                continue
            # Remove vim file info lines like '"/etc/hosts"'
            if re.match(r'^".*"\s+\d+L,\s+\d+B', stripped):
                i += 1
                continue
            # Remove vim write info like " 1L, 21B written"
            if re.match(r'^\s*\d+L,\s+\d+B\s+written', stripped):
                i += 1
                continue
            # Remove vim file size info like " 9L, 208B"
            if re.match(r'^\s*\d+L,\s+\d+B\s*$', stripped):
                i += 1
                continue
            # Remove "Completing file" messages
            if stripped.startswith('Completing'):
                i += 1
                continue
            # Remove vim artifacts like "▽  Pzz\[0%m           [>c"
            if '▽' in stripped or 'Pzz' in stripped or '[>c' in stripped:
                i += 1
                continue
            # Remove partial paths (typing artifacts like "osts", "/etc/host")
            if len(stripped) < 8 and ('/' in stripped or stripped.endswith('osts') or stripped.endswith('ost')):
                # Check if it's a partial path
                if '/' in stripped or stripped in ['osts', 'ost', 'host', 'hosts']:
                    i += 1
                    continue
            # Remove "/etc/host" (partial path)
            if stripped == '/etc/host':
                i += 1
                continue
            # Remove very short lines that are just command names (typing artifacts)
            if len(stripped) <= 4 and stripped in ['vim', 'env', 'mkd', 'cp', 'cd', 'ls']:
                i += 1
                continue
            # Remove partial commands like "cp r"
            if len(stripped) <= 5 and stripped.startswith(('cp ', 'mv ', 'rm ', 'cd ', 'ls ')):
                i += 1
                continue
            # Remove commands that appear in output (typing artifacts)
            # But be careful - only remove if it's clearly a duplicate command
            if stripped in ['vim /etc/hosts', 'vim /etc/resolv.conf', 'vim .env', 'vim users.txt']:
                # This is a command appearing in output, remove it
                i += 1
                continue
            if (stripped.startswith('vim /') or stripped.startswith('nmap ') or stripped.startswith('apt ')) and len(stripped) < 50:
                # Check if this is a complete command (not part of file content)
                if re.match(r'^(vim|nmap|apt)\s+[^\s]+', stripped):
                    i += 1
                    continue
            # Remove vim file quotes like '"/etc/hosts"'
            if re.match(r'^"/.*"$', stripped):
                i += 1
                continue
            # Remove partial text like "# L"
            if len(stripped) <= 3 and stripped.startswith('#'):
                i += 1
                continue
            
            # Skip progressive sequences (typing artifacts)
            # Also check if this line is similar to previous (e.g., "asciinema" vs "asciinem")
            if is_progressive:
                i += 1
                continue
            if i > 0:
                prev_stripped = cleaned[i-1].strip()
                # If lines are very similar (one is almost the same as other), skip the shorter one
                if prev_stripped and stripped:
                    if (prev_stripped.startswith(stripped) or stripped.startswith(prev_stripped)) and abs(len(prev_stripped) - len(stripped)) <= 2:
                        if len(stripped) < len(prev_stripped):
                            # Remove the shorter one from final_cleaned if we already added it
                            if final_cleaned and final_cleaned[-1] == cleaned[i-1]:
                                final_cleaned.pop()
                            i += 1
                            continue
            
            final_cleaned.append(line)
            i += 1
        
        # Final pass: remove vim tildes and other artifacts
        result = '\n'.join(final_cleaned)
        # Remove ANSI sequences from prompts
        result = re.sub(r'\[\?1h\s*', '', result)
        result = re.sub(r'\[\?2004[hl]\s*', '', result)
        # Remove duplicate prompts at the end
        lines = result.split('\n')
        # Remove duplicate consecutive prompts and commands in output
        cleaned_lines = []
        for i, line in enumerate(lines):
            if '┌──(' in line and i > 0 and '┌──(' in lines[i-1]:
                # Skip duplicate prompt
                continue
            # Remove commands that appear in output
            stripped = line.strip()
            if stripped in ['vim /etc/hosts', 'vim /etc/resolv.conf']:
                continue
            cleaned_lines.append(line)
        result = '\n'.join(cleaned_lines)
        # Remove lines that are just tildes
        result_lines = result.split('\n')
        result_lines = [l for l in result_lines if not (l.strip() == '~' or l.strip().startswith('~ '))]
        
        # Remove excessive empty lines
        final_result = []
        prev_empty = False
        for line in result_lines:
            if not line.strip():
                if not prev_empty:
                    final_result.append(line)
                prev_empty = True
            else:
                final_result.append(line)
                prev_empty = False
        
        return '\n'.join(final_result)

