from __future__ import annotations

from fastapi import APIRouter, Security
from fastapi.requests import Request

from goosebit.api.responses import StatusResponse
from goosebit.auth import validate_user_permissions
from goosebit.models import Device, Firmware, UpdateModeEnum
from goosebit.permissions import Permissions
from goosebit.updater.manager import delete_devices, get_update_manager

from . import device
from .requests import DevicesDeleteRequest, DevicesPatchRequest
from .responses import DevicesResponse

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get(
    "",
    dependencies=[Security(validate_user_permissions, scopes=[Permissions.HOME.READ])],
)
async def devices_get(_: Request) -> DevicesResponse:
    return await DevicesResponse.convert(await Device.all().prefetch_related("assigned_firmware", "hardware"))


@router.patch(
    "",
    dependencies=[Security(validate_user_permissions, scopes=[Permissions.DEVICE.WRITE])],
)
async def devices_patch(_: Request, config: DevicesPatchRequest) -> StatusResponse:
    for uuid in config.devices:
        updater = await get_update_manager(uuid)
        if config.firmware is not None:
            if config.firmware == "rollout":
                await updater.update_update(UpdateModeEnum.ROLLOUT, None)
            elif config.firmware == "latest":
                await updater.update_update(UpdateModeEnum.LATEST, None)
            else:
                firmware = await Firmware.get_or_none(id=config.firmware)
                await updater.update_update(UpdateModeEnum.ASSIGNED, firmware)
        if config.pinned is not None:
            await updater.update_update(UpdateModeEnum.PINNED, None)
        if config.name is not None:
            await updater.update_name(config.name)
        if config.feed is not None:
            await updater.update_feed(config.feed)
        if config.force_update is not None:
            await updater.update_force_update(config.force_update)
    return StatusResponse(success=True)


@router.delete(
    "",
    dependencies=[Security(validate_user_permissions, scopes=[Permissions.DEVICE.DELETE])],
)
async def devices_delete(_: Request, config: DevicesDeleteRequest) -> StatusResponse:
    await delete_devices(config.devices)
    return StatusResponse(success=True)


router.include_router(device.router)
