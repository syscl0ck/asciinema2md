"""Parse asciinema cast files."""

import json
from typing import Dict, List, Tuple, Optional


def parse_cast_file(filepath: str) -> Tuple[Dict, List[Tuple[float, str, str]]]:
    """
    Parse an asciinema cast file.
    
    Args:
        filepath: Path to the .cast file
        
    Returns:
        Tuple of (metadata_dict, events_list)
        Events are tuples of (timestamp, event_type, text)
    """
    metadata = {}
    events = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        # First line is metadata
        first_line = f.readline().strip()
        if first_line:
            metadata = json.loads(first_line)
        
        # Remaining lines are events
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                event = json.loads(line)
                if len(event) >= 3:
                    timestamp = event[0]
                    event_type = event[1]
                    text = event[2]
                    events.append((timestamp, event_type, text))
            except json.JSONDecodeError:
                # Skip malformed lines
                continue
    
    return metadata, events

