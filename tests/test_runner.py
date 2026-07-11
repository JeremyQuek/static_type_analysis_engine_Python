from pathlib import Path
from ast import literal_eval

from modules.variable_program_map import VariableProgramMap
from tests.linearizer import Linearizer


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def run_test_file(self, file: Path, root: Path) -> bool:
        type_file = file.with_suffix(".type")

        if not type_file.exists():
            print(f"? {file.relative_to(root)}  (no .type file)")
            return False

        variable_map = VariableProgramMap(str(file))
        variable_map.trace()

        linearizer = Linearizer(variable_map.program_table_tree)
        actual = linearizer.as_list()

        expected = literal_eval(type_file.read_text())

        if set(actual) == set(expected):
            print(f"✓ {file.relative_to(root)}")
            self.passed += 1
            return True
        else:
            print(f"✗ {file.relative_to(root)}")
            self._print_diff(expected, actual)
            self.failed += 1
            return False

    def _print_diff(self, expected, actual):
        max_len = max(len(expected), len(actual))
        for i in range(max_len):
            exp = expected[i] if i < len(expected) else None
            act = actual[i] if i < len(actual) else None
            if exp != act:
                print(f"    [{i}] expected: {exp}")
                print(f"         actual:   {act}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\nPassed {self.passed}/{total} tests.")
