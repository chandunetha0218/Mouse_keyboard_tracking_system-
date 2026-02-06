import re

with open("site_bundle.js", "r", encoding="utf-8") as f:
    content = f.read()

# Search for "punch-in"
matches = [m.start() for m in re.finditer(r"punch-in", content)]

print(f"Found {len(matches)} occurrences of 'punch-in'.")

for idx in matches:
    start = max(0, idx - 400)
    end = min(len(content), idx + 600)
    snippet = content[start:end]
    print(f"\n--- MATCH AT {idx} ---")
    print(snippet)
    print("----------------------")
