"""
This module is used to generate and retrieve labels for the figures.

Each label is a standalone XeLaTeX file, named

    label<timestamp>.tex

XeLaTeX is run automatically to generate the PDF. Then PyPDF2 is used
to insert the label at the desired place.

The generated labels are indexed in a JSON file called labels.json.
The syntax is

    {
        "XeLaTeX contents": basename
    }

When a non-existing label is required, it is first automatically
generated.

Note that importing this module actually does pre-generate some labels
(if necessary).
"""
import datetime
import json
import pathlib
import subprocess

import PyPDF2

LATEX_CODE = """
\\documentclass[12pt, border=0mm, crop=true]{{standalone}}
\\usepackage{{amsfonts}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\usepackage{{unicode-math}}
\\setmainfont{{XITS}}
\\setmathfont{{XITS Math}}
\\AtBeginDocument{{
  \\newcommand{{\\point}}[1]{{\\symsf{{#1}}}}
  \\newcommand{{\\tens}}[1]{{\\symbfsf{{#1}}}}
  \\renewcommand{{\\vec}}[1]{{\\symbf{{#1}}}}}}
\\begin{{document}}
    {}
\\end{{document}}
"""

XELATEX_COMMAND = "xelatex"

INDEX_FILENAME = "labels.json"


def write_index(index):
    with open(INDEX_FILENAME, "w") as f:
        json.dump(index, f)


def read_index():
    if not pathlib.Path(INDEX_FILENAME).exists():
        write_index({})
    with open(INDEX_FILENAME, "r") as f:
        return json.load(f)


def create(contents, labels):
    if contents in labels:
        raise RuntimeError()
    basename = "label" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    with open(basename + ".tex", "w") as f:
        f.write(LATEX_CODE.format(contents))
    subprocess.run([XELATEX_COMMAND, basename + ".tex"])
    labels[contents] = basename
    write_index(labels)
    return basename


def basename(contents):
    labels = read_index()
    if not contents in labels:
        create(contents, labels)
    return labels[contents]


def insert(latex, page, position, anchor):
    label = PyPDF2.PdfFileReader(basename(latex) + ".pdf").getPage(0)
    x1, y1, x2, y2 = [float(x) for x in label.mediaBox]
    dx = anchor[0] * (x2 - x1)
    dy = anchor[1] * (y2 - y1)
    x, y = position
    page.mergeTranslatedPage(label, x - dx, y - dy)


# Initialization code, to be executed each time the module is loaded
basename(r"\(\Lambda(\Gamma)\)")
basename(r"\(\Omega\)")

# if __name__ == "__main__":
#     mm = 72.0 / 25.4
#     page = PyPDF2.PdfFileReader("fig20210105175723-bare.pdf").getPage(0)
#
#     x0 = 0.5 * float(page.mediaBox[0] + page.mediaBox[2])
#     y0 = 0.5 * float(page.mediaBox[1] + page.mediaBox[3])
#
#     position = (x0 - 9.330127018922193 * mm, y0 + 20.570737201667704 * mm)
#     anchor = (1.0, 0.0)
#     insert(r"\(\Omega\)", page, position, anchor)
#
#     writer = PyPDF2.PdfFileWriter()
#     writer.addPage(page)
#     with open("test.pdf", "wb") as f:
#         writer.write(f)
