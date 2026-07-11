from pathlib import Path
import argparse

from modules.variable_program_map import VariableProgramMap
from tests.linearizer import Linearizer


def export_file(file: Path):
    variable_map = VariableProgramMap(str(file))
    variable_map.trace()

    linearizer = Linearizer(variable_map.program_table_tree)
    result = linearizer.as_list()

    type_file = file.with_suffix(".type")
    type_file.write_text(repr(result) + "\n")
    print(f"  wrote {type_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Export .type files for test cases"
    )
    parser.add_argument(
        "-f",
        "--file-prefix",
        help="Only export for files whose names start with this prefix",
    )
    parser.add_argument(
        "-d",
        "--directories",
        nargs="+",
        default=["*"],
        help="One or more test directories (default: all subdirectories of tests)",
    )

    args = parser.parse_args()

    tests_root = Path(__file__).parent

    if args.file_prefix:
        files = sorted(tests_root.rglob(f"{args.file_prefix}*.py"))
        for file in files:
            export_file(file)
    else:
        if args.directories == ["*"]:
            directories = [d for d in tests_root.iterdir() if d.is_dir()]
        else:
            directories = [tests_root / name for name in args.directories]

        for directory in directories:
            files = sorted(directory.glob("*.py"))
            if files:
                print(f"Exporting {directory.name}...")
                for file in files:
                    export_file(file)


if __name__ == "__main__":
    main()
