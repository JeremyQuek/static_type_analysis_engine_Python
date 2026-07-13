import ast

from modules.scopes import Scope
from modules.symbol_table import SymbolTable
from modules.type_lattice import Unassigned


class ExprEvaluator:
    pass

class ConstantExprEvaluator():
    def evaluate(self, expr: ast.Costant) -> type:
        raw_obj = ast.literal_eval(expr)
        raw_type = type(raw_obj)
        return raw_type

# needs to be updated to resolve on LEGB scopign, rn it only handles resolution on global
class NameExprEvaluator():
    def evaluate(self, expr: ast.AST, symbol_table: SymbolTable) -> type:
        left__id = expr.id
        left__id_table = symbol_table.table[Scope.GLOBAL][left__id]
        left__id_latest_entry = left__id_table[-1]
        raw_type = left__id_latest_entry.type
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
