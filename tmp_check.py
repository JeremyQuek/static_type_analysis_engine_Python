import sys
sys.path.insert(0, ".")

from modules.variable_program_map import VariableProgramMap
from tests.linearizer import Linearizer

variable_map = VariableProgramMap("tests/control_flow/control_flow.py")
variable_map.trace()
print(variable_map)

linearizer = Linearizer(variable_map.program_table_tree)
linearizer.print()
print()
print("as_list():")
for entry in linearizer.as_list():
    print(f"  {entry}")
