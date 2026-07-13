import ast
import types
from uuid import uuid4

from modules.scopes import Scope
from modules.symbol_table import SymbolTable
from modules.type_lattice import Unassigned, Unknown
from modules.lexical_scope_tree import LexicalScopeTree
from modules.function_artifact import FunctionArtifact
from modules.expression_evaluators import ConstantExprEvaluator, NameExprEvaluator

# TODO
# 1) Float(inf) is not handled because callables aren't implemented


class VariableProgramMap():
    def __init__(self, file: str) -> None:
        self.file = file
        self.file_ast = self.build_file_ast(self.file)
        self.program_table_tree = LexicalScopeTree()
        self.symbol_table_stack = []
        self.top_table = None

    def trace(self) -> None:
        self.top_table = SymbolTable()
        global_namespace_id = uuid4()
        self.symbol_table_stack.append((self.top_table, global_namespace_id))
        self.analyze_code_block(self.file_ast.body, Scope.GLOBAL)

    # TODO
    # Handle scope changes for individual variables
    def analyze_code_block(self, code_block: list[ast.AST], scope: Scope) -> None:
        symbol_table = self.symbol_table_stack[-1][0]
        current_namespace_id = self.symbol_table_stack[-1][1]

        for node in code_block:
            if isinstance(node, ast.If):
                if_symbol_table = symbol_table.fork_for_branch()
                self.symbol_table_stack.append((if_symbol_table, current_namespace_id))
                self.analyze_code_block(node.body, scope)
                self.symbol_table_stack.pop()

                if not node.orelse:
                    symbol_table.merge_branch(node.end_lineno, scope, if_symbol_table)
                    continue

                else_symbol_table = symbol_table.fork_for_branch()
                self.symbol_table_stack.append((else_symbol_table,current_namespace_id))
                self.analyze_code_block(node.orelse, scope)
                self.symbol_table_stack.pop()

                symbol_table.merge_branch(node.end_lineno, scope, if_symbol_table, else_symbol_table, parent_branch=False)
            
            elif isinstance(node, ast.While):
                while_symbol_table = symbol_table.fork_for_branch()
                self.symbol_table_stack.append((while_symbol_table, current_namespace_id))
                self.analyze_code_block(node.body, scope)
                self.symbol_table_stack.pop()

                symbol_table.merge_branch(node.end_lineno, scope, while_symbol_table)
            
            # TODO
            # Handle variable unpacking in the for
            # To be implemented after implementing support for call sites
            # Also handle extracting the type for method "__contains__" in iteration:
            # for x in container
            elif isinstance(node, ast.For):
                right_expr = node.target
                left_expr =  node.iter
                _id,raw_type,line = self.evaluate_assignment(right_expr, left_expr)
                if _id not in symbol_table:
                    symbol_table.insert(_id, Unassigned(), 0, scope)
                if not (isinstance(raw_type, Unassigned)):
                    symbol_table.insert(_id, raw_type, line, scope)

                for_symbol_table = symbol_table.fork_for_branch()
                self.symbol_table_stack.append((for_symbol_table, current_namespace_id))
                self.analyze_code_block(node.body, scope)
                self.symbol_table_stack.pop()

   
            elif isinstance(node, ast.FunctionDef):
                # Step 1: Create the new namespace_id
                namespace_id = uuid4()

                # Step 2: Parse the arguments and their types into a list
                
                # TODO
                # Handle args
                # Handle kwards
                # Handle return annotations
                parameters_list = []
                # parse args
                for arg_block in node.args.args:
                    arg__id = arg_block.arg
                    arg_line = arg_block.lineno
                    arg_type = Unknown() if not arg_block.annotation else arg_block.annotation.id
                    parameters_list.append([arg__id, arg_type, arg_line])

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
                
                # Step 3: Fork the table
                function_def_symbol_table= symbol_table.fork_for_function(parameters_list, func_namespace_id)


                # Step 4: Update the scope stack
                self.symbol_table_stack.append((function_def_symbol_table, namespace_id))

                # Step 5: Recurse analysis on the function body
                self.analyze_code_block(function_def_symbol_table)

                # Step 6: Pop
                self.symbol_table_stack.pop()

                # Step 7: 
                symbol_table.merge_function_def(node.end_lineno, scope, while_symbol_table)
                
                # Step 8: TODO
                # Flatten out the parent enclosure + local into a single enclosure env for the child, using shallow copy so that context changes are captured      
                enclosure_environment = []

                # Step 9: Update the current symbol table with the new reference binding to the function object type
                func_name = node.name
                func_line = node.lineno
                func_artifact = FunctionArtifact(node, namespace_id, [])
                symbol_table.insert(func_name, types.FunctionType, func_line, scope, {"artifact": func_artifact})

            # Aug assign statement 
            elif isinstance(node, ast.AugAssign):
                right_expr = node.target
                left_expr =  node.value
                _id,raw_type,line = self.evaluate_assignment(right_expr, left_expr)

                if _id not in symbol_table:
                    symbol_table.insert(_id, Unassigned(), 0, scope)
                if not (isinstance(raw_type, Unassigned)):
                    symbol_table.insert(_id, raw_type, line, scope)

            # multi assignment
            elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple):
                for right_expr,left_expr in zip(node.targets[0].elts, node.value.elts):
                    _id,raw_type,line = self.evaluate_assignment(right_expr, left_expr)

                    if _id not in symbol_table:
                        symbol_table.insert(_id, Unassigned(), 0, scope)

                    if not (isinstance(raw_type, Unassigned)):
                        symbol_table.insert(_id, raw_type, line, scope)

            # normal assignment
            elif isinstance(node, ast.Assign):
                right_expr = node.targets[0] 
                left_expr =  node.value
                _id,raw_type,line = self.evaluate_assignment(right_expr, left_expr)
                

                # TODO
                # is unassigned insertion always just on scope?
                if _id not in symbol_table.table[scope]:
                    symbol_table.insert(_id, Unassigned(), 0, scope)

                if not (isinstance(raw_type, Unassigned)):
                    symbol_table.insert(_id, raw_type, line, scope)


        start_line = code_block[0].lineno if code_block else 0
        end_line = code_block[-1].end_lineno if code_block else 0
        self.program_table_tree.insert((symbol_table, start_line, end_line))

    def evaluate_assignment(self, right_expr: ast.Target, left_expr: ast.AST)-> tuple[str, type, int]:
        raw_type = self.evaluate_rhs(left_expr)
        _id,line = self.evaluate_lhs(right_expr)
        return (_id,raw_type,line)

    def evaluate_lhs(self, right_expr: ast.Target)-> tuple[str, int]:
        symbol_table = self.symbol_table_stack[-1]

        line = right_expr.lineno
        _id = right_expr.id

        return _id,line

    def evaluate_rhs(self, left_expr: ast.AST)-> type:
        symbol_table = self.symbol_table_stack[-1]
        raw_type = Unassigned()
        if isinstance(left_expr, ast.Constant):
            evaluator = ConstantExprEvaluator()
            raw_type = evaluator.evaluate(left_expr)

        elif isinstance(left_expr, ast.Name):
            # TODO
            # Add checks if the leftmost _id doesnt exist in the program! (Users can make mistakes in their code)
            evaluator = NameExprEvaluator
            raw_type = evaluator.evaluate(left_expr, symbol_table)
        return raw_type

    def build_file_ast(self, file: str) -> ast.Module:
        with open(file) as f:
            tree = ast.parse(f.read())
            return tree

    def __str__(self) -> str:
        if self.top_table is None:
            return "VariableProgramMap (not yet traced)"
        return str(self.top_table) + f"\n{str(  self.program_table_tree.tree)}"

    def __repr__(self) -> str:
        return f"VariableProgramMap(file={self.file!r})"

