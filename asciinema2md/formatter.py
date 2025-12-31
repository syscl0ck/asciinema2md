"""Format terminal session as Markdown."""

from typing import List, Tuple, Optional


def format_as_markdown(commands_and_output: List[Tuple[Optional[str], str]], 
                      metadata: dict = None) -> str:
    """
    Format commands and output as Markdown.
    
    Args:
        commands_and_output: List of (command, output) tuples
        metadata: Optional metadata dict from cast file
        
    Returns:
        Markdown formatted string
    """
    lines = []
    
    # Add header
    lines.append("# Terminal Session")
    lines.append("")
    
    if metadata:
        # Add metadata as a note
        lines.append("<!--")
        lines.append(f"Recorded: {metadata.get('timestamp', 'unknown')}")
        lines.append(f"Terminal: {metadata.get('width', '?')}x{metadata.get('height', '?')}")
        if 'env' in metadata:
            lines.append(f"Shell: {metadata['env'].get('SHELL', 'unknown')}")
        lines.append("-->")
        lines.append("")
    
    # Format each command/output pair
    for i, (command, output) in enumerate(commands_and_output):
        if command:
            # This is a command
            lines.append(f"## Command: {command}")
            lines.append("")
            lines.append("```bash")
            lines.append(command)
            lines.append("```")
            lines.append("")
            
            if output:
                lines.append("### Output")
                lines.append("")
                # Output in code block
                lines.append("```")
                lines.append(output)
                lines.append("```")
                lines.append("")
        else:
            # Pure output (no command)
            if output:
                lines.append("## Output")
                lines.append("")
                lines.append("```")
                lines.append(output)
                lines.append("```")
                lines.append("")
    
    return '\n'.join(lines)

