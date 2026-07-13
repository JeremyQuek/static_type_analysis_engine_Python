
import ast
from copy import deepcopy
from collections import defaultdict

from modules.scopes import Scope
from modules.type_lattice import Unassigned, join

class SymbolTableEntry():
    def __init__(self, _type, line):
        self.type = _type
        self.line = line

class SymbolTable():
    def __init__(self):
        self.table= {
            Scope.BUILTIN: defaultdict(list),
            Scope.GLOBAL: defaultdict(list),
            Scope.ENCLOSING: [], # list of dicts, in prepend order
            Scope.LOCAL: defaultdict(list)
        }

    def insert(self, _id, _type, line, scope):
        self.table[scope][_id].append(SymbolTableEntry(_type, line))

    def fork_for_branch(self) -> SymbolTable:
        child = SymbolTable()
        child.table = deepcopy(self.table)
        return child
    

    def fork_for_function(self, parameters_list: list[tuple[str, type, int]]) -> SymbolTable:
        # Fork and change scopes
        child = SymbolTable()
        child.table[Scope.GLOBAL] = deepcopy(self.table[Scope.GLOBAL])
        child.table[Scope.ENCLOSING] = deepcopy(self.table[Scope.ENCLOSING])

        parent_enclosure= defaultdict(list)
        for _id, sub_table in self.table[Scope.LOCAL].items():
            for entry in sub_table:
                parent_enclosure[_id].append(SymbolTableEntry(entry.type, entry.line))
        
        child.table[Scope.ENCLOSING].append(parent_enclosure)

        # insert params
        for arg__id, arg_type, arg_line in parameters_list:
            child.insert(arg__id, arg_type, arg_line, Scope.LOCAL)
        
        return child

    def merge_branch(self, merge_line, scope, *branches, parent_branch=True):
        # Snapshot: how many entries each _id has in this scope before branching.
        parent_lengths = {
            _id: len(entries)
            for _id, entries in self.table[scope].items()
        }

        # Only consider _ids modified in at least one branch.
        touched = set()
        for branch in branches:
            for _id, entries in branch.table[scope].items():
                pre = parent_lengths.get(_id, 0)
                if len(entries) > pre:
                    touched.add(_id)

        # Merge the resulting types back into the parent table.
        for _id in touched:
            pre = parent_lengths.get(_id, 0)
            branch_types = []

            for branch in branches:
                entries = branch.table[scope].get(_id)

                if entries and len(entries) > pre:
                    branch_types.append(entries[-1].type)
                else:
                    parent_entries = self.table[scope].get(_id)
                    branch_types.append(
                        parent_entries[-1].type if parent_entries else Unassigned()
                    )

            if _id not in self.table[scope] or not parent_branch:
                self.insert(_id, Unassigned(), 0, scope)
                merged_type = Unassigned()
            else:
                merged_type = self.table[scope][_id][-1].type

            for _type in branch_types:
                merged_type = join(merged_type, _type)

            self.insert(_id, merged_type, merge_line, scope)

    def merge_function_def(self, nested_function_symbol_tables):
        pass
    

    def __str__(self):
        lines = ["SymbolTable"]

        for scope in Scope:
            lines.append(f"\n[{scope.name}]")

            scope_table = self.table.get(scope, {})
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


