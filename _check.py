import json
import os
import shutil
import subprocess
import sys

shutil.copy("beispiel.ipynb", "_t.ipynb")
subprocess.run([sys.executable, "typst2latex.py", "build", "_t.ipynb"], capture_output=True, text=True)
nb = json.load(open("_t.ipynb", encoding="utf-8"))
D = "$" * 2
bad = 0
n_md = 0
for c in nb["cells"]:
    if c.get("metadata", {}).get("typst2latex"):
        n_md += 1
        src = "".join(c["source"])
        if src.count(D) % 2 != 0:
            bad += 1
            print("UNGERADE:", src[:80])
assert n_md == 10, n_md
assert bad == 0, bad
print("OK:", n_md, "Markdown-Zellen, alle $$ paarweise")

# KaTeX-Simulation: keine Zeile mit $$ mitten in einem Textabsatz
for c in nb["cells"]:
    if c.get("metadata", {}).get("typst2latex"):
        lines = "".join(c["source"]).splitlines()
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith(D) and i > 0 and lines[i - 1].strip():
                print("PROBLEM: $$-Zeile als Absatz-Fortsetzung:", s[:60])
                bad += 1
assert bad == 0
print("Keine $$-Fortsetzungszeilen mehr - KaTeX-Fehler behoben")
os.remove("_t.ipynb")
