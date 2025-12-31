# asciinema2md

Convert asciinema cast files to Markdown format for documentation purposes.

## Installation

```bash
# Install from source
python setup.py install

# Or use directly
python asciinema2md.py session.cast -o report.md
```

## Usage

```bash
# Record a session
asciinema rec session.cast
# do your thing
# Press Ctrl+D or type 'exit' to stop recording

# Convert to Markdown
asciinema2md session.cast > report.md

# Or specify output file
asciinema2md session.cast -o report.md

# Keep ANSI color codes (default: strip them)
asciinema2md session.cast --keep-colors -o report.md
```

## Features

- Parses asciinema cast files (version 2 format)
- Strips ANSI escape codes for clean output
- Detects commands and separates them from output
- Formats output as Markdown with code blocks
- Handles terminal cursor movements and editing

## Requirements

- Python 3.7+
- No external dependencies (uses standard library only)

## Notes

The original asciinema tool is from https://asciinema.org, not my creation. 