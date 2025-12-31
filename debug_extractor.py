#!/usr/bin/env python3
"""Debug command extractor."""

from asciinema2md.parser import parse_cast_file
from asciinema2md.command_extractor import CommandExtractor

metadata, events = parse_cast_file('session.cast')
extractor = CommandExtractor()

# Process first 100 events to see what's happening
for i, (timestamp, event_type, text) in enumerate(events[:100]):
    if event_type == 'o':
        clean = text.replace('\x1b', 'ESC').replace('\r', '\\r').replace('\n', '\\n')
        if len(clean) < 100:
            print(f"{i}: {clean[:80]}")
        
        # Check for prompt
        if extractor.prompt_pattern.search(text):
            print(f"  -> PROMPT DETECTED at event {i}")
        
        extractor.process_events([(timestamp, event_type, text)])

print(f"\nCommands found: {len(extractor.commands)}")
for cmd, output, ts in extractor.commands:
    print(f"  - {cmd[:50]}")

