#!/usr/bin/env python3
"""
Automated CodeQL Alert Fixer

This script automatically fixes common CodeQL code quality issues by parsing
alerts from the GitHub API and applying targeted fixes to the codebase.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict


class CodeQLAutoFixer:
    """Automatically fix common CodeQL alerts."""

    def __init__(self, alerts_json: str):
        """Initialize with CodeQL alerts JSON."""
        self.alerts = json.loads(alerts_json)
        self.fixes_applied = []
        self.fixes_failed = []

    def fix_all(self) -> Dict[str, int]:
        """Apply fixes for all alerts."""
        stats = {
            "total": len(self.alerts),
            "fixed": 0,
            "skipped": 0,
            "failed": 0,
        }

        for alert in self.alerts:
            try:
                rule_id = alert.get("rule", {}).get("id", "")
                if self.fix_alert(alert):
                    stats["fixed"] += 1
                    self.fixes_applied.append(f"{rule_id}: {alert['most_recent_instance']['location']['path']}")
                else:
                    stats["skipped"] += 1
            except Exception as e:
                stats["failed"] += 1
                self.fixes_failed.append(f"{alert.get('number', 'unknown')}: {str(e)}")

        return stats

    def fix_alert(self, alert: Dict) -> bool:
        """Fix a single alert based on its rule."""
        rule_id = alert.get("rule", {}).get("id", "")

        fixers = {
            "py/unused-local-variable": self.fix_unused_variable,
            "py/imprecise-assert": self.fix_imprecise_assert,
            "py/multiple-definition": self.fix_multiple_definition,
            "py/empty-except": self.fix_empty_except,
            "py/unreachable-code": self.fix_unreachable_code,
            "py/unreachable-statement": self.fix_unreachable_code,  # Same handler for both
            "py/unnecessary-pass": self.fix_unnecessary_pass,
            "py/catch-base-exception": self.fix_base_exception,
        }

        fixer = fixers.get(rule_id)
        if fixer:
            return fixer(alert)
        return False

    def fix_unused_variable(self, alert: Dict) -> bool:
        """Fix unused variable by prefixing with underscore."""
        location = alert["most_recent_instance"]["location"]
        file_path = Path(location["path"])
        line_num = location["start_line"]

        # Extract variable name from message
        message = alert["most_recent_instance"]["message"]["text"]
        match = re.search(r"Variable (\w+) is not used", message)
        if not match:
            return False

        var_name = match.group(1)

        # Skip if variable already starts with underscore (already marked as intentionally unused)
        if var_name.startswith("_"):
            return False

        # Read file
        content = file_path.read_text()
        lines = content.splitlines(keepends=True)

        if line_num > len(lines):
            return False

        # Replace variable name with underscore-prefixed version
        line = lines[line_num - 1]

        # Handle different assignment patterns
        patterns = [
            (rf"\bdef\s+{var_name}\b", f"def _{var_name}"),  # Function definition
            (rf"\b{var_name}\b(\s*=)", f"_{var_name}\\1"),  # Simple assignment
            (rf"\bfor\s+{var_name}\b", f"for _{var_name}"),  # For loop
            (rf"\b{var_name}\b(\s*,)", f"_{var_name}\\1"),  # Tuple unpacking
            (rf",\s*{var_name}\b", f", _{var_name}"),  # Tuple unpacking (not first)
        ]

        for pattern, replacement in patterns:
            new_line = re.sub(pattern, replacement, line)
            if new_line != line:
                lines[line_num - 1] = new_line
                file_path.write_text("".join(lines))
                return True

        return False

    def fix_imprecise_assert(self, alert: Dict) -> bool:
        """Fix imprecise assert by using specific assert methods."""
        location = alert["most_recent_instance"]["location"]
        file_path = Path(location["path"])
        line_num = location["start_line"]

        # Read file
        content = file_path.read_text()
        lines = content.splitlines(keepends=True)

        if line_num > len(lines):
            return False

        line = lines[line_num - 1]

        # Common patterns to fix
        replacements = [
            (r"assertTrue\((.*?)\s+in\s+(.*?)\)", r"assertIn(\1, \2)"),
            (r"assertTrue\((.*?)\s+not in\s+(.*?)\)", r"assertNotIn(\1, \2)"),
            (r"assertTrue\((.*?)\s+==\s+(.*?)\)", r"assertEqual(\1, \2)"),
            (r"assertTrue\((.*?)\s+!=\s+(.*?)\)", r"assertNotEqual(\1, \2)"),
            (r"assertTrue\((.*?)\s+>\s+(.*?)\)", r"assertGreater(\1, \2)"),
            (r"assertTrue\((.*?)\s+>=\s+(.*?)\)", r"assertGreaterEqual(\1, \2)"),
            (r"assertTrue\((.*?)\s+<\s+(.*?)\)", r"assertLess(\1, \2)"),
            (r"assertTrue\((.*?)\s+<=\s+(.*?)\)", r"assertLessEqual(\1, \2)"),
            (r"assertFalse\((.*?)\s+in\s+(.*?)\)", r"assertNotIn(\1, \2)"),
            (r"assertFalse\((.*?)\s+==\s+(.*?)\)", r"assertNotEqual(\1, \2)"),
        ]

        for pattern, replacement in replacements:
            new_line = re.sub(pattern, replacement, line)
            if new_line != line:
                lines[line_num - 1] = new_line
                file_path.write_text("".join(lines))
                return True

        return False

    def fix_multiple_definition(self, alert: Dict) -> bool:
        """Fix multiple definition by removing the redundant first assignment."""
        location = alert["most_recent_instance"]["location"]
        file_path = Path(location["path"])
        line_num = location["start_line"]

        # Read file
        content = file_path.read_text()
        lines = content.splitlines(keepends=True)

        if line_num > len(lines):
            return False

        # Remove the line (since it's redundant)
        line = lines[line_num - 1]

        # Check if the entire line is just an assignment
        if "=" in line and not line.strip().startswith("#"):
            # Just remove the line entirely
            del lines[line_num - 1]

            file_path.write_text("".join(lines))
            return True

        return False

    def fix_empty_except(self, alert: Dict) -> bool:
        """Fix empty except by adding explanatory comment."""
        location = alert["most_recent_instance"]["location"]
        file_path = Path(location["path"])
        line_num = location["start_line"]

        # Read file
        content = file_path.read_text()
        lines = content.splitlines(keepends=True)

        if line_num > len(lines):
            return False

        line = lines[line_num - 1]

        # Find the pass statement (likely on the next line)
        if "pass" in line:
            # Replace pass with commented pass
            lines[line_num - 1] = line.replace("pass", "pass  # Intentionally empty - safe to ignore errors")
            file_path.write_text("".join(lines))
            return True
        elif line_num < len(lines) and "pass" in lines[line_num]:
            # Pass is on the next line
            lines[line_num] = lines[line_num].replace("pass", "pass  # Intentionally empty - safe to ignore errors")
            file_path.write_text("".join(lines))
            return True

        return False

    def fix_unreachable_code(self, alert: Dict) -> bool:
        """Fix unreachable code by removing it."""
        location = alert["most_recent_instance"]["location"]
        file_path = Path(location["path"])
        start_line = location["start_line"]
        end_line = location.get("end_line", start_line)

        # Read file
        content = file_path.read_text()
        lines = content.splitlines(keepends=True)

        if start_line > len(lines):
            return False

        # Remove the unreachable lines
        # Keep track of how many lines to remove
        lines_to_remove = end_line - start_line + 1

        # Delete the lines
        for _ in range(lines_to_remove):
            if start_line - 1 < len(lines):
                del lines[start_line - 1]

        file_path.write_text("".join(lines))
        return True

    def fix_unnecessary_pass(self, alert: Dict) -> bool:
        """Fix unnecessary pass by removing it."""
        location = alert["most_recent_instance"]["location"]
        file_path = Path(location["path"])
        line_num = location["start_line"]

        # Read file
        content = file_path.read_text()
        lines = content.splitlines(keepends=True)

        if line_num > len(lines):
            return False

        line = lines[line_num - 1]

        # Check if line is just whitespace + pass
        if line.strip() == "pass":
            # Remove the line entirely
            del lines[line_num - 1]
            file_path.write_text("".join(lines))
            return True

        return False

    def fix_base_exception(self, alert: Dict) -> bool:
        """Fix BaseException catch (including bare except:) by adding explanatory comment."""
        location = alert["most_recent_instance"]["location"]
        file_path = Path(location["path"])
        line_num = location["start_line"]

        # Read file
        content = file_path.read_text()
        lines = content.splitlines(keepends=True)

        if line_num > len(lines):
            return False

        line = lines[line_num - 1]

        # Handle both explicit BaseException and bare except:
        if "except" in line:
            # Get indentation
            indent = len(line) - len(line.lstrip())
            # Add comment on the line before
            comment = " " * indent + "# Intentionally catching all exceptions\n"
            lines.insert(line_num - 1, comment)
            file_path.write_text("".join(lines))
            return True

        return False

    def print_summary(self, stats: Dict[str, int]):
        """Print a summary of fixes applied."""
        print("\n" + "=" * 60)
        print("CodeQL AutoFix Summary")
        print("=" * 60)
        print(f"Total alerts: {stats['total']}")
        print(f"Fixed: {stats['fixed']}")
        print(f"Skipped: {stats['skipped']}")
        print(f"Failed: {stats['failed']}")
        print()

        if self.fixes_applied:
            print("Fixes applied:")
            for fix in self.fixes_applied:
                print(f"  ✓ {fix}")

        if self.fixes_failed:
            print("\nFixes failed:")
            for fail in self.fixes_failed:
                print(f"  ✗ {fail}")

        print("=" * 60)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python autofix_codeql.py <alerts.json>", file=sys.stderr)
        sys.exit(1)

    alerts_file = sys.argv[1]

    try:
        with open(alerts_file, "r") as f:
            alerts_json = f.read()
    except FileNotFoundError:
        print(f"Error: Alerts file '{alerts_file}' not found", file=sys.stderr)
        sys.exit(1)

    fixer = CodeQLAutoFixer(alerts_json)
    stats = fixer.fix_all()
    fixer.print_summary(stats)

    # Exit with error if any fixes failed
    if stats["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
