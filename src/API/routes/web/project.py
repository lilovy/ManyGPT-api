from fastapi import APIRouter, Depends, Request, status, Query, Response
from fastapi.responses import FileResponse
from typing import List

from ....core.llms import LLMs
from ...models.project import UserProject, NewUserProject, Projects
from ...models.subscription import Subs
from ...models.count import Count
from ...models.responses import ResponseStatus
from ...dependencies.dependencies import *
from ....database.db import DBHelper


router = APIRouter(prefix="/project", tags=["project"])


@router.get("/count", response_model=Count, status_code=200)
async def get_count_projects(
    request: Request,
    db: DBHelper = Depends(get_db),
    ):
    if request.state.auth.get("status") != status.HTTP_200_OK:
        return request.state.auth

    user_id = request.state.user.get("user_id")
    count = db.get_project_count(
        user_id,
    )
    return Count(
        user_id=user_id,
        object="projects",
        count=count,
    )


@router.get("/all", response_model=List[Projects], status_code=200)
async def get_user_projects(
    request: Request,
    offset: int = Query (0, ge=0),
    limit: int = Query(10, ge=1),
    db: DBHelper = Depends(get_db),
    ):
    if request.state.auth.get("status") != status.HTTP_200_OK:
        return request.state.auth

    user_id = request.state.user.get("user_id")
    projects = db.get_user_projects(user_id, offset, limit)

    project = {"user_id": 123, "name": "pj2", "file": "cats.png"}

    return [Projects(**project) for project in projects]


@router.get("/file", response_class=FileResponse)
async def get_user_project_file(
    request: Request,
    project: UserProject,
    db: DBHelper = Depends(get_db),
    ):
    if request.state.auth.get("status") != status.HTTP_200_OK:
        return request.state.auth
    user = request.state.auth
    user_id = user.get("user_id")
    if user_id != model.user_id:
        return {"status": status.HTTP_401_UNAUTHORIZED}

    content = db.get_user_data_files(
        project.project_id,
    )
    content = "\n".join(content)

    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename={project.name}.txt"
        }
    )


@router.get("/access", responses={200: {"model": ResponseStatus}, 401: {"model": ResponseStatus}})
def сhecking_project_access(
    reques: Request,
    db: DBHelper = Depends(get_db),
):
    if request.state.auth.get("status") != status.HTTP_200_OK:
        return request.state.auth

    user = request.state.auth
    user_id = user.get("user_id")
    if user_id != project.user_id:
        return {"status": status.HTTP_401_UNAUTHORIZED}

    if db.get_user_subscribe_level(user_id) == Subs.advanced.value:
        return {"status": status.HTTP_200_OK}

    return {"status": status.HTTP_401_UNAUTHORIZED}


@router.post("/new", responses={201: {"model": ResponseStatus}, 401: {"model": ResponseStatus}})
async def add_user_project(
    request: Request,
    project: NewUserProject,
    db: DBHelper = Depends(get_db),
    llm: LLMs = Depends(get_llm),
    ):
    if request.state.auth.get("status") != status.HTTP_200_OK:
        return request.state.auth
    user = request.state.auth
    user_id = user.get("user_id")
    if user_id != project.user_id:
        return {"status": status.HTTP_401_UNAUTHORIZED}

    base_model = db.get_base_model(project.base_model_id)

    llm.new_bot(
        project.name,
        project.prompt,
        base_model,
    )

    db.add_project(
        user_id=project.user_id,
        name=project.name,
        system_name=project.system_name,
        mimetype=project.mimetype,
        model_id=project.model_id,
        prompt=project.prompt,
        file=await project.file.read(),
    )
    
    return {"status": status.HTTP_201_CREATED}