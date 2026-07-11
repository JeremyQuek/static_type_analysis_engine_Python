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
    CONTROL= "C"

class VariableProgramMap():
    def __init__(self, file: str) -> None:
        self.file = file
        self.file_ast = self.build_file_ast(self.file)
        self.program_scope_tree = LexicalScopeTree()
        self.symbol_table_stack = []
        self.top_table = None

    def trace(self) -> None:
        self.top_table = SymbolTable()
        self.symbol_table_stack.append( self.top_table )
        self.analyze_code_block(self.file_ast.body, Scope.GLOBAL)

    def analyze_code_block(self, code_block, scope: Scope):
        symbol_table = self.symbol_table_stack[-1]

        for node in code_block:
            # Control flow
            if isinstance(node, ast.If):
                if_symbol_table = symbol_table.fork_for_branch()
                self.symbol_table_stack.append(if_symbol_table)
                self.analyze_code_block(node.body, scope)
                self.symbol_table_stack.pop()

                if not node.orelse:
                    symbol_table.merge_branch(node.end_lineno, scope, if_symbol_table)
                    continue

                else_symbol_table = symbol_table.fork_for_branch()
                self.symbol_table_stack.append(else_symbol_table)
                self.analyze_code_block(node.orelse, scope)
                self.symbol_table_stack.pop()

                symbol_table.merge_branch(node.end_lineno, scope, if_symbol_table, else_symbol_table, parent_branch=False)
            
            elif isinstance(node, ast.While):
                while_symbol_table = symbol_table.fork_for_branch()
                self.symbol_table_stack.append(while_symbol_table)
                self.analyze_code_block(node.body, scope)
                self.symbol_table_stack.pop()

                symbol_table.merge_branch(node.end_lineno, scope, while_symbol_table)
            
            elif isinstance(node, ast.For):
                right_expr = node.target
                left_expr =  node.iter
                identifier,raw_type,line = self.evaluate_assignmet(right_expr, left_expr)
                if identifier not in symbol_table:
                    symbol_table.insert(identifier, Unassigned(), 0, scope)
                if not (isinstance(raw_type, Unassigned)):
                    symbol_table.insert(identifier, raw_type, line, scope)

                for_symbol_table = symbol_table.fork_for_branch()
                self.symbol_table_stack.append(for_symbol_table)
                self.analyze_code_block(node.body, scope)
                self.symbol_table_stack.pop()


            # Aug assign statement 
            elif isinstance(node, ast.AugAssign):
                right_expr = node.target
                left_expr =  node.value
                identifier,raw_type,line = self.evaluate_assignmet(right_expr, left_expr)

                if identifier not in symbol_table:
                    symbol_table.insert(identifier, Unassigned(), 0, scope)
                if not (isinstance(raw_type, Unassigned)):
                    symbol_table.insert(identifier, raw_type, line, scope)
    
            elif isinstance(node, ast.Assign):
                event = None
                # Handles multi-assignment a,b=1,2
                if isinstance(node.targets[0], ast.Tuple):
                    for right_expr,left_expr in zip(node.targets[0].elts, node.value.elts):
                        event = self.evaluate_assignmet(right_expr, left_expr)
                else:
                    right_expr = node.targets[0] 
                    left_expr =  node.value
                    event = self.evaluate_assignmet(right_expr, left_expr)
                
                identifier,raw_type,line = event
                if identifier not in symbol_table:
                    symbol_table.insert(identifier, Unassigned(), 0, scope)

                if not (isinstance(raw_type, Unassigned)):
                    symbol_table.insert(identifier, raw_type, line, scope)

        start_line = code_block[0].lineno if code_block else 0
        end_line = code_block[-1].end_lineno if code_block else 0
        self.program_scope_tree.insert((symbol_table, start_line, end_line))

    def evaluate_assignmet(self, right_expr: ast.Target, left_expr)-> list[str, int, int]:
        identifier,line = self.evaluate_target(right_expr)
        raw_type = self.evaluate_rhs(left_expr)
        return (identifier,raw_type,line)
    
    def evaluate_rhs(self, left_expr: ast.AST)-> str:
        symbol_table = self.symbol_table_stack[-1]
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

    def evaluate_target(self, right_expr: ast.Target)-> list[str, int]:
        symbol_table = self.symbol_table_stack[-1]

        line = right_expr.lineno
        identifier = right_expr.id

        return identifier,line

    def build_file_ast(self, file: str) -> ast.Module:
        with open(file) as f:
            tree = ast.parse(f.read())
            return tree

    def __str__(self) -> str:
        if self.top_table is None:
            return "VariableProgramMap (not yet traced)"
        return str(self.top_table) + f"\n{str(  self.program_scope_tree.tree)}"

    def __repr__(self) -> str:
        return f"VariableProgramMap(file={self.file!r})"




class ExprEvaluateController():
    pass

class ExprEvaluator():
    pass

class ConstantExprEvaluator(ExprEvaluator):
    pass

class NameExprEvaluator(ExprEvaluator):
    pass

class FunctionDefExprEvaluator(ExprEvaluator):
    pass

class CallExprEvaluator(ExprEvaluator):
    pass

class TenaryExprEvaluator(ExprEvaluator):
    pass

class ClassExprEvaluator(ExprEvaluator):
    pass

class MethodCallExprEvaluator(ExprEvaluator):
    pass

class ListExprEvaluator(ExprEvaluator):
    pass

class IteratorExprEvaluator(ExprEvaluator):
    pass

class ForExprEvaluator(ExprEvaluator):
    pass
