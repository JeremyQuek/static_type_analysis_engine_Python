import ast

from modules.scopes import Scope, ScopeFrame
from modules.symbol_table import SymbolTable
from modules.type_lattice import Unassigned, Unknown


class ExprEvaluator:
    pass

class ConstantExprEvaluator():
    def evaluate(self, expr: ast.Costant) -> type:
        raw_obj = ast.literal_eval(expr)
        raw_type = type(raw_obj)
        return raw_type

class NameExprEvaluator():
    def evaluate(self, expr: ast.AST, scope_frame_stack: list[ScopeFrame]) -> type:
        _id = expr.id
        scope_frame = scope_frame_stack[-1]
        symbol_table = scope_frame.symbol_table

        # If mutated (global/nonlocal), resolve from the target frame
        if _id in scope_frame.modified_symbol_scopes:
            target_namespace_id, target_scope = scope_frame.modified_symbol_scopes[_id]
            for frame in scope_frame_stack:
                if frame.namespace_id == target_namespace_id:
                    return self._resolve_from(_id, frame.symbol_table, target_scope)

        # LEGB resolution
        # Try local
        if scope_frame.scope_kind == Scope.LOCAL:
            if _id in symbol_table.tables[Scope.LOCAL]:
                return self._resolve_from(_id, symbol_table, Scope.LOCAL)

        # Try enclosing
        for (_ns_id, enclosing_dict) in reversed(symbol_table.tables[Scope.ENCLOSING]):
            if _id in enclosing_dict:
                return enclosing_dict[_id][-1].type

        # Try Global 
        global_frame = scope_frame_stack[0]
        if _id in global_frame.symbol_table.tables[Scope.GLOBAL]:
            return self._resolve_from(_id, global_frame.symbol_table, Scope.GLOBAL)

        # Try builtin
        if _id in global_frame.symbol_table.tables[Scope.BUILTIN]:
            return self._resolve_from(_id, global_frame.symbol_table, Scope.BUILTIN)

        return Unknown()

    def _resolve_from(self, _id: str, symbol_table: SymbolTable, scope: Scope) -> type:
        entries = symbol_table.tables[scope].get(_id)
        if entries:
            return entries[-1].type
        return Unassigned()

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
