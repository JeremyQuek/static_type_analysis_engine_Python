import ast
import types

from modules.scopes import Scope
from modules.symbol_table import SymbolTable
from modules.type_lattice import Unassigned, Unknown
from modules.lexical_scope_tree import LexicalScopeTree

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

    # TODO
    # Handle scope changes for individual variables
    def analyze_code_block(self, code_block: list[ast.AST], scope: Scope) -> None:
        symbol_table = self.symbol_table_stack[-1]

        for node in code_block:
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
            
            # TODO
            # Handle variable unpacking in the for
            # To be implemented after implementing support for call sites
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

            # TODO
            # Handle args
            # Handle kwards
            # Handle return annotations
            elif isinstance(node, ast.FunctionDef):
                parameters_list = []
                # parse args
                for arg_block in node.args.args:
                    arg_identifier = arg_block.arg
                    arg_line = arg_block.lineno
                    arg_type = Unknown() if not arg_block.annotation else arg_block.annotation.id
                    parameters_list.append([arg_identifier, arg_type, arg_line])

                # factor in defaults
                cur_param_idx = len(parameters_list)-1
                for default_value in node.args.defaults:
                    evaluator = ConstantExprEvaluator()
                    default_type = evaluator.evaluate(default_value)
                    # Theoretically we should have bounds check here since we are manually iterating indexes
                    # But practically len(defaults) should nvr > len(argument.args)
                    if parameters_list[cur_param_idx][1] == Unknown():
                        parameters_list[cur_param_idx][1] = default_type
                    cur_param_idx-=1
                
                #fork
                function_def_symbol_table= symbol_table.fork_for_function(parameters_list)
                self.symbol_table_stack.append(function_def_symbol_table)
                self.analyze_code_block(function_def_symbol_table)
                self.symbol_table_stack.pop()

                symbol_table.merge_function_def(node.end_lineno, scope, while_symbol_table)
                
                func_name = node.name
                func_line = node.lineno
                symbol_table.insert(func_name, types.FunctionType, func_line, scope)

            # Aug assign statement 
            elif isinstance(node, ast.AugAssign):
                right_expr = node.target
                left_expr =  node.value
                identifier,raw_type,line = self.evaluate_assignmet(right_expr, left_expr)

                if identifier not in symbol_table:
                    symbol_table.insert(identifier, Unassigned(), 0, scope)
                if not (isinstance(raw_type, Unassigned)):
                    symbol_table.insert(identifier, raw_type, line, scope)

            # multi assignment
            elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple):
                for right_expr,left_expr in zip(node.targets[0].elts, node.value.elts):
                    identifier,raw_type,line = self.evaluate_assignmet(right_expr, left_expr)

                    if identifier not in symbol_table:
                        symbol_table.insert(identifier, Unassigned(), 0, scope)

                    if not (isinstance(raw_type, Unassigned)):
                        symbol_table.insert(identifier, raw_type, line, scope)

            # normal assignment
            elif isinstance(node, ast.Assign):
                right_expr = node.targets[0] 
                left_expr =  node.value
                identifier,raw_type,line = self.evaluate_assignmet(right_expr, left_expr)
                
                if identifier not in symbol_table:
                    symbol_table.insert(identifier, Unassigned(), 0, scope)

                if not (isinstance(raw_type, Unassigned)):
                    symbol_table.insert(identifier, raw_type, line, scope)


        start_line = code_block[0].lineno if code_block else 0
        end_line = code_block[-1].end_lineno if code_block else 0
        self.program_scope_tree.insert((symbol_table, start_line, end_line))

    def evaluate_assignmet(self, right_expr: ast.Target, left_expr: ast.AST)-> tuple[str, type, int]:
        identifier,line = self.evaluate_target(right_expr)
        raw_type = self.evaluate_rhs(left_expr)
        return (identifier,raw_type,line)
    
    def evaluate_rhs(self, left_expr: ast.AST)-> type:
        symbol_table = self.symbol_table_stack[-1]
        raw_type = Unassigned()
        if isinstance(left_expr, ast.Constant):
            evaluator = ConstantExprEvaluator
            raw_type = evaluator.evaluate(left_expr)

        elif isinstance(left_expr, ast.Name):
            # TODO
            # Add checks if the leftmost identifier doesnt exist in the program! (Users can make mistakes in their code)
            evaluator = NameExprEvaluator
            raw_type = evaluator.evaluate(left_expr, symbol_table)
        return raw_type

    def evaluate_target(self, right_expr: ast.Target)-> tuple[str, int]:
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

class ExprEvaluator:
    pass

class ConstantExprEvaluator():
    def evaluate(self, expr: ast.Costant) -> type:
        raw_obj = ast.literal_eval(expr)
        raw_type = type(raw_obj)
        return raw_type

class NameExprEvaluator():
    def evaluate(self, expr: ast.AST, symbol_table: SymbolTable) -> type:
        left_identifier = expr.id 
        left_identifier_table = symbol_table[left_identifier]
        left_identifier_latest_entry = left_identifier_table[-1]
        raw_type = left_identifier_latest_entry.type
        return raw_type

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
