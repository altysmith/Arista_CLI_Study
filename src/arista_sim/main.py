from __future__ import annotations

import sys

from .cli.session import Session
from .terminal import read_command


def main() -> None:
    session = Session()
    print("Arista Network Foundations Simulator - Milestone 1")
    print("Type ? for contextual help. Type exit to leave.")
    while not session.closed:
        try:
            line = read_command(session)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        output = session.execute(line)
        if output:
            print(output)


if __name__ == "__main__":
    main()
