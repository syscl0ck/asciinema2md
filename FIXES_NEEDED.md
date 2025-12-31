# Issues Found and Fixes Needed

## Major Issues Identified

1. **Missing Commands**: Only 2-3 commands detected instead of 10+
   - Commands like `cd`, `mv`, `mkdir`, `nmap`, `vim`, etc. are missing
   - Only the last few commands in the session are captured

2. **Wrong Command Detection**: 
   - "The following lines are desirable for IPv6 capable hosts" detected as command (it's a file comment)
   - "aasciinema2md" should be "apt install nuclei -y"

3. **Terminal Emulator Limitation**:
   - Only maintains current screen (28 lines)
   - Earlier commands are scrolled off and lost
   - Screen clears (`\u001b[2J`) wipe out history

4. **Command Tracking Issues**:
   - Character-by-character typing with backspaces is complex
   - Autocomplete suggestions interfere with tracking
   - Need to properly handle `\r\r\n` (Enter key)

## Root Cause

The asciinema format records terminal OUTPUT, not input. When content scrolls off screen or screen is cleared, that history is lost from the terminal's perspective. The terminal emulator can't recover scrolled content.

## Recommended Solution

1. **Event-Based Command Extraction**: Track commands in real-time as events are processed
   - Detect prompts
   - Track command buffer (handle backspaces)
   - Detect Enter key (`\r\r\n`)
   - Extract final command
   - Capture output until next prompt

2. **Look for Complete Command Strings**: Some commands appear as complete strings in events (e.g., "nmap -p -sV 10.10.11.99 -oA VersionScan" at line 307)

3. **Hybrid Approach**: 
   - Use complete command strings when available
   - Fall back to character-by-character tracking
   - Use terminal emulator for final state verification

## Next Steps

The current implementation works but has limitations. To fully fix:

1. Rewrite command tracking to be event-driven from the start
2. Properly handle backspaces and autocomplete
3. Maintain command history separately from terminal state
4. Match commands with outputs by timestamp/proximity

