from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from app.schemas.workspace import (
    WorkspaceLatexCompileRequest,
    WorkspaceLatexCompileStatusResponse,
)
from app.services.latex_compile_service import compile_latex
from app.services.workspace_service import get_workspace

router = APIRouter(
    prefix="/workspaces",
    tags=["LaTeX Workspace"],
)


@router.post(
    "/{workspace_id}/latex/compile/status",
    response_model=WorkspaceLatexCompileStatusResponse,
)
def compile_workspace_latex_status(
    workspace_id: str,
    payload: WorkspaceLatexCompileRequest,
) -> WorkspaceLatexCompileStatusResponse:
    """
    Compile LaTeX and return status, compiler log, and parsed errors
    without returning PDF bytes.
    """
    get_workspace(workspace_id)

    result = compile_latex(
        latex_source=payload.latex_code,
        references_bib=payload.references_bib,
        document_format=payload.document_format,
    )

    return WorkspaceLatexCompileStatusResponse(
        success=result["success"],
        log=result["log"],
        errors=result["errors"],
        document_format=payload.document_format,
    )


@router.post(
    "/{workspace_id}/latex/compile",
    responses={
        200: {
            "content": {
                "application/pdf": {},
            },
            "description": (
                "Compiled PDF returned as binary data."
            ),
        },
        422: {
            "description": (
                "LaTeX compilation failed. The response contains "
                "the Tectonic log and parsed errors."
            ),
        },
    },
)
def compile_workspace_latex(
    workspace_id: str,
    payload: WorkspaceLatexCompileRequest,
) -> Response:
    """
    Compile a workspace LaTeX draft and return its PDF directly.

    The compiled PDF is not persistently stored. The frontend uses
    browser Blob URLs for temporary preview and download.
    """
    get_workspace(workspace_id)

    result = compile_latex(
        latex_source=payload.latex_code,
        references_bib=payload.references_bib,
        document_format=payload.document_format,
    )

    if not result["success"] or not result["pdf_bytes"]:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "LaTeX compilation failed.",
                "log": result["log"],
                "errors": result["errors"],
                "document_format": payload.document_format,
            },
        )

    return Response(
        content=result["pdf_bytes"],
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'inline; filename="researchos-document.pdf"'
            ),
            "Cache-Control": "no-store",
            "X-ResearchOS-Document-Format": payload.document_format,
        },
    )