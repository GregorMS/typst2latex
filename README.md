# typst2latex – Offline-Konverter für die DGL-Klausur

Schreibt Mathe in **Typst**-Syntax, rendert es im Jupyter-Notebook als LaTeX.
Läuft **komplett offline** – es wird nur pandoc als Binary in diesem Ordner
gebraucht (siehe unten, wie man sie bekommt).

## Enthaltene Dateien

| Datei | Zweck |
| --- | --- |
| `typst2latex.py` | Der Wrapper (Import im Notebook) |
| `test_typst2latex.py` | Selbsttest |
| `pandoc-*-…` | pandoc-Binaries (nicht im Repo, selbst herunterladen – siehe nächster Abschnitt) |

## pandoc-Binaries herunterladen

Die pandoc-Binaries sind zu groß für GitHub (>100 MB) und liegen deshalb
**nicht im Repo**. Sie müssen einmalig in diesen Ordner gelegt werden:

1. Gewünschte Architektur auf der VM prüfen: `uname -m`
   (`x86_64` → amd64, `aarch64` → arm64; unter Windows immer amd64)
2. Von <https://github.com/jgm/pandoc/releases> die Datei
   `pandoc-<ver>-linux-<arch>.tar.gz` (bzw. für Windows
   `pandoc-<ver>-windows-amd64.zip`) herunterladen
3. Entpacken und die Binary `bin/pandoc` in diesen Ordner legen, umbenannt:
   - `pandoc-linux-amd64` (Linux x86_64 – vermutlich das richtige für die VM)
   - `pandoc-linux-arm64` (Linux ARM64)
   - `pandoc-windows-amd64.exe` (Windows)

Die Dateinamen sind wichtig – der Wrapper sucht genau nach diesen.

Der Wrapper sucht automatisch die passende Binary für das laufende System
(Windows/Linux, amd64/arm64). Fehlt das Exec-Bit (z. B. nach USB-Kopie unter
Linux), setzt es es automatisch wieder.

## Einrichtung auf der VM (einmalig, vor der Klausur testen!)

1. Diesen Ordner komplett aufs VM-Home kopieren (z. B. per `scp`, USB, oder
   hochladen und herunterladen – je nachdem, wie man Dateien aufs VM bringt).
2. Terminal, im Ordner:

   ```bash
   chmod +x pandoc-linux-*    # Ausführbar machen (falls nötig)
   python3 test_typst2latex.py   # Selbsttest muss ohne Fehler durchlaufen
   ```

3. Im Jupyter-Notebook muss der Ordner erreichbar sein. Einfachster Weg:
   `typst2latex.py` in denselben Ordner legen wie das Notebook, oder
   `sys.path.insert(0, "/pfad/zu/typst2latex")` vor dem Import.

**Wichtig:** Im Notebook immer so importieren (verhindert veraltete Modulversionen):

```python
import typst2latex as t2l, importlib
importlib.reload(t2l)
print(t2l.__version__)  # 2.0 oder hoeher erwartet
```

## Verwendung im Notebook

```python
import typst2latex as t2l
```

**Formel-Schnipsel konvertieren und rendern:**

```python
t2l.math("y'' + p(x) y' + q(x) y = 0")          # -> LaTeX-String
t2l.display_math("frac(d y, d x) = sqrt(x^2+1)") # -> gerendert im Output
```

**Als Cell-Magic (empfohlen, fühlt sich wie Typst an):**

```
%%typst
y'' + p(x) y' + q(x) y = 0
```

- `%%typst` → Zelle ist ein Mathe-Schnipsel, wird gerendert
- `%%typst --latex` → nur den LaTeX-Quelltext ausgeben
- `%%typst --doc` → Zelle ist ein komplettes Typst-Dokument (auch
  Überschriften mit `=`, Text, Inline-Mathe mit `$ ... $`); wird direkt
  **gerendert** als Markdown angezeigt (Überschriften, Text, Formeln)
- `%%typst --doc --latex` → Dokument, aber LaTeX-Quelltext statt Renderung
- `%%typst --insert` → zusätzlich Markdown-Zelle in die .ipynb-Datei einfügen
  (danach Notebook im Editor neu laden, nicht einfach weiterbearbeiten!)

## Abgabe-Workflow (wichtig!)

Damit der Korrektor alles **ohne pandoc und ohne Python** sieht, müssen die
gerenderten Ergebnisse als Markdown-Zellen in der .ipynb-Datei stehen
(Jupyter rendert Markdown nativ):

1. Notebook **speichern und schließen**
2. Im Terminal im Notebook-Ordner:
   ```bash
   python3 typst2latex.py build <notebook>.ipynb
   ```
   Fügt nach jeder `%%typst`-Zelle eine Markdown-Zelle mit dem gerenderten
   Ergebnis ein. Idempotent (keine Duplikate bei erneutem Ausführen).
3. Notebook neu öffnen und kurz kontrollieren.

Verhalten ohne pandoc (z. B. Korrektor macht „Run All"): `import typst2latex`
crasht nicht, `%%typst`-Zellen werden mit Hinweis **übersprungen** – die
Markdown-Zellen bleiben erhalten und rendern weiterhin.

## Typst-Syntax-Spickzettel (für die Klausur)

| Typst | LaTeX-Ergebnis |
| --- | --- |
| `x^2`, `x_1` | Exponent / Index |
| `frac(a, b)` oder `a/b` | Bruch |
| `sqrt(x)`, `sqrt(n, x)` | Wurzel / n-te Wurzel |
| `sum_(k=1)^n`, `integral_0^oo` | Summe / Integral |
| `lim_(x->oo)` | Limes |
| `dot(x)`, `dot.op(x)` | Ableitung `ẋ` |
| `y''` | zweite Ableitung |
| `dif x` | Differenzial `dx` (aufrecht) |
| `mat(1, 2; 3, 4)` | Matrix (Spalten mit `,`, Zeilen mit `;`) |
| `vec(a, b)` | Spaltenvektor |
| `cases(1 & x < 0, 0 & x >= 0)` | Fallunterscheidung (`,` trennt Fälle, `&` aligned) |
| `arrow(v)`, `tilde(x)`, `hat(x)` | Vektorpfeil etc. |
| `alpha beta gamma pi theta oo` | Griechisch, `oo` = ∞ |
| `in`, `subset`, `times`, `dot.c`, `cross` | Mengen/Produkte |
| `e^(i pi)`, `e^(-x t)` | Exponential |

Achtung: In `mat(...)` trennt `;` die Zeilen, in `cases(...)` trennen `,` die
Fälle – nicht vertauschen.

## Bekannte pandoc-Einschränkungen

- Sehr exotische Typst-Funktionen (`fmt!`, `pad`, `grid` …) werden evtl.
  nicht unterstützt → im Zweifel Formel einfacher schreiben.
- Im Schnipsel-Modus wird die ganze Zelle als eine Formel interpretiert.
- Bei Fehlermeldung `pandoc-Fehler: ...` steht die pandoc-Fehlermeldung im
  Traceback – meist ein Tippfehler in der Syntax.

## falls pandoc gar nicht läuft

Falls die VM-Architektur anders ist als mitgebracht: `uname -m` auf der VM
prüfen und die passende Binary gemäß Abschnitt „pandoc-Binaries
herunterladen" von <https://github.com/jgm/pandoc/releases> herunterladen
(Datei `pandoc-<ver>-linux-<arch>.tar.gz`, darin `bin/pandoc`) und in diesen
Ordner legen als `pandoc-linux-<arch>`.
