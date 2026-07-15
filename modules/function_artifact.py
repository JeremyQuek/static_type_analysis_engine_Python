import ast
from uuid import UUID
from collections import defaultdict


class FunctionArtifact:
    def __init__(self, ast_node: ast.FunctionDef, namespace_id: UUID, free_variables: list[tuple[UUID, defaultdict]] = []) -> None:
        self.namespace_id = namespace_id
        self.ast_node = ast_node
        self.free_variables = free_variables

        self.cache: dict = {}