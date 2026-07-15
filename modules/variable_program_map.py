import ast
import types
from uuid import uuid4
from copy import deepcopy

from modules.scopes import Scope, ScopeFrame
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
        self.scope_frame_stack = []
        self.global_table = None

    def trace(self) -> None:
        self.global_table = SymbolTable()
        global_namespace_id = uuid4()
        self.scope_frame_stack.append(ScopeFrame(global_namespace_id, self.global_table, Scope.GLOBAL))
        self.analyze_code_block(self.file_ast.body)

    # TODO
    # Handle scope changes for individual variables
    def analyze_code_block(self, code_block: list[ast.AST]) -> None:
        scope_frame = self.scope_frame_stack[-1]
        scope_frame.start_line = code_block[0].lineno if code_block else 0
        scope_frame.end_line = code_block[-1].end_lineno if code_block else 0

        scope = scope_frame.scope_kind
        symbol_table = scope_frame.symbol_table
        current_namespace_id = scope_frame.namespace_id

        for node in code_block:
            if isinstance(node, ast.If):
                if_symbol_table = symbol_table.fork_for_branch()
                self.scope_frame_stack.append(ScopeFrame(current_namespace_id, if_symbol_table, scope))
                self.analyze_code_block(node.body)
                self.scope_frame_stack.pop()

                if not node.orelse:
                    symbol_table.merge_branch(node.end_lineno, scope, if_symbol_table)
                    continue

                else_symbol_table = symbol_table.fork_for_branch()
                self.scope_frame_stack.append(ScopeFrame(current_namespace_id, else_symbol_table, scope))
                self.analyze_code_block(node.orelse)
                self.scope_frame_stack.pop()

                symbol_table.merge_branch(node.end_lineno, scope, if_symbol_table, else_symbol_table, parent_branch=False)
            
            elif isinstance(node, ast.While):
                while_symbol_table = symbol_table.fork_for_branch()
                self.scope_frame_stack.append(ScopeFrame(current_namespace_id, while_symbol_table, scope))
                self.analyze_code_block(node.body)
                self.scope_frame_stack.pop()

                symbol_table.merge_branch(node.end_lineno, scope, while_symbol_table)
            
            # TODO
            # Handle variable unpacking in the for
            # To be implemented after implementing support for call sites
            # Also handle extracting the type for method "__contains__" in iteration:
            # for x in container
            elif isinstance(node, ast.For):
                right_expr = node.target
                left_expr =  node.iter
                self.evaluate_assignment(right_expr, left_expr)

                for_symbol_table = symbol_table.fork_for_branch()
                self.scope_frame_stack.append(ScopeFrame(current_namespace_id, for_symbol_table, scope))
                self.analyze_code_block(node.body)
                self.scope_frame_stack.pop()

   
            elif isinstance(node, ast.FunctionDef):
                # Step 1: Create the new namespace_id
                func_namespace_id = uuid4()

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
                function_def_symbol_table= symbol_table.fork_for_function_def(parameters_list, current_namespace_id)

                # Step 4: Update the scope stack
                self.scope_frame_stack.append(ScopeFrame(func_namespace_id, function_def_symbol_table, Scope.LOCAL))

                # Step 5: Recurse analysis on the function body
                self.analyze_code_block(node.body)

                # Step 6: Pop
                self.scope_frame_stack.pop()

                # Step 7: TODO
                enclosure_environment = []
                for i in range(len(self.scope_frame_stack)-1, -1, -1):
                    ancestor_scope_frame = self.scope_frame_stack[i]
                    ancestor_symbol_table = ancestor_scope_frame.symbol_table
                    ancestor_id = ancestor_scope_frame.namespace_id
                    enclosure_environment.append(self.scope_frame_stack[i])

                # Step 8: Update the current symbol table with the new reference binding to the function object type
                func_name = node.name
                func_line = node.lineno
                func_artifact = FunctionArtifact(node, func_namespace_id, enclosure_environment)
                symbol_table.insert(func_name, types.FunctionType, func_line, scope, artifact=func_artifact)

            # TODO: Add error handling of invalid call of global
            elif isinstance(node, ast.Global):
                for _id in node.names:
                    global_scope = self.scope_frame_stack[0].namespace_id
                    scope_frame.mutated_symbols[_id] = (global_scope, Scope.GLOBAL)

            # Walk up the recursion stack
            # TODO: Add error handling of invalid call of nonlocal
            elif isinstance(node, ast.Nonlocal):
                for _id in node.names:
                    origin_scope = self.resolve_symbol_origin(_id)
                    scope_frame.mutated_symbols[_id] = (origin_scope, Scope.LOCAL)

            # Aug assign statement
            elif isinstance(node, ast.AugAssign):
                self.evaluate_assignment(node.target, node.value)

            # multi assignment
            elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple):
                for right_expr, left_expr in zip(node.targets[0].elts, node.value.elts):
                    self.evaluate_assignment(right_expr, left_expr)

            # normal assignment
            elif isinstance(node, ast.Assign):
                self.evaluate_assignment(node.targets[0], node.value)

        self.program_table_tree.insert((symbol_table, scope_frame.start_line, scope_frame.end_line))

    
    def evaluate_assignment(self, right_expr: ast.Target, left_expr: ast.AST) -> None:
        _id, line = self.evaluate_lhs(right_expr)
        raw_type = self.evaluate_rhs(left_expr)

        scope_frame = self.scope_frame_stack[-1]
        scope = scope_frame.scope_kind

        symbol_table = scope_frame.symbol_table
        target_table = symbol_table
        target_scope = scope

        in_function_definition = True
        # If in local scope and _id was declared global/nonlocal, redirect to the target
        if scope == Scope.LOCAL and _id in scope_frame.mutated_symbols:
            target_namespace_id, target_scope = scope_frame.mutated_symbols[_id]
            if in_function_definition:
                # During definition: write to local copy of the target scope's table
                target_table = symbol_table
            else:
                # At callsite: mutate the real ancestor's table
                for frame in self.scope_frame_stack:
                    if frame.namespace_id == target_namespace_id:
                        target_table = frame.symbol_table
                        break

        if _id not in target_table.tables[target_scope]:
            target_table.insert(_id, Unassigned(), 0, target_scope)

        if not isinstance(raw_type, Unassigned):
            target_table.insert(_id, raw_type, line, target_scope)

    def evaluate_lhs(self, right_expr: ast.Target)-> tuple[str, int]:
        line = right_expr.lineno
        _id = right_expr.id
        
        return _id,line

    def evaluate_rhs(self, left_expr: ast.AST)-> type:
        scope_frame = self.scope_frame_stack[-1]
        raw_type = Unassigned()
        if isinstance(left_expr, ast.Constant):
            evaluator = ConstantExprEvaluator()
            raw_type = evaluator.evaluate(left_expr)

        elif isinstance(left_expr, ast.Name):
            # TODO
            # Add checks if the leftmost _id doesnt exist in the program! (Users can make mistakes in their code)
            evaluator = NameExprEvaluator()
            raw_type = evaluator.evaluate(left_expr, self.scope_frame_stack)
        return raw_type

    def resolve_symbol_origin(self, _id: str) -> UUID | None:
        # Don't check the current frame
        for i in range(len(self.scope_frame_stack)-2, -1, -1):
            _scope_frame = self.scope_frame_stack[i]
            _symbol_table = _scope_frame.symbol_table
            if _id in _symbol_table.tables[Scope.LOCAL]:
                return _scope_frame.namespace_id
        return None

    def build_file_ast(self, file: str) -> ast.Module:
        with open(file) as f:
            tree = ast.parse(f.read())
            return tree

    def __str__(self) -> str:
        if self.global_table is None:
            return "VariableProgramMap (not yet traced)"
        return str(self.global_table) + f"\n{str(  self.program_table_tree.tree)}"

    def __repr__(self) -> str:
        return f"VariableProgramMap(file={self.file!r})"

