
from copy import deepcopy
from collections import defaultdict
from modules.type_lattice import Unassigned, join

class SymbolTableEntry():
    def __init__(self, line, _type, scope):
        self.line = line
        self.type = _type
        self.scope = scope


class SymbolTable():
    def __init__(self):
        self.table= defaultdict(list)

    def insert(self, identifier, _type, line, scope):
        self.table[identifier].append(SymbolTableEntry(line, _type, scope))

    def fork_for_branch(self):
        child = SymbolTable()
        child.table = deepcopy(self.table)
        return child
    
    def fork_for_function(self):
        child = SymbolTable()
        child.table = deepcopy(self.table)
        return child

    def merge_branch(self, merge_line, scope, *branches, parent_branch=True):
        # Snapshot the symbol table state before branching.
        parent_lengths = {
            identifier: len(entries)
            for identifier, entries in self.table.items()
        }

        # Only consider identifiers modified in at least one branch.
        touched = set()
        for branch in branches:
            for identifier, entries in branch.table.items():
                pre = parent_lengths.get(identifier, 0)
                if len(entries) > pre:
                    touched.add(identifier)

        # Merge the resulting types back into the parent table.
        for identifier in touched:
            pre = parent_lengths.get(identifier, 0)
            branch_types = []

            for branch in branches:
                entries = branch.table.get(identifier)

                if entries and len(entries) > pre:
                    # Identifier was reassigned in this branch.
                    branch_types.append(entries[-1].type)
                else:
                    # Identifier was not reassigned; inherit the parent's type.
                    parent_entries = self.table.get(identifier)
                    branch_types.append(
                        parent_entries[-1].type if parent_entries else Unassigned()
                    )

            if identifier not in self.table or not parent_branch:
                merged_type = Unassigned() 
            else:
                merged_type= self.table[identifier][-1].type
                
            for _type in branch_types:
                merged_type = join(merged_type, _type)

            self.insert(identifier, merged_type, merge_line,scope)

    def merge_function(self, nested_function_symbol_tables):
        pass
    

    def __str__(self):
        if not self.table:
            return "SymbolTable (empty)"
        lines = ["SymbolTable"]
        for identifier, entries in self.table.items():
            lines.append(f"  [{identifier}]")
            for e in entries:
                type_name = getattr(e.type, "__name__", str(e.type))
                lines.append(f"    line {e.line:>4}  {type_name:<20}  scope={e.scope}")
        return "\n".join(lines)

    def __contains__(self, identifier):
        return identifier in self.table

    def __getitem__(self, identifier):
        return self.table[identifier]

