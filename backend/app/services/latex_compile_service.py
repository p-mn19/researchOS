from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


TECTONIC_EXECUTABLE = (
    r"C:\Users\Prem\tools\tectonic\tectonic.exe"
)
COMPILE_TIMEOUT_SECONDS = 300
MAX_LATEX_SOURCE_CHARS = 250_000
MAX_BIBTEX_CHARS = 250_000


def _convert_markdown_bold(latex_source: str) -> str:
    """Support Markdown bold markers left in legacy generated drafts."""
    return re.sub(
        r"\*\*(.+?)\*\*",
        r"\\textbf{\1}",
        latex_source,
    )


def _restore_legacy_citation_tokens(
    latex_source: str,
    references_bib: str,
) -> str:
    """Convert older escaped citation placeholders back to LaTeX cites."""
    citation_keys = re.findall(
        r"@\w+\s*\{\s*([^,\s]+)",
        references_bib,
    )

    def replace_token(match: re.Match[str]) -> str:
        citation_index = int(match.group(1))

        if citation_index >= len(citation_keys):
            return match.group(0)

        return f"\\cite{{{citation_keys[citation_index]}}}"

    return re.sub(
        r"@@CITATION(?:\\_|_)(\d+)@@",
        replace_token,
        latex_source,
    )


def build_complete_document(
    latex_source: str,
    references_bib: str = "",
) -> str:
    """
    Accept either a complete LaTeX document or a generated LaTeX section.

    Workspace AI generation currently returns content such as:
        \\section{Related Work}
        ...

    This function wraps such generated section content in a minimal
    compilable LaTeX document.
    """
    source = _restore_legacy_citation_tokens(
        _convert_markdown_bold(
            (latex_source or "").strip(),
        ),
        references_bib,
    )

    if "\\documentclass" in source:
        return source

    bibliography = """
\\nocite{*}
\\bibliographystyle{plain}
\\bibliography{references}
""" if references_bib.strip() else ""

    return f"""\\documentclass[12pt]{{article}}

\\usepackage[margin=1in]{{geometry}}
\\usepackage{{amsmath}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}

\\title{{ResearchOS Generated Draft}}
\\author{{}}
\\date{{}}

\\begin{{document}}

\\maketitle

{source}

{bibliography}

\\end{{document}}
"""


def parse_latex_errors(log_text: str) -> list[dict[str, Any]]:
    """
    Extract a small, display-friendly error list from Tectonic output.

    The raw compile log is also returned to the caller for debugging.
    """
    errors: list[dict[str, Any]] = []
    seen: set[tuple[int | None, str]] = set()

    patterns = [
        re.compile(r"main\.tex:(\d+):\s*(.+)"),
        re.compile(r"l\.(\d+)\s+(.+)"),
        re.compile(r"error:\s*(.+)", re.IGNORECASE),
    ]

    for raw_line in log_text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        for pattern in patterns:
            match = pattern.search(line)

            if not match:
                continue

            if pattern.pattern.startswith("main"):
                line_number = int(match.group(1))
                message = match.group(2).strip()
            elif pattern.pattern.startswith("l\\."):
                line_number = int(match.group(1))
                message = match.group(2).strip()
            else:
                line_number = None
                message = match.group(1).strip()

            key = (line_number, message)

            if key not in seen:
                errors.append(
                    {
                        "line": line_number,
                        "message": message,
                    }
                )
                seen.add(key)

            break

    return errors[:20]


def compile_latex(
    latex_source: str,
    references_bib: str = "",
) -> dict[str, Any]:
    """
    Compile workspace LaTeX using Tectonic.

    Security boundaries in this initial implementation:
    - Fixed filenames: main.tex and references.bib
    - New temporary directory for every request
    - Tectonic --untrusted mode
    - No shell=True
    - Compile timeout
    - Source-size limits
    """
    source = (latex_source or "").strip()
    bibtex = (references_bib or "").strip()

    if not source:
        return {
            "success": False,
            "pdf_bytes": None,
            "log": "No LaTeX source was provided.",
            "errors": [
                {
                    "line": None,
                    "message": "No LaTeX source was provided.",
                }
            ],
        }

    if len(source) > MAX_LATEX_SOURCE_CHARS:
        return {
            "success": False,
            "pdf_bytes": None,
            "log": "LaTeX source exceeds the allowed size.",
            "errors": [
                {
                    "line": None,
                    "message": (
                        f"LaTeX source must be at most "
                        f"{MAX_LATEX_SOURCE_CHARS:,} characters."
                    ),
                }
            ],
        }

    if len(bibtex) > MAX_BIBTEX_CHARS:
        return {
            "success": False,
            "pdf_bytes": None,
            "log": "BibTeX source exceeds the allowed size.",
            "errors": [
                {
                    "line": None,
                    "message": (
                        f"BibTeX source must be at most "
                        f"{MAX_BIBTEX_CHARS:,} characters."
                    ),
                }
            ],
        }

    tectonic_path = shutil.which(TECTONIC_EXECUTABLE)

    if tectonic_path is None:
        return {
            "success": False,
            "pdf_bytes": None,
            "log": "Tectonic executable was not found on PATH.",
            "errors": [
                {
                    "line": None,
                    "message": (
                        "Tectonic is not installed or cannot be found "
                        "through the backend PATH."
                    ),
                }
            ],
        }

    complete_document = build_complete_document(source, bibtex)

    with tempfile.TemporaryDirectory(
        prefix="researchos_latex_",
    ) as temp_dir:
        workspace_dir = Path(temp_dir)
        output_dir = workspace_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        tex_path = workspace_dir / "main.tex"
        bib_path = workspace_dir / "references.bib"
        pdf_path = output_dir / "main.pdf"

        tex_path.write_text(
            complete_document,
            encoding="utf-8",
        )

        if bibtex:
            bib_path.write_text(
                bibtex,
                encoding="utf-8",
            )

        command = [
            tectonic_path,
            "--untrusted",
            "--keep-logs",
            "--keep-intermediates",
            "--outdir",
            str(output_dir),
            str(tex_path),
        ]

        try:
            result = subprocess.run(
                command,
                cwd=workspace_dir,
                capture_output=True,
                text=True,
                timeout=COMPILE_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "pdf_bytes": None,
                "log": (
                    "LaTeX compilation exceeded the "
                    f"{COMPILE_TIMEOUT_SECONDS}-second time limit."
                ),
                "errors": [
                    {
                        "line": None,
                        "message": "LaTeX compilation timed out.",
                    }
                ],
            }
        except OSError as exc:
            return {
                "success": False,
                "pdf_bytes": None,
                "log": str(exc),
                "errors": [
                    {
                        "line": None,
                        "message": (
                            "Unable to start the Tectonic compiler: "
                            f"{exc}"
                        ),
                    }
                ],
            }

        compile_log = "\n".join(
            item
            for item in (
                result.stdout.strip(),
                result.stderr.strip(),
            )
            if item
        ).strip()

        if result.returncode != 0 or not pdf_path.exists():
            if not compile_log:
                compile_log = (
                    "Tectonic did not produce a PDF. "
                    f"Process exit code: {result.returncode}."
                )

            errors = parse_latex_errors(compile_log)

            if not errors:
                errors = [
                    {
                        "line": None,
                        "message": (
                            "LaTeX compilation failed. Check the "
                            "compiler log for details."
                        ),
                    }
                ]

            return {
                "success": False,
                "pdf_bytes": None,
                "log": compile_log,
                "errors": errors,
            }

        return {
            "success": True,
            "pdf_bytes": pdf_path.read_bytes(),
            "log": compile_log,
            "errors": [],
        }
