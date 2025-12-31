"""Detect commands and separate them from output."""

import re
from typing import List, Tuple, Optional


# Common prompt patterns - more flexible
PROMPT_PATTERNS = [
    r'┌──\([^\)]+\)\-\[[^\]]+\]\r?\n└─[#\$] ',  # Kali/Zsh prompt with box drawing
    r'[^\s]+\@[^\s]+\:[^\$#\n]+\$ ',  # user@host:path$ 
    r'[^\s]+\@[^\s]+\:[^\$#\n]+\# ',  # user@host:path#
    r'[^\$#\n]+\$ ',                    # path$ 
    r'[^\$#\n]+\# ',                    # path#
    r'\$ ',                             # $ 
    r'\# ',                             # # 
    r'> ',                              # > 
    r'PS [^\>]+\> ',                    # PowerShell prompt
]


def detect_prompt(text: str) -> Optional[Tuple[str, int]]:
    """
    Detect if text contains a command prompt.
    
    Args:
        text: Text to check (can be multi-line)
        
    Returns:
        Tuple of (prompt_string, position) if found, None otherwise
    """
    for pattern in PROMPT_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return (match.group(0), match.start())
    return None


def extract_command(line: str, prompt: str) -> Optional[str]:
    """
    Extract command from a line that starts with a prompt.
    
    Args:
        line: Line containing prompt and command
        prompt: The prompt string to remove
        
    Returns:
        Command string or None
    """
    if line.startswith(prompt):
        command = line[len(prompt):].strip()
        if command:
            return command
    return None


def is_likely_command(text: str) -> bool:
    """
    Heuristic to determine if text looks like a command.
    
    Args:
        text: Text to check
        
    Returns:
        True if text looks like a command
    """
    # Commands are usually short, single-line, and don't contain certain patterns
    lines = text.strip().split('\n')
    if len(lines) > 3:
        return False  # Output is usually multi-line
    
    # Check for common command patterns
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\s+[^\s]+)*$', text.strip()):
        return True
    
    return False


def split_commands_and_output(lines: List[str]) -> List[Tuple[Optional[str], str]]:
    """
    Split terminal output into commands and their outputs.
    
    Args:
        lines: List of terminal output lines
        
    Returns:
        List of (command, output) tuples. command is None for pure output.
    """
    # Join lines for better pattern matching
    full_text = '\n'.join(lines)
    
    result = []
    last_pos = 0
    
    # Find all prompts in the text
    prompts = []
    for pattern in PROMPT_PATTERNS:
        for match in re.finditer(pattern, full_text):
            prompts.append((match.start(), match.group(0)))
    
    # Sort by position
    prompts.sort(key=lambda x: x[0])
    
    for i, (pos, prompt) in enumerate(prompts):
        # Get text between last prompt and current prompt
        if pos > last_pos:
            segment = full_text[last_pos:pos].strip()
            if segment:
                # This is output from previous command
                if result:
                    prev_cmd, prev_out = result[-1]
                    result[-1] = (prev_cmd, (prev_out + '\n' + segment).strip())
                else:
                    result.append((None, segment))
        
        # Extract command after prompt
        cmd_start = pos + len(prompt)
        # Find end of command (next newline or next prompt)
        next_prompt_pos = prompts[i+1][0] if i+1 < len(prompts) else len(full_text)
        cmd_end = full_text.find('\n', cmd_start)
        if cmd_end == -1 or cmd_end > next_prompt_pos:
            cmd_end = next_prompt_pos
        
        command = full_text[cmd_start:cmd_end].strip()
        
        # Skip if command is empty or just whitespace
        if command and not command.isspace():
            result.append((command, ''))
        
        last_pos = cmd_end
    
    # Handle remaining text after last prompt
    if last_pos < len(full_text):
        segment = full_text[last_pos:].strip()
        if segment:
            if result:
                prev_cmd, prev_out = result[-1]
                result[-1] = (prev_cmd, (prev_out + '\n' + segment).strip())
            else:
                result.append((None, segment))
    
    # Clean up results - remove empty commands
    cleaned = []
    for cmd, out in result:
        if cmd or out:
            cleaned.append((cmd if cmd else None, out))
    
    return cleaned

