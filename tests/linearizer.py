from modules.symbol_table import SymbolTable
from modules.lexical_scope_tree import LexicalScopeTree
from modules.scopes import Scope


class LinearEntry:
    def __init__(self, identifier, _type, line, scope):
        self.identifier = identifier
        self.type = _type
        self.line = line
        self.scope = scope

    def __repr__(self):
        type_name = getattr(self.type, "__name__", str(self.type))
        return f"{self.identifier}: {type_name}, line {self.line}"

# TODO:
# Since we changed the function definition to directly update global/nonlocal
# The nested version having the ground truth model might no longer be relevant...possibly
# Need to rethink

class Linearizer:
    def __init__(self, program_table_tree: LexicalScopeTree):
        self.entries = self._flatten_tree(program_table_tree)

    # Tree is ordered innermost-first, so the first (identifier, line) we encounter
    # is the most nested/truthful entry; parent merge duplicates get skipped by dedup.
    def _flatten_tree(self, tree: LexicalScopeTree) -> list[LinearEntry]:
        seen = set()
        result = []
        for symbol_table, start_line, end_line in tree.tree:
            for scope, scope_dict in symbol_table.tables.items():
                if scope in (Scope.ENCLOSING, Scope.BUILTIN):
                    continue
                for identifier, entries in scope_dict.items():
                    for e in entries:
                        key = (identifier, e.line)
                        if key not in seen:
                            seen.add(key)
                            result.append(LinearEntry(identifier, e.type, e.line, scope))
        result.sort(key=lambda entry: entry.line)
        return result

    def as_list(self) -> list[tuple[str, str, int, str]]:
        return [
            (e.identifier, getattr(e.type, "__name__", str(e.type)), e.line, e.scope.value)
            for e in self.entries
        ]

    def print(self):
        if not self.entries:
            print("(empty)")
            return

        id_w = max(len(e.identifier) for e in self.entries)
        type_w = max(len(getattr(e.type, "__name__", str(e.type))) for e in self.entries)
        scope_w = max(len(e.scope.value) for e in self.entries)

        print(f"{'var':<{id_w}}  {'type':<{type_w}}  {'line':<6}{'scope'}")
        print(f"{'-' * id_w}  {'-' * type_w}  {'----':<6}{'-' * scope_w}")

        for e in self.entries:
            type_name = getattr(e.type, "__name__", str(e.type))
            print(f"{e.identifier:<{id_w}}  {type_name:<{type_w}}  {e.line:<6}{e.scope.value}")
