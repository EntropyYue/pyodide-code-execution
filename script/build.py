import os
import re
import sys


def extract_replace_block(source_path):
    if not os.path.exists(source_path) or not os.path.isfile(source_path):
        return None, f"Source file does not exist: {source_path}"

    lines = []
    in_block = False
    with open(source_path, "r", encoding="utf-8") as f:
        for line in f:
            if not in_block:
                if "[replace begin]" in line:
                    in_block = True
                    continue
            else:
                if "[replace end]" in line:
                    return "\n".join(lines), None
                lines.append(line.rstrip("\n"))
    if in_block:
        return (
            None,
            f"Found [replace begin] in {source_path} but no [replace end] found",
        )
    return None, f"No [replace begin] block found in {source_path}"


def main():
    target_file = "src/main.py"

    if not os.path.exists(target_file):
        print(f"Target file does not exist: {target_file}")
        sys.exit(1)

    text = open("src/main.py", "r", encoding="utf-8").read()

    pattern = re.compile(r"\{\{\s*(.+?)\s*\}\}")

    warnings = []

    def repl(m):
        filename = m.group(1).strip()
        source_path = filename

        replace_content, err = extract_replace_block(source_path)
        if err:
            warnings.append(err + f" (placeholder: {{{{{filename}}}}})")
            return m.group(0)

        if not replace_content:
            warnings.append(
                f"No content to replace for placeholder: {{{{{filename}}}}}"
            )
            return m.group(0)

        start_idx = m.start()
        line_start = text.rfind("\n", 0, start_idx)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1
        leading = text[line_start:start_idx]
        indent_match = re.match(r"[ \t]*", leading)
        indent = indent_match.group(0) if indent_match else ""

        replaced_lines = []
        for ln in replace_content.split("\n"):
            if ln.strip() == "":
                replaced_lines.append("")
            else:
                replaced_lines.append(indent + ln)
        return "\n".join(replaced_lines).strip()

    new_text = pattern.sub(repl, text)

    os.makedirs("dist", exist_ok=True)
    with open("dist/plugin.py", "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"Processing completed: {target_file}")
    if warnings:
        print("Warnings (placeholders not replaced):")
        for w in warnings:
            print(" -", w)


if __name__ == "__main__":
    main()
