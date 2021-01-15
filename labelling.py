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
import os.path
import pathlib
import subprocess

import PyPDF2

import stylesheet

LATEX_CODE = """
\\documentclass[12pt, border=0mm, crop=true]{{standalone}}
\\usepackage{{amsfonts}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\usepackage{{unicode-math}}
\\usepackage{{xcolor}}
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
    filename = stylesheet.full_path(INDEX_FILENAME)
    with open(filename, "w") as f:
        json.dump(index, f)


def read_index():
    filename = stylesheet.full_path(INDEX_FILENAME)
    if not pathlib.Path(filename).exists():
        write_index({})
    with open(filename, "r") as f:
        return json.load(f)


def create(contents, labels):
    if contents in labels:
        raise RuntimeError()
    basename = "label" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = stylesheet.full_path(basename + ".tex")
    with open(filename, "w") as f:
        f.write(LATEX_CODE.format(contents))
    subprocess.run([XELATEX_COMMAND, basename + ".tex"], cwd=stylesheet.full_path(""))
    labels[contents] = basename
    write_index(labels)
    return basename


class Label:
    def __init__(self, contents, position, anchor, y_upwards=True):
        self.contents = contents
        self.position = position
        self.anchor = anchor
        self.y_upwards = y_upwards

    @property
    def basename(self):
        labels = read_index()
        if not self.contents in labels:
            create(self.contents, labels)
        return labels[self.contents]

    def insert(self, page):
        filename = stylesheet.full_path(self.basename + ".pdf")
        label = PyPDF2.PdfFileReader(filename).getPage(0)
        x1, y1, x2, y2 = [float(x) for x in label.mediaBox]
        x, y = self.position
        if not self.y_upwards:
            y = float(page.mediaBox[3]) - float(page.mediaBox[1]) - y
        x -= self.anchor[0] * (x2 - x1)
        y -= self.anchor[1] * (y2 - y1)
        page.mergeTranslatedPage(label, x, y)


def label_json_formatter(o):
    if isinstance(o, Label):
        return {
            "contents": o.contents,
            "position": o.position,
            "anchor": o.anchor,
            "y_upwards": o.y_upwards,
        }
    else:
        raise TypeError()


def insert_labels(basename, labels):
    filename = stylesheet.full_path(basename + "-bare.pdf")
    page = PyPDF2.PdfFileReader(filename).getPage(0)
    for label in labels:
        label.insert(page)
    writer = PyPDF2.PdfFileWriter()
    writer.addPage(page)
    filename = stylesheet.full_path(basename + ".pdf")
    with open(filename, "wb") as f:
        writer.write(f)
