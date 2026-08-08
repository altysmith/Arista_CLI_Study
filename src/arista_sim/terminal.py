from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cli.session import Session


def read_command(session: "Session") -> str:
    """Read a command, providing basic Tab completion on a Windows console."""
    if os.name != "nt" or not sys.stdin.isatty():
        return input(f"{session.prompt} ")

    import msvcrt

    prompt = f"{session.prompt} "
    buffer = ""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    while True:
        char = msvcrt.getwch()
        if char in ("\r", "\n"):
            print()
            return buffer
        if char == "\x03":
            raise KeyboardInterrupt
        if char == "\x1a":
            raise EOFError
        if char == "\b":
            if buffer:
                buffer = buffer[:-1]
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue
        if char == "\t":
            completed, matches = session.complete(buffer)
            if completed != buffer:
                suffix = completed[len(buffer) :]
                buffer = completed
                sys.stdout.write(suffix)
            elif len(matches) > 1:
                sys.stdout.write("\n  " + "  ".join(matches) + "\n" + prompt + buffer)
            sys.stdout.flush()
            continue
        if char in ("\x00", "\xe0"):
            msvcrt.getwch()  # Consume unsupported extended-key scan code.
            continue
        if char.isprintable():
            buffer += char
            sys.stdout.write(char)
            sys.stdout.flush()

