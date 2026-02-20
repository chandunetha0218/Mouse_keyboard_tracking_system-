
filename = r"c:\Users\sagar\Downloads\mouse_tracking\Mouse_keyboard_tracking_system-\main.py"

with open(filename, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines[:200]): # Inspect first 200 lines carefully
    stripped = line.lstrip()
    if not stripped: continue
    indent = len(line) - len(stripped)
    # Check if indent is multiple of 4
    if indent % 4 != 0:
        print(f"Line {i+1}: Indent {indent} (NOT MULTIPLE OF 4!) -> {stripped.strip()[:40]}...")
    else:
        # print(f"Line {i+1}: Indent {indent}")
        pass

print("--- Checking Class Structure ---")
# Check defs
for i, line in enumerate(lines):
    if line.strip().startswith("def "):
        indent = len(line) - len(line.lstrip())
        print(f"Line {i+1}: def at indent {indent}: {line.strip()[:40]}...")
