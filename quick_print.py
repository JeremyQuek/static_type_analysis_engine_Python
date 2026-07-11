import argparse
import ast


def print_line(tree, lineno, include_attributes):
    # Dump the top-level statement that starts on the given source line.
    for node in tree.body:
        if getattr(node, "lineno", None) == lineno:
            print(ast.dump(node, indent=2, include_attributes=include_attributes))


def main():
    parser = argparse.ArgumentParser(
        description="Python AST Dumper"
    )
    parser.add_argument(
        "-f",
        "--file",
        required=True,
        help="Python source file to dump",
    )
    parser.add_argument(
        "-l",
        "--line",
        type=int,
        help="Dump only the top-level AST node starting on this line",
    )
    parser.add_argument(
        "--attributes",
        action="store_true",
        help="Include AST attributes (lineno, col_offset, etc.)",
    )

    args = parser.parse_args()

    with open(args.file) as f:
        tree = ast.parse(f.read())

    if args.line is None:
        print(ast.dump(tree, indent=2, include_attributes=args.attributes))
    else:
        print_line(tree, args.line, args.attributes)


if __name__ == "__main__":
    main()