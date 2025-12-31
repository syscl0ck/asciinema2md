"""ANSI escape code handling."""

import re


def strip_ansi(text):
    """
    Strip all ANSI escape sequences from text.
    
    Args:
        text: String containing ANSI escape codes
        
    Returns:
        String with all ANSI codes removed
    """
    # Pattern matches:
    # - ESC[ followed by parameters and a command letter
    # - ESC] (OSC sequences)
    # - ESC followed by other control sequences
    # - Common control characters like \r, \b (we'll handle these separately)
    
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[=<>]')
    text = ansi_escape.sub('', text)
    
    # Remove other control characters that are formatting-related
    # Keep \n, \r, \t as they're meaningful
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    return text


def clean_text(text):
    """
    Clean text by stripping ANSI codes and normalizing whitespace.
    
    Args:
        text: String to clean
        
    Returns:
        Cleaned string
    """
    text = strip_ansi(text)
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text

