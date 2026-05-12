import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CompileResult:
    success: bool
    page_count: int = 0
    pdf_bytes: bytes | None = None
    error: str | None = None


_PAGES_RE = re.compile(r"Output written on .+?\((\d+) pages?")


def compile_latex_to_pdf(latex: str, timeout: float = 25.0) -> CompileResult:
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = Path(tmpdir) / "cv.tex"
        tex_path.write_text(latex)
        try:
            proc = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                 "-output-directory", tmpdir, str(tex_path)],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return CompileResult(success=False, error="pdflatex timed out")
        except FileNotFoundError:
            return CompileResult(success=False, error="pdflatex binary not found on PATH")

        pdf_path = Path(tmpdir) / "cv.pdf"
        if proc.returncode != 0 or not pdf_path.exists():
            tail = (proc.stdout + proc.stderr)[-1200:]
            return CompileResult(success=False, error=tail)

        match = _PAGES_RE.search(proc.stdout)
        return CompileResult(
            success=True,
            page_count=int(match.group(1)) if match else 0,
            pdf_bytes=pdf_path.read_bytes(),
        )
