from pathlib import Path
import argparse

from tests.test_runner import TestRunner


class Tester:
    def __init__(self, tests_root: Path, directories: list[Path], file_prefix: str | None):
        self.tests_root = tests_root
        self.directories = directories
        self.file_prefix = file_prefix
        self.runner = TestRunner()

    def run(self) -> None:
        if self.file_prefix:
            self.run_test_prefix(self.file_prefix)
        else:
            self.run_test_dirs(self.directories)
        self.runner.summary()

    def run_test_dirs(self, directories: list[Path]) -> None:
        for directory in directories:
            self.run_test_dir(directory)

    def run_test_dir(self, directory: Path):
        files = sorted(directory.glob("*.py"))

        if not files:
            return

        print(f"Running {directory.name}...\n")

        for file in files:
            self.runner.run_test_file(file, directory)

        print()

    def run_test_prefix(self, prefix: str):
        print(f"Running tests with prefix '{prefix}'...\n")

        for file in sorted(self.tests_root.rglob(f"{prefix}*.py")):
            self.runner.run_test_file(file, self.tests_root)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Static Type Analysis Engine"
    )
    parser.add_argument(
        "-d",
        "--directories",
        nargs="+",
        default=["*"],
        help="One or more test directories (default: all subdirectories of tests)",
    )

    parser.add_argument(
        "-f",
        "--file-prefix",
        help="Only run test files whose names start with this prefix",
    )

    args = parser.parse_args()

    tests_root = Path(__file__).parent

    if args.directories == ["*"]:
        directories = [d for d in tests_root.iterdir() if d.is_dir()]
    else:
        directories = [tests_root / name for name in args.directories]

    tester = Tester(tests_root, directories, args.file_prefix)
    tester.run()


if __name__ == "__main__":
    main()
