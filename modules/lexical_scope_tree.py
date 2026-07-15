from modules.symbol_table import SymbolTable

class LexicalScopeTree():
    def __init__(self) -> None:
        self.tree: list[tuple[SymbolTable, int, int]] = []

    def insert(self, entry: tuple[SymbolTable, int, int]) -> None:
        self.tree.append(entry)