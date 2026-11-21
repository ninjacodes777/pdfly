"""End-to-end CLI tests. All generated PDFs live in a temporary directory."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

SCRIPT = Path(__file__).resolve().parent / "pdfly.py"


class PdflyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        # Distinct widths let us verify page order, not only page counts.
        for name, widths in (("notes.pdf", [101, 102, 103]),
                             ("exercises.pdf", [201, 202])):
            writer = PdfWriter()
            for width in widths:
                writer.add_blank_page(width=width, height=300)
            writer.add_metadata({"/Title": "Test document"})
            writer.write(self.folder / name)
            writer.close()

    def cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *args],
                                cwd=self.folder, capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
        return result

    def widths(self, name):
        # Strict parsing also checks that each output is a readable PDF.
        reader = PdfReader(self.folder / name, strict=True)
        return [int(page.mediabox.width) for page in reader.pages]

    def test_merge(self):
        self.cli("merge", "notes.pdf", "exercises.pdf", "-o", "merged.pdf")
        self.assertEqual(self.widths("merged.pdf"), [101, 102, 103, 201, 202])

    def test_split_pages(self):
        self.cli("split", "notes.pdf", "-d", "pages")
        self.assertEqual(len(list((self.folder / "pages").glob("*.pdf"))), 3)
        for number, width in enumerate([101, 102, 103], 1):
            self.assertEqual(self.widths(f"pages/notes_{number:03d}.pdf"), [width])

    def test_split_ranges(self):
        self.cli("split", "notes.pdf", "-d", "parts", "--ranges", "1-2,3")
        self.assertEqual(self.widths("parts/notes_001.pdf"), [101, 102])
        self.assertEqual(self.widths("parts/notes_002.pdf"), [103])

    def test_extract_order_and_duplicates(self):
        self.cli("extract", "notes.pdf", "-p", "3,1-2,1", "-o", "selected.pdf")
        self.assertEqual(self.widths("selected.pdf"), [103, 101, 102, 101])

    def test_info(self):
        output = self.cli("info", "notes.pdf").stdout
        self.assertIn("Pages: 3", output)
        self.assertIn("Title: Test document", output)

    def test_bad_selections(self):
        for selection in ("0", "4", "3-1", "1,,2", "abc", "-1", "1-"):
            with self.subTest(selection=selection):
                self.cli("extract", "notes.pdf", "-p", selection,
                         "-o", "bad.pdf", success=False)
                self.assertFalse((self.folder / "bad.pdf").exists())

    def test_refuses_overwrite_and_input_collision(self):
        self.cli("extract", "notes.pdf", "-p", "1", "-o", "notes.pdf", success=False)
        self.assertEqual(self.widths("notes.pdf"), [101, 102, 103])
        self.cli("merge", "notes.pdf", "exercises.pdf", "-o", "merged.pdf")
        original = (self.folder / "merged.pdf").read_bytes()
        self.cli("merge", "notes.pdf", "exercises.pdf", "-o", "merged.pdf", success=False)
        self.assertEqual((self.folder / "merged.pdf").read_bytes(), original)

    def test_split_checks_all_names_first(self):
        directory = self.folder / "parts"
        directory.mkdir()
        (directory / "notes_002.pdf").write_text("leave this file alone")
        self.cli("split", "notes.pdf", "-d", "parts", success=False)
        self.assertFalse((directory / "notes_001.pdf").exists())
        self.assertEqual((directory / "notes_002.pdf").read_text(), "leave this file alone")

    def test_missing_corrupt_and_encrypted(self):
        self.cli("info", "missing.pdf", success=False)
        (self.folder / "broken.pdf").write_bytes(b"not a PDF")
        self.cli("info", "broken.pdf", success=False)
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.encrypt("test-only-password")
        writer.write(self.folder / "locked.pdf")
        writer.close()
        self.cli("info", "locked.pdf", success=False)

    def test_merge_requires_two_inputs(self):
        self.cli("merge", "notes.pdf", "-o", "bad.pdf", success=False)


if __name__ == "__main__":
    unittest.main()
