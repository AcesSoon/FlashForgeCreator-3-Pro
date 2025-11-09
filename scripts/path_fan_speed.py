#!/usr/bin/env python3
"""
Minimal PrusaSlicer post-processing script.

Behavior:
- When it sees 'M108 Tn', it remembers tool n.
- It adds/replaces ' Tn' on subsequent 'M106' lines that have an S value until another M108 Tm appears.
- On tool change, if a last fan speed Sx is known, it inserts 'M106 Sx Tn' to continue the fan on the new tool.
- Everything else is left unchanged. Newlines and comments are preserved.

Invocation (works with PrusaSlicer):
    path_fan_speed.py INPUT_GCODE [OUTPUT_GCODE]
If OUTPUT_GCODE is omitted, the INPUT_GCODE is modified in place.
"""

import sys
import os
import re
from pathlib import Path


def process_lines(lines):
    tool_re = re.compile(r"^\s*M108\s+T(\d+)\b", re.IGNORECASE)
    # No tool until we see an explicit M108 Tn marker.
    current_tool = None
    out = []
    last_fan_speed = None  # remember numeric string like '38.25'

    for line in lines:
        # Preserve original newline style per line
        if line.endswith("\r\n"):
            eol = "\r\n"
            stripped = line[:-2]
        elif line.endswith("\n"):
            eol = "\n"
            stripped = line[:-1]
        else:
            eol = "\n"
            stripped = line

        # Track M108 Tn (tool marker)
        m_tool = tool_re.match(stripped)
        if m_tool:
            current_tool = m_tool.group(1)
            out.append(stripped + eol)
            # Immediately continue fan speed for new tool if we have a last value
            if last_fan_speed is not None:
                out.append(f"M106 S{last_fan_speed} T{current_tool}" + eol)
            continue

        # Rewrite M106 with Tn if available
        if stripped.lstrip().upper().startswith("M106") and current_tool is not None:
            # Split off inline comment
            parts = stripped.split(";", 1)
            code = parts[0]
            comment_suffix = (";" + parts[1]) if len(parts) == 2 else ""

            # Only modify if an S parameter is present on this M106 line
            s_match = re.search(r"(?i)\bS(-?\d+(?:\.\d+)?)\b", code)
            if s_match:
                last_fan_speed = s_match.group(1)
                # Remove any existing T parameter but keep S and other params untouched
                code_no_t = re.sub(r"(?i)\s*T\d+\b", "", code)
                new_code = code_no_t.rstrip() + f" T{current_tool}"
                new_line = new_code + (" " if comment_suffix and not new_code.endswith(" ") else "") + comment_suffix
                out.append(new_line + eol)
                continue

        # Default: pass through unchanged
        out.append(stripped + eol)

    return out


def main():
    if len(sys.argv) < 2:
        print("Usage: path_fan_speed.py INPUT_GCODE [OUTPUT_GCODE]", file=sys.stderr)
        sys.exit(2)

    inp = Path(sys.argv[1])
    if not inp.exists():
        print(f"Input file not found: {inp}", file=sys.stderr)
        sys.exit(1)

    text = inp.read_text(encoding="utf-8", errors="ignore")
    out_lines = process_lines(text.splitlines(True))

    if len(sys.argv) >= 3:
        Path(sys.argv[2]).write_text("".join(out_lines), encoding="utf-8")
    else:
        inp.write_text("".join(out_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
