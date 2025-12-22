import ast
import os
import re
import sys
from typing import Set, Tuple

DRY_RUN = "--dry-run" in sys.argv
VERBOSE = "--verbose" in sys.argv


class DocstringRemover(ast.NodeVisitor):
    def __init__(self, lines: list[str]):
        self.lines = lines
        self.lines_to_remove: Set[int] = set()
        self.file_content = "".join(lines)

    def visit_Module(self, node: ast.Module) -> None:
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring_node = node.body[0]
            self._mark_docstring_for_removal(docstring_node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring_node = node.body[0]
            self._mark_docstring_for_removal(docstring_node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring_node = node.body[0]
            self._mark_docstring_for_removal(docstring_node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _mark_docstring_for_removal(self, node: ast.Expr) -> None:
        start_line = node.lineno - 1
        end_line = node.end_lineno

        for line_num in range(start_line, end_line):
            self.lines_to_remove.add(line_num)


def is_help_text_line(line: str) -> bool:
    return "help_text=" in line


def should_keep_comment(comment: str) -> bool:
    keywords = ["TODO", "FIXME", "HACK", "XXX", "NOTE"]
    for keyword in keywords:
        if keyword in comment:
            return True
    return False


def is_complex_comment(comment: str) -> bool:
    if len(comment) > 100:
        return True

    technical_terms = [
        "algorithm",
        "logic",
        "handle",
        "exception",
        "error",
        "validation",
        "format",
        "parse",
        "convert",
        "transform",
        "calculate",
        "compute",
        "optimization",
        "performance",
    ]

    comment_lower = comment.lower()
    return any(term in comment_lower for term in technical_terms)


def remove_simple_comments(content: str) -> str:
    lines = content.split("\n")
    result_lines = []

    for _i, line in enumerate(lines):
        if "help_text=" in line:
            result_lines.append(line)
            continue

        stripped = line.lstrip()

        if stripped.startswith("#"):
            comment_text = stripped[1:].strip()

            if should_keep_comment(comment_text):
                result_lines.append(line)
            elif is_complex_comment(comment_text):
                result_lines.append(line)
            else:
                pass
        else:
            result_lines.append(line)

    return "\n".join(result_lines)


def remove_docstrings_from_file(file_path: str) -> Tuple[bool, str]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        original_content = "".join(lines)

        try:
            tree = ast.parse(original_content, filename=file_path)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        remover = DocstringRemover(lines)
        remover.visit(tree)

        modified_lines = [line for i, line in enumerate(lines) if i not in remover.lines_to_remove]

        modified_content = "".join(modified_lines)

        modified_content = remove_simple_comments(modified_content)

        modified_content = re.sub(r"\n\n\n+", "\n\n", modified_content)

        try:
            ast.parse(modified_content, filename=file_path)
        except SyntaxError as e:
            return False, f"Syntax error after modification: {e}"

        return original_content != modified_content, modified_content

    except Exception as e:
        return False, f"Error: {str(e)}"


def should_process_file(file_path: str) -> bool:
    if "/migrations/" in file_path:
        return False

    if "/node_modules/" in file_path:
        return False

    if "/venv/" in file_path:
        return False

    if "/.venv/" in file_path:
        return False

    return file_path.endswith(".py")


def main():
    if len(sys.argv) < 2:
        print("Usage: python remove_docstrings.py <directory> [--dry-run] [--verbose]")
        sys.exit(1)

    root_dir = sys.argv[1]

    if not os.path.isdir(root_dir):
        print(f"Error: {root_dir} is not a directory")
        sys.exit(1)

    python_files = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ["migrations", "node_modules", "venv", ".venv", "__pycache__", ".git"]]

        for file in files:
            file_path = os.path.join(root, file)
            if should_process_file(file_path):
                python_files.append(file_path)

    print(f"Found {len(python_files)} Python files to process")

    modified_count = 0
    error_count = 0

    for file_path in sorted(python_files):
        was_modified, result = remove_docstrings_from_file(file_path)

        if isinstance(result, str) and not was_modified:
            if VERBOSE:
                print(f"✗ {file_path}: {result}")
            error_count += 1
            continue

        if was_modified:
            modified_count += 1
            if VERBOSE:
                print(f"✓ {file_path}")

            if not DRY_RUN:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(result)

    print("\nSummary:")
    print(f"  Modified: {modified_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total: {len(python_files)}")

    if DRY_RUN:
        print("\nDry-run mode: No files were modified")


if __name__ == "__main__":
    main()
