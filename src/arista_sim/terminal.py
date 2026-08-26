from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Callable, TextIO

if TYPE_CHECKING:
    from .cli.session import Session


def read_command(session: "Session") -> str:
    """Read a command with platform-appropriate interactive line editing."""
    if not sys.stdin.isatty():
        return input(f"{session.prompt} ")

    if os.name != "nt":
        _enable_readline()
        return input(f"{session.prompt} ")

    import msvcrt

    return _read_windows_command(session, msvcrt.getwch, sys.stdout)


def _enable_readline() -> bool:
    """Enable ANSI-terminal editing and history when readline is available."""
    try:
        import readline  # noqa: F401
    except ImportError:
        return False
    return True


def _read_windows_command(
    session: "Session", getwch: Callable[[], str], output: TextIO
) -> str:
    prompt = f"{session.prompt} "
    buffer = ""
    history_index = len(session.history)
    draft = ""
    output.write(prompt)
    output.flush()

    def redraw(replacement: str) -> str:
        nonlocal buffer
        old_length = len(buffer)
        buffer = replacement
        output.write("\r" + prompt + buffer)
        if old_length > len(buffer):
            output.write(" " * (old_length - len(buffer)))
            output.write("\b" * (old_length - len(buffer)))
        output.flush()
        return buffer

    while True:
        char = getwch()
        if char in ("\r", "\n"):
            output.write("\n")
            output.flush()
            return buffer
        if char == "\x03":
            raise KeyboardInterrupt
        if char == "\x1a":
            raise EOFError
        if char == "\b":
            if buffer:
                buffer = buffer[:-1]
                output.write("\b \b")
                output.flush()
            continue
        if char == "?":
            help_output = session.help(buffer + "?")
            output.write("?\n" + help_output + "\n" + prompt + buffer)
            output.flush()
            continue
        if char == "\t":
            completed, matches = session.complete(buffer)
            if completed != buffer:
                suffix = completed[len(buffer) :]
                buffer = completed
                output.write(suffix)
            elif len(matches) > 1:
                output.write("\n  " + "  ".join(matches) + "\n" + prompt + buffer)
            output.flush()
            continue
        if char in ("\x00", "\xe0"):
            scan_code = getwch()
            if scan_code == "H" and session.history:
                if history_index == len(session.history):
                    draft = buffer
                if history_index > 0:
                    history_index -= 1
                    redraw(session.history[history_index])
            elif scan_code == "P" and history_index < len(session.history):
                history_index += 1
                redraw(draft if history_index == len(session.history) else session.history[history_index])
            continue
        if char.isprintable():
            buffer += char
            output.write(char)
            output.flush()
