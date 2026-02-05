import re

with open("site_bundle.js", "r", encoding="utf-8") as f:
    content = f.read()

matches = [m.start() for m in re.finditer(r"/api/attendance", content)]

print(f"Found {len(matches)} occurrences.")

for idx in matches:
    start = max(0, idx - 100)
    end = min(len(content), idx + 200)
    snippet = content[start:end]
    print(f"\n--- MATCH AT {idx} ---")
    print(snippet)
    print("----------------------")
