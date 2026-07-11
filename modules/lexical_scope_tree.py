from modules.symbol_table import SymbolTable

class LexicalScopeTree():
    def __init__(self):
        self.tree = []
    
    def insert(self, entry: tuple(SymbolTable, start_line, end_line)):
        self.tree.append(entry)