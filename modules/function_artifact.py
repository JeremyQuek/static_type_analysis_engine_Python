import ast


class FunctionArtifact:
    def __init__(self, ast_node: ast.FunctionDef, namespace_id: uuid, free_variables: list=[]) -> None:
        self.namespace_id = namespace_id
        self.ast_node = ast_node 
        self.free_variables = free_variables
