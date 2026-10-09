from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal

DocumentFormat = Literal["normal", "ieee"]

TECTONIC_EXECUTABLE = (
    r"C:\Users\Prem\tools\tectonic\tectonic.exe"
)

COMPILE_TIMEOUT_SECONDS = 300
MAX_LATEX_SOURCE_CHARS = 250_000
MAX_BIBTEX_CHARS = 250_000


def _compile_failure(
    log: str,
    message: str,
    line: int | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "pdf_bytes": None,
        "log": log,
        "errors": [
            {
                "line": line,
                "message": message,
            }
        ],
    }


def _convert_markdown_bold(
    latex_source: str,
) -> str:
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


def _normal_document_preamble() -> str:
    return r"""\documentclass[12pt,a4paper]{article}

\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage{url}
\usepackage[hidelinks]{hyperref}
\usepackage{float}

\title{ResearchOS Generated Draft}
\author{}
\date{}
"""


def _ieee_document_preamble() -> str:
    return r"""\documentclass[conference]{IEEEtran}

\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{xcolor}
\usepackage{booktabs}
\usepackage{array}
\usepackage{enumitem}
\usepackage{url}
\usepackage[hidelinks]{hyperref}
\usepackage{balance}
\usepackage{float}

\title{ResearchOS Generated Draft}
\author{}
"""


def _bibliography_block(
    references_bib: str,
    document_format: DocumentFormat,
) -> str:
    if not references_bib.strip():
        return ""

    bibliography_style = (
        "IEEEtran"
        if document_format == "ieee"
        else "plain"
    )

    return (
        "\n\\nocite{*}\n"
        f"\\bibliographystyle{{{bibliography_style}}}\n"
        "\\bibliography{references}\n"
    )


def validate_document_format(
    latex_source: str,
    document_format: DocumentFormat,
) -> str | None:
    """
    Validate a full LaTeX document against its selected format.

    Returns an error string when a complete document has a document-class
    mismatch. Returns None for valid complete documents and fragments.
    """
    source = latex_source or ""

    if "\\documentclass" not in source:
        return None

    ieee_document_class = (
        r"\documentclass[conference]{IEEEtran}"
    )

    if (
        document_format == "ieee"
        and ieee_document_class not in source
    ):
        return (
            "IEEE double-column format was selected, but the LaTeX "
            "source does not contain "
            r"\documentclass[conference]{IEEEtran}."
        )

    if (
        document_format == "normal"
        and "IEEEtran" in source
    ):
        return (
            "Normal single-column format was selected, but the LaTeX "
            "source still uses the IEEEtran document class."
        )

    return None


def build_complete_document(
    latex_source: str,
    references_bib: str = "",
    document_format: DocumentFormat = "normal",
) -> str:
    """
    Accept a complete LaTeX document or a generated LaTeX fragment.

    If the source is a fragment, wrap it using either a normal article
    template or IEEE two-column conference template.
    """
    source = _restore_legacy_citation_tokens(
        _convert_markdown_bold(
            (latex_source or "").strip(),
        ),
        references_bib,
    )

    if "\\documentclass" in source:
        return source

    preamble = (
        _ieee_document_preamble()
        if document_format == "ieee"
        else _normal_document_preamble()
    )

    bibliography = _bibliography_block(
        references_bib,
        document_format,
    )

    return f"""{preamble}

\\begin{{document}}

\\maketitle

{source}

{bibliography}

\\end{{document}}
"""


def parse_latex_errors(
    log_text: str,
) -> list[dict[str, Any]]:
    """
    Extract a small display-friendly error list from Tectonic output.
    The raw compiler log is also returned.
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
    document_format: DocumentFormat = "normal",
) -> dict[str, Any]:
    """
    Compile workspace LaTeX using Tectonic.

    Security boundaries:
    - Fixed filenames: main.tex and references.bib
    - A new temporary directory per request
    - Tectonic --untrusted mode
    - No shell=True
    - Timeouts and size limits
    """
    source = (latex_source or "").strip()
    bibtex = (references_bib or "").strip()

    if document_format not in ("normal", "ieee"):
        return _compile_failure(
            log="Unsupported document format.",
            message=(
                "Document format must be either 'normal' or 'ieee'."
            ),
        )

    if not source:
        return _compile_failure(
            log="No LaTeX source was provided.",
            message="No LaTeX source was provided.",
        )

    if len(source) > MAX_LATEX_SOURCE_CHARS:
        return _compile_failure(
            log="LaTeX source exceeds the allowed size.",
            message=(
                f"LaTeX source must be at most "
                f"{MAX_LATEX_SOURCE_CHARS:,} characters."
            ),
        )

    if len(bibtex) > MAX_BIBTEX_CHARS:
        return _compile_failure(
            log="BibTeX source exceeds the allowed size.",
            message=(
                f"BibTeX source must be at most "
                f"{MAX_BIBTEX_CHARS:,} characters."
            ),
        )

    format_error = validate_document_format(
        source,
        document_format,
    )

    if format_error:
        return _compile_failure(
            log=format_error,
            message=format_error,
        )

    tectonic_path = shutil.which(TECTONIC_EXECUTABLE)

    if tectonic_path is None:
        tectonic_path = shutil.which("tectonic")

    if tectonic_path is None:
        return _compile_failure(
            log="Tectonic executable was not found.",
            message=(
                "Tectonic is not installed or cannot be found "
                "through the configured executable path or backend PATH."
            ),
        )

    complete_document = build_complete_document(
        latex_source=source,
        references_bib=bibtex,
        document_format=document_format,
    )

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
            return _compile_failure(
                log=(
                    "LaTeX compilation exceeded the "
                    f"{COMPILE_TIMEOUT_SECONDS}-second time limit."
                ),
                message="LaTeX compilation timed out.",
            )
        except OSError as exc:
            return _compile_failure(
                log=str(exc),
                message=(
                    "Unable to start the Tectonic compiler: "
                    f"{exc}"
                ),
            )

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