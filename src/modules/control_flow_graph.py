import ast
from collections import defaultdict

from lexical_environment import LexicalEnvironment
from custom_ast_node import Body, FunctionBody, ClassBody

class Node():
    def __init__(self, block = None, enviroment = None):
        self.block = block
        self.enviroment = enviroment
        self.next = []

class TerminalNode(Node): pass
class EntryNode(TerminalNode): pass 
class ExitNode(TerminalNode):pass 

# Regular code node
class BodyNode(Node):pass
# Splinters into a graph that join
class ControlFlowNode(Node):pass
# Splinters into a subgraph
class DefinitionNode(Node): pass


class ControlFlowGraph():
    mapping= {
        ast.FunctionDef : DefinitionNode,
        ast.ClassDef : DefinitionNode,
        Body: BodyNode,
        FunctionBody: BodyNode,
        ClassBody: BodyNode,
        }

    def __init__(self):
        self.entry = EntryNode()
        self.nodes = {0: self.entry}
        self.edges=[]
        self.adj = defaultdict(list)

        # For pretty print
        self._id_counter = 0
        self._node_ids = {id(self.entry): 0}
    
    def insert(self, parent: ast.AST, child: ast.AST)->None:
        u = self.entry if parent is None else self._get_node(parent) 
        v = self._get_node(child)
        self.adj[u].append(v)
        self.edges.append([u,v])


    def _get_node(self, ast_node: ast.AST) -> Node:
        if ast_node not in self.nodes:
            u = self._create_node(ast_node)
            self.nodes[ast_node] = u 
        else:
            u = self.nodes[ast_node]
        return u

    # returns the correct Node Type,
    def _create_node(self, ast_node: ast.AST) -> Node:
        ast_type = type(ast_node)
        node_class = self.mapping[ast_type]
        node = node_class(block=ast_node)

        # For pretty print
        self._id_counter += 1
        self._node_ids[id(node)] = self._id_counter
        return node

    """
    Post AST Walk Graph topology changes
    """
    def _append_exit_nodes():
        pass

    def _format_class_bodies():
        pass
    
    def _split_control_flow():
        pass
    
    def _append_execution_graph_at_call_site():
        pass


    """
    Prints the edge list in a format pasteable into 
    graphonline.top/create_graph_by_edge_list 
    for visual debugging.
    """
    def _pretty_print(self):
        
        for u, v in self.edges:
            print(f"{self._label(u)}-{self._label(v)}")

    def _label(self, node: Node) -> str:
        nid = self._node_ids[id(node)]
        if isinstance(node, EntryNode):
            return f"Entry({nid})"
        if isinstance(node, ExitNode):
            return f"Exit({nid})"
        block = node.block
        if isinstance(block, FunctionBody):
            return f"FuncBody({nid})"
        if isinstance(block, ClassBody):
            return f"ClassBody({nid})"
        if isinstance(block, Body):
            return f"Body({nid})"
        if isinstance(block, ast.FunctionDef):
            return f"FuncDef({nid})"
        if isinstance(block, ast.ClassDef):
            return f"ClassDef({nid})"
        return f"Node({nid})"
    


