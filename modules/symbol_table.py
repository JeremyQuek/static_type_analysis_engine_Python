
from __future__ import annotations
import ast
import builtins
from copy import deepcopy
from collections import defaultdict
from uuid import UUID

from modules.scopes import Scope, BUILTIN, GLOBAL, ENCLOSING, LOCAL
from modules.type_lattice import Unassigned, join

class SymbolTableEntry():
    def __init__(self, _type: type, line: int, artifact=None) -> None:
        self.type = _type
        self.line = line
        self.artifact = artifact

class SymbolTable():
    def __init__(self) -> None:
        self.sections= {
            BUILTIN: defaultdict(list),
            GLOBAL: defaultdict(list),

            # ENCLOSING is meant to entirely be a function definition side effect save copy of previous locals for best-effort
            # definition body analysis. It is not used outside of that, when the enclosure environment is stored into FunctionMetadata
            # which is used for call site
            ENCLOSING: [],  # list[tuple[UUID, defaultdict[str, list]]] 

            LOCAL: defaultdict(list)
        }

        for name in dir(builtins):
            obj = getattr(builtins, name)
            _type =  type(obj)
            self.insert(name, _type, 0, BUILTIN)

    def insert(self, symbol: str, _type: type, line: int, scope: Scope, **kwargs) -> None:
        self.sections[scope][symbol].append(SymbolTableEntry(_type, line, **kwargs))

    # This is for function definitons, where we modify the enclosure scope of the local table
    def insert_free_variable(self, symbol: str, _type: type, line: int, namespace_id: UUID, **kwargs) -> None:
        for (_ns_id, enclosing_dict) in self.sections[ENCLOSING]:
            if _ns_id == namespace_id:
                enclosing_dict[symbol].append(SymbolTableEntry(_type, line, **kwargs))
                return

    def fork(self) -> SymbolTable:
        child = SymbolTable()
        child.sections = deepcopy(self.sections)
        return child

    def fork_for_branch(self) -> SymbolTable:
        return self.fork()

    def fork_for_function_def(self, parameters_list: list[tuple[str, type, int]], parent_namespace_id: UUID) -> SymbolTable:
        # Fork and change scopes
        child = SymbolTable()
        child.sections[GLOBAL] = deepcopy(self.sections[GLOBAL])

        # Deepcopy the enclosing environment so that assingments don't mutate the external env
        child.sections[ENCLOSING] = deepcopy(self.sections[ENCLOSING])
        parent_enclosure= defaultdict(list)
        for symbol, sub_table in self.sections[LOCAL].items():
            for entry in sub_table:
                parent_enclosure[symbol].append(SymbolTableEntry(entry.type, entry.line))
        
        child.sections[ENCLOSING].append((parent_namespace_id, parent_enclosure))

        # insert params
        for arg__id, arg_type, arg_line in parameters_list:
            child.insert(arg__id, arg_type, arg_line, LOCAL)
        
        return child

    def merge_branch(self, merge_line: int, scope: Scope, *branches: SymbolTable, parent_branch: bool = True) -> None:
        parent_lengths = {
            symbol: len(entries)
            for symbol, entries in self.sections[scope].items()
        }

        touched = set()
        for branch in branches:
            for symbol, entries in branch.sections[scope].items():
                pre = parent_lengths.get(symbol, 0)
                if len(entries) > pre:
                    touched.add(symbol)

        for symbol in touched:
            pre = parent_lengths.get(symbol, 0)
            branch_types = []

            for branch in branches:
                entries = branch.sections[scope].get(symbol)

                if entries and len(entries) > pre:
                    branch_types.append(entries[-1].type)
                else:
                    parent_entries = self.sections[scope].get(symbol)
                    branch_types.append(
                        parent_entries[-1].type if parent_entries else Unassigned()
                    )

            if symbol not in self.sections[scope] or not parent_branch:
                if symbol not in self.sections[scope]:
                    self.insert(symbol, Unassigned(), 0, scope)
                merged_type = Unassigned()
            else:
                merged_type = self.sections[scope][symbol][-1].type

            for _type in branch_types:
                merged_type = join(merged_type, _type)

            self.insert(symbol, merged_type, merge_line, scope)

    
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

            scope_table = self.sections.get(scope, {})
            if not scope_table:
                lines.append("  (empty)")
                continue

            for symbol in scope_table:
                lines.append(f"  [{symbol}]")

                for entry in scope_table[symbol]:
                    type_name = getattr(entry.type, "__name__", str(entry.type))
                    lines.append(
                        f"    line {entry.line:>4}  {type_name:<20}"
                    )

        return "\n".join(lines)


