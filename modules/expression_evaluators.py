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
        scope_frame  = scope_frame_stack[-1]
        symbol_table = scope_frame.symbol_table


        if scope_frame.scope_kind == Scope.GLOBAL:
            return self._resolve_from(_id, symbol_table, Scope.GLOBAL)

        # In local scope: check global/nonlocal mutations first
        if _id in scope_frame.mutated_symbols:
            target_namespace_id = scope_frame.mutated_symbols[_id]
            for frame in scope_frame_stack:
                if frame.namespace_id == target_namespace_id:
                    target_scope = Scope.GLOBAL if frame.scope_kind == Scope.GLOBAL else Scope.LOCAL
                    return self._resolve_from(_id, frame.symbol_table, target_scope)

        # Try local
        if _id in symbol_table.tables[Scope.LOCAL]:
            return self._resolve_from(_id, symbol_table, Scope.LOCAL)

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
