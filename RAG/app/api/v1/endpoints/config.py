from fastapi import APIRouter, HTTPException, Request, status
from pydantic import ValidationError

from app.core.config import build_config_fields, upsert_settings, validate_setting_updates
from app.core.runtime import reload_runtime_services
from app.schemas.config import (
    ConfigStateResponse,
    ConfigUpdateRequest,
    ConfigUpdateResponse,
)


router = APIRouter(tags=["config"])


@router.get(
    "/config",
    response_model=ConfigStateResponse,
    summary="获取当前配置和字段定义",
)
async def get_config() -> ConfigStateResponse:
    return ConfigStateResponse(fields=build_config_fields())


@router.patch(
    "/config",
    response_model=ConfigUpdateResponse,
    summary="更新配置并立即刷新服务",
)
async def update_config(
    payload: ConfigUpdateRequest,
    request: Request,
) -> ConfigUpdateResponse:
    try:
        validated_updates = validate_setting_updates(payload.values)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    upsert_settings(validated_updates)
    reload_runtime_services(request.app)

    return ConfigUpdateResponse(
        message="保存成功，配置已刷新",
        fields=build_config_fields(),
    )
