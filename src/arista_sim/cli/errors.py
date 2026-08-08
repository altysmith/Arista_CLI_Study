class CliError(Exception):
    message = "% Invalid input"


class InvalidInput(CliError):
    message = "% Invalid input"


class AmbiguousCommand(CliError):
    message = "% Ambiguous command"


class IncompleteCommand(CliError):
    message = "% Incomplete command"

