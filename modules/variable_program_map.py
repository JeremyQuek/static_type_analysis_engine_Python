import ast
import types
from uuid import uuid4
from copy import deepcopy

from modules.scopes import Scope, GlobalScope, FunctionScope, BranchScope, ClassScope, BUILTIN, GLOBAL, ENCLOSING, LOCAL, CLASS
from modules.symbol_table import SymbolTable
from modules.type_lattice import Unassigned, Unknown
from modules.lexical_scope_tree import LexicalScopeTree
from modules.function_metadata import FunctionMetadata
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
        self.scope_frame_stack.append(GlobalScope(global_namespace_id, self.global_table, GLOBAL))
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
                self.scope_frame_stack.append(BranchScope(current_namespace_id, if_symbol_table, scope, modified_symbol_scopes=scope_frame.modified_symbol_scopes))
                self.analyze_code_block(node.body)
                self.scope_frame_stack.pop()

                if not node.orelse:
                    symbol_table.merge_branch(node.end_lineno, scope, if_symbol_table)
                    continue

                else_symbol_table = symbol_table.fork_for_branch()
                self.scope_frame_stack.append(BranchScope(current_namespace_id, else_symbol_table, scope, modified_symbol_scopes=scope_frame.modified_symbol_scopes))
                self.analyze_code_block(node.orelse)
                self.scope_frame_stack.pop()

                symbol_table.merge_branch(node.end_lineno, scope, if_symbol_table, else_symbol_table, parent_branch=False)
            
            elif isinstance(node, ast.While):
                while_symbol_table = symbol_table.fork_for_branch()
                self.scope_frame_stack.append(BranchScope(current_namespace_id, while_symbol_table, scope, modified_symbol_scopes=scope_frame.modified_symbol_scopes))
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
                self.scope_frame_stack.append(BranchScope(current_namespace_id, for_symbol_table, scope, modified_symbol_scopes=scope_frame.modified_symbol_scopes))
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
                self.scope_frame_stack.append(FunctionScope(func_namespace_id, function_def_symbol_table, LOCAL))

                # Step 5: Recurse analysis on the function body
                self.analyze_code_block(node.body)

                # Step 6: Pop
                self.scope_frame_stack.pop()

                # Step 7: The closure environment is captured during definition and irregardless of the call stack
                # Environment is fixed but variables are live
                closure_environment = []
                for i in range(len(self.scope_frame_stack)-1, -1, -1):
                    ancestor_scope_frame = self.scope_frame_stack[i]
                    ancestor_symbol_table = ancestor_scope_frame.symbol_table
                    ancestor_id = ancestor_scope_frame.namespace_id
                    closure_environment.append(self.scope_frame_stack[i])

                # Step 8: Update the current symbol table with the new reference binding to the function object type
                func_name = node.name
                func_line = node.lineno
                func_metadata = FunctionMetadata(node, func_namespace_id, closure_environment)
                symbol_table.insert(func_name, types.FunctionType, func_line, scope, artifact=func_metadata)

            # TODO: Add error handling of invalid call of global
            elif isinstance(node, ast.Global):
                for symbol in node.names:
                    global_scope = self.scope_frame_stack[0].namespace_id
                    scope_frame.modified_symbol_scopes[symbol] = (global_scope, "global")

            # Walk up the recursion stack
            # TODO: Add error handling of invalid call of nonlocal
            elif isinstance(node, ast.Nonlocal):
                for symbol in node.names:
                    origin_scope = self.resolve_symbol_origin(symbol)
                    scope_frame.modified_symbol_scopes[symbol] = (origin_scope, "nonlocal")

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
        symbol, line = self.evaluate_lhs(right_expr)
        raw_type = self.evaluate_rhs(left_expr)

        scope_frame = self.scope_frame_stack[-1]
        scope = scope_frame.scope_kind
        symbol_table = scope_frame.symbol_table
        in_function_definition = True

        # if we are global, trivial, scope modifiers shldnt exist
        if scope == GLOBAL:
            self._insert_into(symbol_table, symbol, raw_type, line, GLOBAL)

        # If we are in a function
        # Assignment targets require different lookup semantics from NameExprEvaluator.
        #
        # NameExprEvaluator resolves a value, so it performs a read-only LEGB lookup
        # until the first matching binding is found.
        #
        # Assignment instead resolves the destination of the write. If the identifier
        # has been marked as global/nonlocal, the assignment must target a fundamentally
        # different table to insert into, hence the branching logic searches for that table


        # TODO nonlocal propagates on read
        # But if u assign a propagated nonlocal x from a parent without calling nonlocal
        # You reassign it to a local
        elif scope == LOCAL:
            # Case 1: Target scope modified
            if symbol in scope_frame.modified_symbol_scopes:
                target_namespace_id, target_scope = scope_frame.modified_symbol_scopes[symbol]

                # Case 1a: In function definition, modify local copy
                if in_function_definition:
                    if target_scope == GLOBAL:
                        self._insert_into(symbol_table, symbol, raw_type, line, GLOBAL)
                    else:
                        if not isinstance(raw_type, Unassigned):
                            symbol_table.insert_free_variable(symbol, raw_type, line, target_namespace_id)

                # Case 1b: At callsite: modify the real ancestor's table
                else:
                    # TODO: Dont traverse the stack frame, traverse closure environment which contains frames that might already be removed
                    # Need a way to access it
                    for frame in self.scope_frame_stack:
                        if frame.namespace_id == target_namespace_id:
                            self._insert_into(frame.symbol_table, symbol, raw_type, line, target_scope)
                            break

            # Case 2: Target scope not modified, so its local
            else:
                self._insert_into(symbol_table, symbol, raw_type, line, LOCAL)

    def _insert_into(self, table: SymbolTable, symbol: str, raw_type: type, line: int, scope: Scope) -> None:
        if symbol not in table.sections[scope]:
            table.insert(symbol, Unassigned(), 0, scope)
        if not isinstance(raw_type, Unassigned):
            table.insert(symbol, raw_type, line, scope)

    def evaluate_lhs(self, right_expr: ast.Target)-> tuple[str, int]:
        line = right_expr.lineno
        symbol = right_expr.id

        return symbol,line

    def evaluate_rhs(self, left_expr: ast.AST)-> type:
        scope_frame = self.scope_frame_stack[-1]
        raw_type = Unassigned()
        if isinstance(left_expr, ast.Constant):
            evaluator = ConstantExprEvaluator()
            raw_type = evaluator.evaluate(left_expr)

        elif isinstance(left_expr, ast.Name):
            # TODO
            # Add checks if the leftmost symbol doesnt exist in the program! (Users can make mistakes in their code)
            evaluator = NameExprEvaluator()
            raw_type = evaluator.evaluate(left_expr, self.scope_frame_stack)
        return raw_type

    def resolve_symbol_origin(self, symbol: str) -> UUID | None:
        # Don't check the current frame
        for i in range(len(self.scope_frame_stack)-2, -1, -1):
            _scope_frame = self.scope_frame_stack[i]
            _symbol_table = _scope_frame.symbol_table
            if symbol in _symbol_table.sections[LOCAL]:
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

