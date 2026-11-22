# pdfly

A small Python command-line app for everyday PDF tasks. Merge documents, split a PDF into pages or ranges, extract the pages you need, and check document information. Everything runs locally on your computer.

**Try the web version:** https://ninjacodes777.github.io/pdfly/

## Features

- Merge multiple PDFs in the order you choose
- Split a PDF into one file per page, or one file per page range
- Extract selected pages into a new PDF, including custom ordering
- Show page count, file size and document metadata
- Clear error messages for missing files and invalid page selections
- Refuses to overwrite existing files or replace your input PDFs
- Commented Python code with one function for each command

## Web version

The `docs/` folder holds a single-page web app (plain HTML/CSS/JS, no build
step) with the same merge, split, extract and info tools, hosted on GitHub
Pages:

https://ninjacodes777.github.io/pdfly/

It works in a phone browser and runs entirely on your device using the
[pdf-lib](https://pdf-lib.js.org/) library from a CDN - your PDFs are never
uploaded anywhere.

## Requirements

- Python 3.10+
- **pypdf** (an external package, not part of Python's standard library)

## Installation

Download this repository using GitHub's **Code > Download ZIP** button and extract it, or clone it with Git:

```bash
git clone https://github.com/ninjacodes777/pdfly.git
cd pdfly
python -m pip install -r requirements.txt
```

If your system uses `python3` instead of `python`, replace `python` in the commands below with `python3`. A virtual environment is recommended:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Use the activation command for your own system, not both.

## Usage

Open a terminal in the project folder. These examples assume you have your own PDFs named `notes.pdf` and `exercises.pdf` in that folder. Sample PDFs are not included.

### See all commands

```bash
python pdfly.py --help
python pdfly.py split --help
```

### Merge PDFs

```bash
python pdfly.py merge notes.pdf exercises.pdf -o combined.pdf
```

The pages from `notes.pdf` come first, then the pages from `exercises.pdf`. You can pass more than two input files.

### Split into separate pages

```bash
python pdfly.py split combined.pdf -d pages
```

Creates the output folder if needed, then writes `combined_001.pdf`, `combined_002.pdf`, and so on.

### Split into page ranges

For a PDF with at least five pages:

```bash
python pdfly.py split combined.pdf -d chapters --ranges "1-2,3-5"
```

Writes two PDFs: `combined_001.pdf` contains pages 1-2 and `combined_002.pdf` contains pages 3-5. Each comma-separated item becomes one output file.

### Extract specific pages

```bash
python pdfly.py extract combined.pdf --pages "1,3-5" -o selected.pdf
```

Page numbers start at **1**, not 0. Ranges include both ends. Selected pages stay in the order you type, and repeated pages are allowed:

```bash
python pdfly.py extract combined.pdf --pages "5,1,1" -o reordered.pdf
```

This produces a three-page PDF containing page 5, then page 1 twice.

### Show PDF information

```bash
python pdfly.py info combined.pdf
```

Shows page count, file size and available title, author, subject, creator and producer metadata. Missing metadata is shown as `(not set)`.

Quote filenames containing spaces, for example `"lecture notes.pdf"`.

## How it works

1. `argparse` reads the command and options from your terminal.
2. `pathlib` handles filenames and checks output locations.
3. `pypdf.PdfReader` opens each input document.
4. Page selections such as `1,3-5` are checked and converted into zero-based Python indexes.
5. `pypdf.PdfWriter` combines or copies the selected pages into new PDFs.

Input files stay open until writing is complete. Output files are created in exclusive mode, so an existing file is never silently replaced. The source PDFs are not modified.

## Notes and limitations

- Encrypted/password-protected PDFs are not supported.
- This is a terminal app, not a web app or a graphical PDF editor.
- Extract copies whole pages; it does not extract text or perform OCR.
- Merging uses pypdf's document append operation. Splitting and extracting copy pages, not every document-level feature such as outlines or metadata.
- Editing a digitally signed PDF may invalidate its signature. Keep the original.
- Large PDFs may need significant memory.
- For merge/extract, create the output's parent folder first. Split creates its output folder automatically.
- If an output name already exists, choose another name or move the old output yourself.
- A disk or permission error partway through a split can leave earlier completed outputs in place.

## Run the tests

```bash
python -m unittest -v
```

The tests create temporary PDFs, run the real CLI, and check page counts, page order and common error cases. Temporary PDFs are removed automatically.
