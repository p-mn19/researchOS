from typing import List

from fastapi import APIRouter

from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceGenerateRequest,
    WorkspaceGenerationResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
    WorkspaceVersionCreate,
    WorkspaceVersionResponse,
)
from app.services.workspace_service import (
    create_workspace,
    create_workspace_version,
    delete_workspace,
    generate_workspace_content,
    get_workspace,
    list_workspace_versions,
    list_workspaces,
    update_workspace,
)

router = APIRouter(
    prefix="/workspaces",
    tags=["Module 9 - Research Workspace"],
)


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=201,
)
def create_new_workspace(
    payload: WorkspaceCreate,
) -> WorkspaceResponse:
    return create_workspace(payload)


@router.get(
    "",
    response_model=List[WorkspaceResponse],
)
def get_all_workspaces() -> List[WorkspaceResponse]:
    return list_workspaces()


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
)
def get_one_workspace(
    workspace_id: str,
) -> WorkspaceResponse:
    return get_workspace(workspace_id)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
)
def update_one_workspace(
    workspace_id: str,
    payload: WorkspaceUpdate,
) -> WorkspaceResponse:
    return update_workspace(workspace_id, payload)


@router.delete(
    "/{workspace_id}",
)
def delete_one_workspace(
    workspace_id: str,
) -> dict[str, int | str]:
    return delete_workspace(workspace_id)


@router.post(
    "/{workspace_id}/generate",
    response_model=WorkspaceGenerationResponse,
)
def generate_content_for_workspace(
    workspace_id: str,
    payload: WorkspaceGenerateRequest,
) -> WorkspaceGenerationResponse:
    return generate_workspace_content(
        workspace_id,
        payload,
    )


@router.post(
    "/{workspace_id}/versions",
    response_model=WorkspaceVersionResponse,
    status_code=201,
)
def save_workspace_version(
    workspace_id: str,
    payload: WorkspaceVersionCreate,
) -> WorkspaceVersionResponse:
    return create_workspace_version(
        workspace_id,
        payload,
    )


@router.get(
    "/{workspace_id}/versions",
    response_model=List[WorkspaceVersionResponse],
)
def get_workspace_version_list(
    workspace_id: str,
) -> List[WorkspaceVersionResponse]:
    return list_workspace_versions(workspace_id)
