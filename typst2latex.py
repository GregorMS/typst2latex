"""
typst2latex: Offline-Konverter Typst -> LaTeX/Markdown fuer Jupyter Notebooks.

Basiert auf mitgelieferten pandoc-Binaries (kein Internet, keine Installation).

Workflow:
    1. Im Notebook Typst schreiben und ausfuehren:
         %%typst          -> Zelle = Mathe-Schnipsel, wird gerendert
         %%typst --doc    -> Zelle = komplettes Typst-Dokument, wird gerendert
         %%typst --latex  -> LaTeX-Quelltext anzeigen
         %%typst --insert -> zusaetzlich Markdown-Zelle in die .ipynb-Datei einfuegen
    2. AM ENDE (wichtig): Notebook speichern & schliessen, dann im Terminal
         python typst2latex.py build <notebook.ipynb>
       Das fuegt nach jeder %%typst-Zelle eine Markdown-Zelle mit dem gerenderten
       Ergebnis ein. Idempotent (keine Duplikate).

Vorteil: Der Korrektor braucht weder pandoc noch Python. Markdown-Zellen
rendert Jupyter nativ; fehlt pandoc, werden %%typst-Zellen beim Ausfuehren
einfach uebersprungen statt Fehler zu werfen.
"""

from __future__ import annotations

__version__ = "2.0"  # 2.0: build-Befehl (Markdown-Zellen in .ipynb), Skip wenn pandoc fehlt

import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import uuid
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _find_pandoc() -> Path | None:
    """Sucht die passende pandoc-Binary: mitgebracht (dieses Verzeichnis), dann PATH.
    Gibt None zurueck, wenn nichts gefunden -> Skip statt Crash."""
    system = platform.system().lower()          # windows / linux / darwin
    machine = platform.machine().lower()        # x86_64 / amd64 / aarch64 / arm64
    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("aarch64", "arm64"):
        arch = "arm64"
    else:
        arch = None
    suffix = ".exe" if system == "windows" else ""

    candidates = []
    if arch is not None:
        candidates.append(_HERE / f"pandoc-{system}-{arch}{suffix}")
    candidates.append(_HERE / f"pandoc{suffix}")
    for c in candidates:
        if c.exists():
            return c
    found = shutil.which("pandoc")
    if found:
        return Path(found)
    return None


_PANDOC = _find_pandoc()


def _run_pandoc(src: str, from_fmt: str, to_fmt: str = "latex") -> str:
    if _PANDOC is None:
        raise RuntimeError(
            "pandoc nicht gefunden (Skip statt Fehler). "
            "Die gerenderte Version steht in der Markdown-Zelle unter dieser Zelle."
        )
    args = [str(_PANDOC), "-f", from_fmt, "-t", to_fmt]
    try:
        proc = subprocess.run(
            args,
            input=src,
            capture_output=True,
            text=True,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except PermissionError:
        # Exec-Bit ging beim Kopieren verloren (z.B. USB-Stick -> Linux)
        _PANDOC.chmod(_PANDOC.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        proc = subprocess.run(
            args, input=src, capture_output=True, text=True, encoding="utf-8"
        )
    if proc.returncode != 0:
        raise RuntimeError(f"pandoc-Fehler:\n{proc.stderr}")
    return proc.stdout.strip()


def _looks_like_doc(src: str) -> bool:
    """Heuristik: echte Typst-Datei (= Headings, #fu, $..$ inline) vs. nackter Mathe-Schnipsel."""
    stripped = src.strip()
    if stripped.startswith("$") or "$" in stripped:
        return True
    if stripped.startswith("=") and not stripped.startswith("=="):
        return True
    for line in stripped.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return True
    return False


def to_latex(src: str, *, doc: bool | None = None) -> str:
    """
    Konvertiert Typst-Quelltext nach LaTeX.

    doc=False (Default, wenn nicht erkennbar): src ist Mathe-Schnipsel ohne
        $-Delimiter und wird als Display-Math interpretiert.
    doc=True: src ist ein vollstaendiges Typst-Dokument.
    """
    if doc is None:
        doc = _looks_like_doc(src)
    if doc:
        return _run_pandoc(src, "typst")
    return _run_pandoc(f"$ {src.strip()} $", "typst")


def _strip_delims(latex: str) -> str:
    s = latex.strip()
    if s.startswith(r"\[") and s.endswith(r"\]"):
        return s[2:-2].strip()
    if s.startswith("$") and s.endswith("$"):
        return s[1:-1].strip()
    return s


def _markdown_for_jupyter(md: str) -> str:
    """
    pandoc-Markdown schreibt alle Mathe als $...$ (inline) bzw. $$...$$ (display).
    Jupyter rendert $$...$$ immer als zentrierte Display-Formel, daher:
    - ganze Zeile(n) $$...$$  -> bleibt Display-Mathe
    - $$...$$ mitten im Text  -> wird zu $...$ (inline)
    """
    out_lines = []
    in_display = False
    for line in md.splitlines():
        if in_display:
            out_lines.append(line)
            if line.rstrip().endswith("$$"):
                in_display = False
            continue
        stripped = line.strip()
        # Zeile beginnt mit $$: Display-Formel (ein- oder mehrzeilig)?
        if stripped.startswith("$$"):
            prev_empty = not out_lines or not out_lines[-1].strip()
            if prev_empty:
                # eigene Display-Formel -> $$ bleibt
                out_lines.append(line)
                if not stripped.endswith("$$"):
                    in_display = True
                continue
            # Fortsetzung eines Textabsatzes (pandoc trennt Absaetze bei
            # Formeln) -> KaTeX-Verwirrung vermeiden: inline machen
            line = re.sub(r"\$\$([^$]+?)\$\$", r"$\1$", line)
            out_lines.append(line)
            continue
        # Inline-Mathe $$...$$ mitten im Text -> $...$
        line = re.sub(r"\$\$([^$]+?)\$\$", r"$\1$", line)
        out_lines.append(line)
    return "\n".join(out_lines)


def to_markdown(src: str) -> str:
    """
    Konvertiert ein komplettes Typst-Dokument nach Markdown (mit $-Mathematik).
    Rendert Jupyter nativ - funktioniert auch ohne pandoc auf Korrektor-Seite.
    """
    return _markdown_for_jupyter(_run_pandoc(src, "typst", to_fmt="markdown"))


def snippet_markdown(latex: str) -> str:
    """Macht aus einem LaTeX-Schnipsel eine Display-Formel fuer eine Markdown-Zelle."""
    return f"$$\n{_strip_delims(latex)}\n$$"


def to_doc_display(src: str):
    """Konvertiert Typst-Dokument nach Markdown und zeigt es gerendert im Notebook an."""
    from IPython.display import Markdown, display

    display(Markdown(to_markdown(src)))


def display_math(src: str, *, doc: bool = False):
    """Konvertiert und zeigt das Ergebnis direkt im Notebook gerendert an.

    doc=False: Mathe-Schnipsel -> gerenderte Formel.
    doc=True:  Typst-Dokument -> gerendertes Markdown (Headings, Text, Mathe).
    """
    if doc:
        to_doc_display(src)
        return
    from IPython.display import Math, display
    display(Math(_strip_delims(to_latex(src, doc=False))))


def math(src: str) -> str:
    """Kurzform: konvertiert Typst-Mathe-Schnipsel nach LaTeX (String-Rueckgabe)."""
    return to_latex(src, doc=False)


# ------------------------- Notebook-Datei-Bearbeitung -------------------------

_MARKER = "typst2latex"


def _cell_source(cell: dict) -> str:
    src = cell.get("source", "")
    if isinstance(src, list):
        src = "".join(src)
    return src


def _norm(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def _locate_current_cell(nb: dict, cell_text: str) -> int | None:
    """Findet den Index der aktuellen Code-Zelle: erst ueber Zell-ID
    (parent_header, falls verfuegbar), sonst ueber den Zellinhalt."""
    cell_id = None
    try:
        ph = get_ipython().kernel.parent_header  # type: ignore[name-defined]
        meta = ph.get("metadata", {}) or {}
        cell_id = (meta.get("cell") or {}).get("id") or meta.get("cellId")
    except Exception:
        pass
    if cell_id:
        for i, cell in enumerate(nb["cells"]):
            if cell.get("id") == cell_id:
                return i
    # Fallback: Inhalt vergleichen (Magic-Zeile der Notebook-Zelle ignorieren)
    target = _norm(cell_text)
    for i, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") != "code":
            continue
        src = _cell_source(cell)
        if src.lstrip().startswith("%%"):
            src = "\n".join(src.lstrip().splitlines()[1:])
        if _norm(src) == target:
            return i
    return None


def _insert_markdown_after(nb_path: Path, cell_text: str, md_text: str) -> str:
    """Fuegt nach der passenden Code-Zelle eine Markdown-Zelle ein (idempotent)."""
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    idx = _locate_current_cell(nb, cell_text)
    if idx is None:
        return "Zelle nicht im Notebook gefunden - nichts eingefuegt."
    following = nb["cells"][idx + 1] if idx + 1 < len(nb["cells"]) else None
    if following is not None and _cell_source(following).strip() == md_text.strip():
        return "Markdown-Zelle existiert bereits."
    md_cell = {
        "cell_type": "markdown",
        "id": uuid.uuid4().hex[:8],
        "metadata": {_MARKER: __version__},
        "source": md_text,
    }
    nb["cells"].insert(idx + 1, md_cell)
    nb_path.write_text(
        json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return f"Markdown-Zelle eingefuegt nach Zelle {idx + 1} in {nb_path.name}."


def _find_notebook_files() -> list[Path]:
    files: list[Path] = []
    for directory in (Path.cwd(), Path.cwd().parent):
        try:
            files.extend(p for p in directory.glob("*.ipynb") if not p.name.startswith("."))
        except OSError:
            pass
    # Duplikate entfernen, Reihenfolge stabil
    seen = set()
    unique = []
    for p in files:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            unique.append(p)
    return unique


def insert_into_open_notebook(cell_text: str, md_text: str) -> str:
    """Sucht das Notebook der aktuellen Zelle im cwd und fuegt die Markdown-Zelle
    in die erste Datei ein, die die Zelle enthaelt."""
    for nb_path in _find_notebook_files():
        try:
            result = _insert_markdown_after(nb_path, cell_text, md_text)
        except (json.JSONDecodeError, OSError) as e:
            result = f"{nb_path.name}: uebersprungen ({e})"
        if "eingefuegt" in result or "existiert bereits" in result:
            return result
    return "Kein passendes .ipynb im Arbeitsverzeichnis gefunden."


def build(nb_path: str | Path) -> str:
    """
    Konvertiert ALLE %%typst-Zellen eines Notebooks und fuegt nach jeder eine
    Markdown-Zelle mit dem gerenderten Ergebnis ein. Idempotent.
    Nach dem Ausfuehren: Notebook im Editor neu laden (nicht ueberschreiben!).
    """
    nb_path = Path(nb_path)
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    inserted = 0
    skipped = 0
    cells = nb["cells"]
    new_cells = []
    for i, cell in enumerate(cells):
        new_cells.append(cell)
        if cell.get("cell_type") != "code":
            continue
        src = _cell_source(cell)
        if not src.lstrip().startswith("%%typst"):
            continue
        following = cells[i + 1] if i + 1 < len(cells) else None
        if following is not None and following.get("metadata", {}).get(_MARKER):
            continue  # bereits konvertiert
        args = src.lstrip().splitlines()[0].split()[1:]
        doc = "--doc" in args
        body = "\n".join(src.lstrip().splitlines()[1:])
        try:
            if doc:
                md_text = to_markdown(body)
            else:
                md_text = snippet_markdown(to_latex(body, doc=False))
        except RuntimeError as e:
            if "pandoc nicht gefunden" in str(e):
                skipped += 1
                continue
            raise
        md_cell = {
            "cell_type": "markdown",
            "id": uuid.uuid4().hex[:8],
            "metadata": {_MARKER: __version__},
            "source": md_text,
        }
        new_cells.append(md_cell)
        inserted += 1
    nb["cells"] = new_cells
    nb_path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    return f"{inserted} Markdown-Zellen eingefuegt, {skipped} uebersprungen (pandoc fehlt)."


# ---------------------------- IPython Magics ---------------------------------

def _load_ipython_extension(ipython=None):
    from IPython.core.magic import Magics, cell_magic, magics_class

    @magics_class
    class TypstMagics(Magics):
        @cell_magic
        def typst(self, line, cell):
            """%%typst            -> Zelle = Typst-Mathe-Schnipsel, wird gerendert
               %%typst --doc     -> Zelle = komplettes Typst-Dokument, wird gerendert
               %%typst --latex   -> nur LaTeX-Quelltext anzeigen
               %%typst --insert  -> zusaetzlich Markdown-Zelle in die .ipynb einfuegen"""
            args = line.split()
            doc = "--doc" in args
            show_latex = "--latex" in args
            insert = "--insert" in args

            # pandoc fehlt (z.B. Korrektor-Rechner): skip statt Crash
            if _PANDOC is None:
                from IPython.display import Markdown, display
                display(Markdown(
                    "> **Hinweis:** `pandoc` nicht gefunden - Typst-Zelle uebersprungen. "
                    "Die gerenderte Version steht in der Markdown-Zelle unter dieser Zelle."
                ))
                return None

            try:
                if doc and not show_latex:
                    md_text = to_markdown(cell)
                    to_doc_display(cell)
                else:
                    latex = to_latex(cell, doc=doc)
                    if show_latex:
                        print(latex)
                    else:
                        from IPython.display import Math, display
                        display(Math(_strip_delims(latex)))
                    md_text = snippet_markdown(latex)
            except RuntimeError as e:
                if "pandoc nicht gefunden" in str(e):
                    from IPython.display import Markdown, display
                    display(Markdown(f"> **Hinweis:** {e}"))
                    return None
                raise

            if insert:
                print(insert_into_open_notebook(cell, md_text))
            return None

    ipython = ipython or get_ipython()
    ipython.register_magics(TypstMagics)


try:
    _load_ipython_extension()
except Exception:
    pass  # nicht in IPython-Umgebung (z.B. normaler python-Lauf)


if __name__ == "__main__":
    import argparse

    argv = [a for a in sys.argv[1:] if a != "build"]  # "build" optional erlauben
    parser = argparse.ArgumentParser(
        description="Fuegt nach jeder %%typst-Zelle eines Notebooks eine gerenderte "
                    "Markdown-Zelle ein (fuer Abgabe ohne pandoc/python). "
                    "Aufruf: python typst2latex.py build <notebook.ipynb>"
    )
    parser.add_argument("notebook", help="Pfad zur .ipynb-Datei")
    ns = parser.parse_args(argv)
    print(build(ns.notebook))
