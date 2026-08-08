from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .errors import AmbiguousCommand, IncompleteCommand, InvalidInput

Handler = Callable[[dict[str, object]], str]
Parser = Callable[[str], object]


@dataclass
class ArgumentNode:
    name: str
    description: str
    parser: Parser
    greedy: bool = False
    child: "CommandNode" = field(default_factory=lambda: CommandNode())


@dataclass
class CommandNode:
    literals: dict[str, tuple[str, "CommandNode"]] = field(default_factory=dict)
    arguments: list[ArgumentNode] = field(default_factory=list)
    handler: Handler | None = None

    def literal(self, keyword: str, description: str = "") -> "CommandNode":
        key = keyword.lower()
        if key not in self.literals:
            self.literals[key] = (description, CommandNode())
        return self.literals[key][1]

    def argument(self, name: str, description: str, parser: Parser, greedy: bool = False) -> "CommandNode":
        for argument in self.arguments:
            if argument.name == name:
                return argument.child
        argument = ArgumentNode(name, description, parser, greedy)
        self.arguments.append(argument)
        return argument.child


class CommandTree:
    def __init__(self) -> None:
        self.root = CommandNode()

    def add(self, parts: list[tuple], handler: Handler) -> None:
        node = self.root
        for part in parts:
            if part[0] == "literal":
                node = node.literal(part[1], part[2])
            else:
                node = node.argument(part[1], part[2], part[3], part[4])
        node.handler = handler

    @staticmethod
    def _literal_match(node: CommandNode, token: str) -> CommandNode | None:
        lowered = token.lower()
        if lowered in node.literals:
            return node.literals[lowered][1]
        matches = [child for key, (_, child) in node.literals.items() if key.startswith(lowered)]
        if len(matches) > 1:
            raise AmbiguousCommand
        return matches[0] if matches else None

    def execute(self, tokens: list[str]) -> str:
        node = self.root
        values: dict[str, object] = {}
        index = 0
        while index < len(tokens):
            token = tokens[index]
            literal = self._literal_match(node, token)
            if literal is not None:
                node = literal
                index += 1
                continue
            parsed = False
            for argument in node.arguments:
                try:
                    raw_value = " ".join(tokens[index:]) if argument.greedy else token
                    value = argument.parser(raw_value)
                except ValueError:
                    continue
                values[argument.name] = value
                node = argument.child
                parsed = True
                if argument.greedy:
                    index = len(tokens) - 1
                break
            if not parsed:
                raise InvalidInput
            index += 1
        if node.handler is None:
            raise IncompleteCommand
        return node.handler(values)

    def help(self, tokens: list[str], partial: str = "") -> str:
        node = self.root
        for token in tokens:
            literal = self._literal_match(node, token)
            if literal is not None:
                node = literal
                continue
            for argument in node.arguments:
                try:
                    argument.parser(token)
                except ValueError:
                    continue
                node = argument.child
                break
            else:
                raise InvalidInput

        rows: list[tuple[str, str]] = []
        lowered = partial.lower()
        for keyword, (description, _) in sorted(node.literals.items()):
            if keyword.startswith(lowered):
                rows.append((keyword, description))
        if not partial:
            rows.extend((f"<{a.name}>", a.description) for a in node.arguments)
            if node.handler is not None:
                rows.append(("<cr>", ""))
        if not rows:
            raise InvalidInput
        width = max(len(name) for name, _ in rows)
        return "\n".join(f"  {name:<{width}}  {description}".rstrip() for name, description in rows)

    def complete(self, tokens: list[str], partial: str) -> list[str]:
        node = self.root
        try:
            for token in tokens:
                literal = self._literal_match(node, token)
                if literal is None:
                    return []
                node = literal
        except AmbiguousCommand:
            return []
        lowered = partial.lower()
        return sorted(keyword for keyword in node.literals if keyword.startswith(lowered))


def literal(keyword: str, description: str = "") -> tuple:
    return ("literal", keyword, description)


def argument(name: str, description: str, parser: Parser, *, greedy: bool = False) -> tuple:
    return ("argument", name, description, parser, greedy)
