
from __future__ import annotations
import ast
from copy import deepcopy
from collections import defaultdict
from uuid import UUID

from modules.scopes import Scope
from modules.type_lattice import Unassigned, join

class SymbolTableEntry():
    def __init__(self, _type: type, line: int, artifact=None) -> None:
        self.type = _type
        self.line = line
        self.artifact = artifact

class SymbolTable():
    def __init__(self) -> None:
        self.tables= {
            Scope.BUILTIN: defaultdict(list),
            Scope.GLOBAL: defaultdict(list),

            # Scope.ENCLOSING is meant to entirely be a function definition side effect save copy of previous locals for best-effort
            # definition body analysis. It is not used outside of that, when the enclosure environment is stored into FunctionArtifact
            # which is used for call site
            Scope.ENCLOSING: [],  # list[tuple[UUID, defaultdict[str, list]]] 
            
            Scope.LOCAL: defaultdict(list)
        }

    def insert(self, _id: str, _type: type, line: int, scope: Scope, **kwargs) -> None:
        self.tables[scope][_id].append(SymbolTableEntry(_type, line, **kwargs))

    def fork(self) -> SymbolTable:
        child = SymbolTable()
        child.tables = deepcopy(self.tables)
        return child

    def fork_for_branch(self) -> SymbolTable:
        return self.fork()

    def fork_for_function_def(self, parameters_list: list[tuple[str, type, int]], parent_namespace_id: UUID) -> SymbolTable:
        # Fork and change scopes
        child = SymbolTable()
        child.tables[Scope.GLOBAL] = deepcopy(self.tables[Scope.GLOBAL])

        # Deepcopy the enclosing environment so that assingments don't mutate the external env
        child.tables[Scope.ENCLOSING] = deepcopy(self.tables[Scope.ENCLOSING])
        parent_enclosure= defaultdict(list)
        for _id, sub_table in self.tables[Scope.LOCAL].items():
            for entry in sub_table:
                parent_enclosure[_id].append(SymbolTableEntry(entry.type, entry.line))
        
        child.tables[Scope.ENCLOSING].append((parent_namespace_id, parent_enclosure))

        # insert params
        for arg__id, arg_type, arg_line in parameters_list:
            child.insert(arg__id, arg_type, arg_line, Scope.LOCAL)
        
        return child

    def merge_branch(self, merge_line: int, scope: Scope, *branches: SymbolTable, parent_branch: bool = True) -> None:
        # Snapshot: how many entries each _id has in this scope before branching.
        parent_lengths = {
            _id: len(entries)
            for _id, entries in self.tables[scope].items()
        }

        # Only consider _ids modified in at least one branch.
        touched = set()
        for branch in branches:
            for _id, entries in branch.tables[scope].items():
                pre = parent_lengths.get(_id, 0)
                if len(entries) > pre:
                    touched.add(_id)

        # Merge the resulting types back into the parent table.
        for _id in touched:
            pre = parent_lengths.get(_id, 0)
            branch_types = []

            for branch in branches:
                entries = branch.tables[scope].get(_id)

                if entries and len(entries) > pre:
                    branch_types.append(entries[-1].type)
                else:
                    parent_entries = self.tables[scope].get(_id)
                    branch_types.append(
                        parent_entries[-1].type if parent_entries else Unassigned()
                    )

            if _id not in self.tables[scope] or not parent_branch:
                if _id not in self.tables[scope]:
                    self.insert(_id, Unassigned(), 0, scope)
                merged_type = Unassigned()
            else:
                merged_type = self.tables[scope][_id][-1].type

            for _type in branch_types:
                merged_type = join(merged_type, _type)

            self.insert(_id, merged_type, merge_line, scope)

    
    # HARD TODO
    """
    Function definitions and function calls must be handled separately.

    Example:
        def a():
            x = 5

            def b():
                nonlocal x
                x = str

            inspect_type(x)   # x is still int

    Although `b` mutates `x`, the function has only been defined, not executed.
    Side effects on enclosing or global scopes should only be propagated after
    an actual function call, not after encountering a FunctionDef.

    Additionally, the current ENCLOSING list uses positional indexes (0 = immediate
    parent, 1 = grandparent, etc). This works for LEGB lookup going down the call
    chain, but breaks when merging side effects back up — the caller has a different
    stack shape so indexes don't map. Need to switch to stable scope IDs (e.g. keyed
    by function AST node id) so mutations can target a specific frame regardless of
    where we are in the call stack.
    """

    def __str__(self) -> str:
        lines = ["SymbolTable"]

        for scope in Scope:
            lines.append(f"\n[{scope.name}]")

            scope_table = self.tables.get(scope, {})
            if not scope_table:
                lines.append("  (empty)")
                continue

            for _id in scope_table:
                lines.append(f"  [{_id}]")

                for entry in scope_table[_id]:
                    type_name = getattr(entry.type, "__name__", str(entry.type))
                    lines.append(
                        f"    line {entry.line:>4}  {type_name:<20}"
                    )

        return "\n".join(lines)


