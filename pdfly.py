#!/usr/bin/env python3
"""pdfly: small, local PDF tools. Run `python pdfly.py --help` to start."""

import argparse
from contextlib import ExitStack
from pathlib import Path
import re
import sys

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.errors import PyPdfError
except ImportError:
    sys.exit("Missing dependency: run python -m pip install -r requirements.txt")


def page_numbers(selection, total):
    """Turn a 1-based selection like '1,3-5' into ordered 0-based indexes."""
    indexes = []
    for part in selection.split(","):
        part = part.strip()
        if not re.fullmatch(r"[0-9]+(?:\s*-\s*[0-9]+)?", part):
            raise ValueError("Use page numbers or ranges, for example: 1,3-5")
        bounds = [int(number.strip()) for number in part.split("-")]
        start, end = bounds[0], bounds[-1]
        if start < 1 or end > total or start > end:
            raise ValueError(f"Invalid range '{part}': use pages 1-{total}, ascending.")
        # Keep the supplied order. Repeated pages are allowed intentionally.
        indexes.extend(range(start - 1, end))
    return indexes


def open_pdf(stack, path):
    """Keep the input open until pypdf has finished reading its pages."""
    stream = stack.enter_context(path.open("rb"))
    reader = PdfReader(stream)
    if reader.is_encrypted:
        raise ValueError(f"Encrypted PDF is not supported: {path}")
    if not reader.pages:
        raise ValueError(f"PDF has no pages: {path}")
    return reader


def check_outputs(paths, inputs):
    """Refuse existing files and input/output collisions, even through symlinks."""
    resolved_inputs = {path.resolve() for path in inputs}
    resolved_outputs = [path.resolve() for path in paths]
    if len(set(resolved_outputs)) != len(paths):
        raise ValueError("Output filenames must be different.")
    for path, resolved in zip(paths, resolved_outputs):
        if resolved in resolved_inputs:
            raise ValueError(f"Output cannot replace an input PDF: {path}")
        if path.exists() or path.is_symlink():
            raise ValueError(f"Output already exists: {path}. Choose a new name.")
        if not path.parent.is_dir():
            raise ValueError(f"Output folder does not exist: {path.parent}")


def save_pdf(writer, path):
    """Exclusive creation prevents accidentally overwriting an existing file."""
    created = False
    try:
        with path.open("xb") as output:
            created = True
            writer.write(output)
    except Exception:
        # Remove only a partial file created by this call, never another file.
        if created:
            path.unlink(missing_ok=True)
        raise
    finally:
        writer.close()


def merge(args):
    check_outputs([args.output], args.inputs)
    with ExitStack() as stack:
        readers = [open_pdf(stack, path) for path in args.inputs]
        writer = PdfWriter()
        for reader in readers:
            writer.append(reader)
        count = len(writer.pages)
        save_pdf(writer, args.output)
    print(f"Merged {len(args.inputs)} PDFs -> {args.output} ({count} pages)")


def extract(args):
    check_outputs([args.output], [args.input])
    with ExitStack() as stack:
        reader = open_pdf(stack, args.input)
        indexes = page_numbers(args.pages, len(reader.pages))
        writer = PdfWriter()
        for index in indexes:
            writer.add_page(reader.pages[index])
        save_pdf(writer, args.output)
    print(f"Extracted {len(indexes)} pages -> {args.output}")


def split(args):
    with ExitStack() as stack:
        reader = open_pdf(stack, args.input)
        total = len(reader.pages)
        # Without --ranges, each page becomes a separate PDF. Each comma-separated
        # range otherwise becomes one output: '1-3,4-6' produces two PDFs.
        groups = ([page_numbers(part, total) for part in args.ranges.split(",")]
                  if args.ranges else [[index] for index in range(total)])
        directory = args.output_dir
        if directory.exists() and not directory.is_dir():
            raise ValueError(f"Not a folder: {directory}")
        directory.mkdir(parents=True, exist_ok=True)
        outputs = [directory / f"{args.input.stem}_{number:03d}.pdf"
                   for number in range(1, len(groups) + 1)]
        # Check all names before writing anything to avoid partial splits on a
        # predictable filename conflict. I/O failures can still leave prior files.
        check_outputs(outputs, [args.input])
        for indexes, output in zip(groups, outputs):
            writer = PdfWriter()
            for index in indexes:
                writer.add_page(reader.pages[index])
            save_pdf(writer, output)
            print(f"Created {output} ({len(indexes)} pages)")
    print(f"Split complete: {len(outputs)} PDFs")


def info(args):
    with ExitStack() as stack:
        reader = open_pdf(stack, args.input)
        print(f"File: {args.input}")
        print(f"Pages: {len(reader.pages)}")
        print(f"Size: {args.input.stat().st_size:,} bytes")
        metadata = reader.metadata or {}
        for label in ("Title", "Author", "Subject", "Creator", "Producer"):
            value = metadata.get(f"/{label}")
            print(f"{label}: {value if value else '(not set)'}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="pdfly", description="Merge, split, extract and inspect PDFs locally.")
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("merge", help="Combine PDFs in the given order")
    command.add_argument("inputs", nargs="+", type=Path, help="Two or more input PDFs")
    command.add_argument("-o", "--output", required=True, type=Path)
    command.set_defaults(run=merge)

    command = commands.add_parser("split", help="Make one PDF per page or range")
    command.add_argument("input", type=Path)
    command.add_argument("-d", "--output-dir", required=True, type=Path)
    command.add_argument("--ranges", help="One output per range, e.g. 1-3,4-6,7")
    command.set_defaults(run=split)

    command = commands.add_parser("extract", help="Copy selected pages into one PDF")
    command.add_argument("input", type=Path)
    command.add_argument("-p", "--pages", required=True, help="Pages like 1,3-5,8")
    command.add_argument("-o", "--output", required=True, type=Path)
    command.set_defaults(run=extract)

    command = commands.add_parser("info", help="Show page count and metadata")
    command.add_argument("input", type=Path)
    command.set_defaults(run=info)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "merge" and len(args.inputs) < 2:
        parser.error("merge requires at least two input PDFs")
    try:
        args.run(args)
    except (OSError, ValueError, PyPdfError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
