#!/usr/bin/env python3
"""Debug script to see what terminal output looks like."""

from asciinema2md.parser import parse_cast_file
from asciinema2md.terminal import Terminal
from asciinema2md.ansi import strip_ansi

metadata, events = parse_cast_file('session.cast')
width = metadata.get('width', 80)
height = metadata.get('height', 24)

terminal = Terminal(width=width, height=height)

for timestamp, event_type, text in events:
    if event_type == 'o':
        terminal.process_text(text)

output = terminal.get_output()
output = strip_ansi(output)

# Write to file
with open('debug_output.txt', 'w', encoding='utf-8') as f:
    f.write(output)

print(f"Output written to debug_output.txt ({len(output)} chars, {len(output.split(chr(10)))} lines)")

