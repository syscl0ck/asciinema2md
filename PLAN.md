# asciinema2md Implementation Plan

## Project Overview
Convert asciinema cast files (terminal recordings) to Markdown format for documentation purposes.

## Technical Approach

### 1. Technology Stack
- **Language**: Python 3.7+ (widely available on Linux)
- **Key Libraries**:
  - `json` (standard library) - Parse cast file format
  - `re` (standard library) - ANSI escape code handling
  - `argparse` (standard library) - CLI interface
  - `ansi2html` or custom ANSI parser - Handle terminal colors/formatting

### 2. Asciinema Format Analysis
The cast file format consists of:
- **Line 1**: JSON metadata object with `version`, `width`, `height`, `timestamp`, `env`
- **Subsequent lines**: JSON arrays `[timestamp, "o"/"i", "text"]`
  - `"o"` = output (terminal output)
  - `"i"` = input (user input, though rare in recordings)
  - Text contains ANSI escape codes for colors, cursor movements, etc.

### 3. Core Components

#### 3.1 Cast File Parser (`parser.py`)
- Read and parse JSON lines from cast file
- Extract metadata
- Parse event arrays into structured format
- Handle malformed JSON gracefully

#### 3.2 ANSI Code Handler (`ansi.py`)
- Strip or convert ANSI escape sequences:
  - Color codes (`\u001b[31m`, `\u001b[0m`, etc.)
  - Cursor movements (`\u001b[A`, `\u001b[K`, `\r`, etc.)
  - Terminal control sequences
- Options:
  - Strip all ANSI (simplest)
  - Convert to HTML/Markdown formatting
  - Preserve some formatting (bold, colors)

#### 3.3 Terminal State Emulator (`terminal.py`)
- Maintain virtual terminal state:
  - Current cursor position
  - Screen buffer
  - Current line being edited
- Process events chronologically:
  - Handle cursor movements (`\r`, `\n`, `\u001b[A`, etc.)
  - Handle text insertion/deletion
  - Handle line clearing (`\u001b[K`)
- Reconstruct final terminal output

#### 3.4 Command/Output Detector (`detector.py`)
- Identify command prompts (e.g., `$ `, `# `, custom prompts)
- Detect command execution (newline after prompt)
- Separate commands from their output
- Handle edge cases:
  - Multi-line commands
  - Interactive programs (vim, less, etc.)
  - Prompt changes during session

#### 3.5 Markdown Formatter (`formatter.py`)
- Format terminal session as Markdown:
  - Commands in code blocks with language hint
  - Output in code blocks or plain text
  - Preserve structure and readability
- Options:
  - Include timestamps
  - Include prompt information
  - Collapse/expand sections

#### 3.6 Main CLI (`asciinema2md.py`)
- Argument parsing:
  - Input file (required)
  - Output file (optional, default: stdout)
  - Options (strip colors, include timestamps, etc.)
- Error handling
- File I/O

### 4. Implementation Strategy

#### Phase 1: Basic Parser
1. Parse cast file format
2. Extract raw text (strip all ANSI for now)
3. Output simple Markdown

#### Phase 2: Terminal Emulation
1. Implement basic terminal state
2. Handle cursor movements
3. Reconstruct accurate output

#### Phase 3: Command Detection
1. Detect prompts
2. Separate commands from output
3. Format appropriately

#### Phase 4: Polish
1. Handle edge cases
2. Improve formatting
3. Add options
4. Error handling

### 5. Example Output Format

```markdown
# Terminal Session

## Command: cd Documents/htb
```bash
cd Documents/htb
```

## Command: nmap -p 445 --script "smb*" $TARGETIP -oA SMBDetailedScan
```bash
nmap -p 445 --script "smb*" $TARGETIP -oA SMBDetailedScan
```

### Output
```
Starting Nmap 7.95 ( https://nmap.org ) at 2025-12-30 17:56 CST
Error #486: Your port specifications are illegal...
```

## Command: nmap -p -sV 10.10.11.99 -oA VersionScan
```bash
nmap -p -sV 10.10.11.99 -oA VersionScan
```

### Output
```
Starting Nmap 7.95 ( https://nmap.org ) at 2025-12-30 17:56 CST
Nmap scan report for 10.10.11.99
Host is up (0.049s latency).
Not shown: 998 filtered tcp ports (no-response)
PORT     STATE SERVICE VERSION
80/tcp   open  http    Microsoft IIS httpd 10.0
5985/tcp open  http    Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
...
```
```

### 6. File Structure
```
asciinema2md/
├── asciinema2md/
│   ├── __init__.py
│   ├── parser.py          # Cast file parsing
│   ├── ansi.py            # ANSI code handling
│   ├── terminal.py        # Terminal emulation
│   ├── detector.py        # Command/output detection
│   └── formatter.py       # Markdown formatting
├── asciinema2md.py        # Main CLI entry point
├── requirements.txt       # Dependencies
├── setup.py              # Package setup
├── README.md             # Documentation
├── LICENSE               # License file
└── session.cast          # Test file
```

### 7. Testing Strategy
- Test with provided `session.cast` file
- Verify output format
- Test edge cases:
  - Empty cast files
  - Malformed JSON
  - Special characters
  - Long sessions
  - Interactive programs

### 8. Dependencies
- Python 3.7+
- No external dependencies initially (use standard library)
- Optional: `ansi2html` or similar for advanced ANSI handling

### 9. Future Enhancements
- Support for preserving colors in output
- HTML output option
- Interactive mode
- Filtering options (skip certain commands)
- Timestamp inclusion
- Custom prompt detection

## Next Steps
1. Set up project structure
2. Implement basic parser
3. Test with session.cast
4. Iterate and improve

