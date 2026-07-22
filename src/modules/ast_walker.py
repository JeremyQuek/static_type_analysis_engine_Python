import ast
from control_flow_graph import ControlFlowGraph
from custom_ast_node import Body, FunctionBody, ClassBody

class ASTWalker():
    def __init__(self, cfg: ControlFlowGraph, filepath: str):
        self.cfg = cfg
        self.filepath = filepath
        self.ast = self.get_ast()

    def get_ast(self) -> ast.AST:
        with open(self.filepath, "r", encoding="utf-8") as f:
            source_code = f.read()
        return ast.parse(source_code, filename=self.filepath)

    def traverse_ast_for_cfg(self):
        self.parse(self.ast, None)

    def get_body_type(self, parent: ast.AST | None):
        if isinstance(parent, ast.FunctionDef):
            return FunctionBody
        if isinstance(parent, ast.ClassDef):
            return ClassBody
        return Body

    def parse(self, ast_node: ast.AST, parent: ast.AST | None = None):
        code_body = ast_node.body
        CustomBody = self.get_body_type(parent)

        # Step 1 split the list into sections
        l=0
        cfg_nodes = [parent]
        for r in range(len(code_body)):
            cur_node = code_body[r]
            if isinstance(cur_node, ast.FunctionDef) or isinstance(cur_node, ast.ClassDef):
                if r > l:
                    stmts = code_body[l:r]
                    cfg_nodes.append(CustomBody(
                        body=stmts,
                        lineno=stmts[0].lineno,
                        col_offset=stmts[0].col_offset,
                        end_lineno=stmts[-1].end_lineno,
                        end_col_offset=stmts[-1].end_col_offset,
                    ))
                cfg_nodes.append(cur_node)
                self.parse(cur_node, parent=cur_node)
                l = r+1

        if l < len(code_body):
            stmts = code_body[l:]
            cfg_nodes.append(CustomBody(
                body=stmts,
                lineno=stmts[0].lineno,
                col_offset=stmts[0].col_offset,
                end_lineno=stmts[-1].end_lineno,
                end_col_offset=stmts[-1].end_col_offset,
            ))

        # Step 2 insert the edges
        for i in range(len(cfg_nodes)-1):
            self.cfg.insert(cfg_nodes[i], cfg_nodes[i+1])

if __name__ == "__main__":
    cfg = ControlFlowGraph()
    walker = ASTWalker(cfg, "tests/linear.py")
    walker.traverse_ast_for_cfg()
    walker.cfg._pretty_print()

