import ast

from modules.scopes import Scope, ScopeFrame, BUILTIN, GLOBAL, ENCLOSING, LOCAL
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
        symbol = expr.id
        scope_frame = scope_frame_stack[-1]
        symbol_table = scope_frame.symbol_table

        # TODO: Only supports definition time lookup
        # Check for mutated Scope
        modified_namespace_id, modified_scope = None, None
        if symbol in scope_frame.modified_symbol_scopes:
            modified_namespace_id, modified_scope = scope_frame.modified_symbol_scopes[symbol]

        SEARCH_LOCAL = (
            scope_frame.scope_kind == LOCAL
            and modified_scope is None
        )

        SEARCH_ENCLOSING = (
            scope_frame.scope_kind == LOCAL
            and modified_scope != GLOBAL
        )
        SEARCH_GLOBAL = True
        SEARCH_BUILTIN = True

        # LEGB resolution

        # Try local
        if SEARCH_LOCAL:
            if symbol in symbol_table.sections[LOCAL]:
                return self._resolve_from(symbol, symbol_table, LOCAL)

        # Try enclosing
        if SEARCH_ENCLOSING:
            for (namespace_id, enclosing_dict) in reversed(symbol_table.sections[ENCLOSING]):
                if modified_namespace_id is not None and namespace_id != modified_namespace_id:
                    continue

                if symbol in enclosing_dict:
                    return enclosing_dict[symbol][-1].type

        # Try Global
        if SEARCH_GLOBAL:
            global_frame = scope_frame_stack[0]
            if symbol in global_frame.symbol_table.sections[GLOBAL]:
                return self._resolve_from(symbol, global_frame.symbol_table, GLOBAL)

        # Try builtin
        if SEARCH_BUILTIN:
            if symbol in global_frame.symbol_table.sections[BUILTIN]:
                return self._resolve_from(symbol, global_frame.symbol_table, BUILTIN)

        return Unknown()



    def _resolve_from(self, symbol: str, symbol_table: SymbolTable, scope: Scope) -> type:
        entries = symbol_table.sections[scope].get(symbol)
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
