import typst2latex as t2l

tests = [
    # einfache Ableitungen
    "y'' + p(x) y' + q(x) y = 0",
    # Bruch, Wurzel, Grenzwert-Notation
    "frac(d y, d x) = sqrt(x^2 + 1)",
    # Summen, Integrale mit Grenzen
    "sum_(n=1)^oo 1/n^2 = pi^2/6",
    "integral_0^oo e^(-x t) dif t",
    # Matrix / lineare Systeme
    "dot(x) = mat(1, 2; 3, 4) x + vec(t, t^2)",
    # Fallunterscheidung (Typst-Syntax: Kommas trennen Faelle, & aligniert)
    "f(x) = cases(1 & x < 0, 0 & x >= 0)",
    # Limsup, griechisch, Verktoren
    "lim_(x->oo) (1 + 1/x)^x = e",
    "arrow(nabla) dot arrow(u) = 0",
    # exp / log
    "e^(i pi) + 1 = 0",
]

for src in tests:
    print("TYPST :", src)
    print("LATEX :", t2l.math(src))
    print()

# Dokument-Modus
doc = """= Aufgabe 1
Die DGL $ y'' + y = 0 $ hat die Loesung $ y = C_1 cos x + C_2 sin x $."""
print("DOC-LATEX:")
print(t2l.to_latex(doc, doc=True))
