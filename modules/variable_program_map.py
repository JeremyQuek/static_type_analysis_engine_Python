import ast
from enum import Enum
from modules.type_lattice import Unassigned
from modules.symbol_table import SymbolTable
from modules.lexical_scope_tree import LexicalScopeTree

class Scope(Enum):
    GLOBAL = "G"
    BUILTIN = "B"
    ENCLOSING = "E"
    LOCAL = "L"

class VariableProgramMap():
    def __init__(self, file: str) -> None:
        self.file = file
        self.file_ast = self.build_file_ast(self.file)
        self.program_scope_tree = LexicalScopeTree()

    def trace(self) -> None:
        global_level_table = SymbolTable()
        self.analyze_code_block(self.file_ast.body, global_level_table, Scope.GLOBAL)
        self.symbol_table = global_level_table

    def analyze_code_block(self, code_block, symbol_table: SymbolTable, scope: Scope):
        start_line = code_block[0].lineno if code_block else 0
        end_line = code_block[-1].end_lineno if code_block else 0
        self.program_scope_tree.insert((symbol_table, start_line, end_line))

        for node in code_block:
            # Control flow
            if isinstance(node, ast.If):
                if_symbol_table = symbol_table.fork_for_branch()
                else_symbol_table = symbol_table.fork_for_branch()

                self.analyze_code_block(node.body, if_symbol_table, scope)
                self.analyze_code_block(node.orelse, else_symbol_table, scope)

                symbol_table.merge_branch(node.end_lineno, scope, if_symbol_table, else_symbol_table)

            # Assign statement 
            elif (isinstance(node, ast.AugAssign) or isinstance(node, ast.Assign)):
                event = None
                if isinstance(node, ast.Assign):
                    # Handles multi-assignment a,b=1,2
                    if isinstance(node.targets[0], ast.Tuple):
                        for right_expr,left_expr in zip(node.targets[0].elts, node.value.elts):
                            event = self.evaluate_assignmet(right_expr, left_expr, symbol_table, scope)
                    else:
                        right_expr = node.targets[0] 
                        left_expr =  node.value
                        event = self.evaluate_assignmet(right_expr, left_expr, symbol_table, scope)

                elif isinstance(node, ast.AugAssign):
                    right_expr = node.target
                    left_expr =  node.value
                    event = self.evaluate_assignmet(right_expr, left_expr, symbol_table, scope)
                
                identifier,raw_type,line = event
                if not (isinstance(raw_type, Unassigned)):
                    symbol_table.insert(identifier, raw_type, line, scope)

            # TODO 
            #function definition
            # elif (isinstance(node,ast.FunctionDef)):
            #     pass

    def evaluate_assignmet(self, right_expr: ast.Target, left_expr, symbol_table: SymbolTable, scope: Scope)-> list[str, int, int]:
        identifier,line = self.evaluate_target(right_expr, symbol_table, scope)
        raw_type = self.evaluate_rhs(left_expr, symbol_table, scope)
        return (identifier,raw_type,line)
    
    def evaluate_rhs(self, left_expr: ast.AST , symbol_table: SymbolTable, scope: Scope)-> str:
        raw_type = Unassigned()
        if isinstance(left_expr, ast.Constant):
            raw_obj = ast.literal_eval(left_expr)
            raw_type = type(raw_obj)

        elif isinstance(left_expr, ast.Name):
            # TODO
            # Add checks if the leftmost identifier doesnt exist in the program! (Users can make mistakes in their code)
            left_identifier = left_expr.id 
            left_identifier_table = symbol_table[left_identifier]
            left_identifier_latest_entry = left_identifier_table[-1]
            raw_type = left_identifier_latest_entry.type
        return raw_type

    def evaluate_target(self, right_expr: ast.Target, symbol_table: SymbolTable, scope: Scope)-> list[str, int]:
        line = right_expr.lineno
        identifier = right_expr.id

        if identifier not in symbol_table:
            symbol_table.insert(identifier, Unassigned(), 0, scope)

        return identifier,line

    def build_file_ast(self, file: str) -> ast.Module:
        with open(file) as f:
            tree = ast.parse(f.read())
            return tree

    def __str__(self) -> str:
        if self.symbol_table is None:
            return "VariableProgramMap (not yet traced)"
        return str(self.program_scope_tree.tree[0][0])

    def __repr__(self) -> str:
        return f"VariableProgramMap(file={self.file!r})"


class ExprEvaluator():
    pass

class ConstantExprEvaluator():
    pass

class NameExprEvaluator():
    pass

class FunctionDefExprEvaluator():
    pass

class CallExprEvaluator():
    pass

class TenaryExprEvaluator():
    pass

class ClassExprEvaluator():
    pass

class MethodCallExprEvaluator():
    pass

class ListExprEvaluator():
    pass

class IteratorExprEvaluator():
    pass

class ForExprEvaluator():
    pass
