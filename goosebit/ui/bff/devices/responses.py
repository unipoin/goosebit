from __future__ import annotations

from enum import IntEnum
from typing import Any, Callable

from pydantic import BaseModel, Field
from tortoise.expressions import Q
from tortoise.queryset import QuerySet

from goosebit.db.models import Device, UpdateModeEnum, UpdateStateEnum
from goosebit.device_manager import DeviceManager, get_device_or_none
from goosebit.schema.devices import DeviceSchema
from goosebit.ui.bff.common.columns import DeviceColumns, orderable_names, searchable_names
from goosebit.ui.bff.common.requests import DataTableRequest

# Integer-enum columns displayed as text: search the term against the enum names, not the column.
ENUM_SEARCH_COLUMNS: dict[str, type[IntEnum]] = {
    "last_state": UpdateStateEnum,
    "update_mode": UpdateModeEnum,
}


# The target software column shows the software a device would get, which depends on its update mode (assigned,
# rollout, latest). Only assigned software is stored on the device, so this column is filtered in memory.
TARGET_SOFTWARE_COLUMN = "assigned_software__version"


async def _target_software_matches(device: Device, value: str) -> bool:
    # resolve on a separate instance: get_update() re-fetches relations and would drop the prefetched
    # compatibility of the instance that is serialized afterwards
    target_device = await get_device_or_none(device.id)
    if target_device is None:
        return False
    _, software = await DeviceManager.get_update(target_device)
    return software is not None and value.casefold() in software.version.casefold()


def _enum_search_query(name: str, enum_cls: type[IntEnum], value: str) -> Q:
    # Substring match on enum display names ("err" -> ERROR); no match -> empty __in -> no rows.
    value = value.casefold()
    matches = [int(member) for member in enum_cls if value in str(member).casefold()]
    return Q(**{f"{name}__in": matches})


class BFFDeviceResponse(BaseModel):
    data: list[DeviceSchema]
    draw: int
    records_total: int = Field(serialization_alias="recordsTotal")
    records_filtered: int = Field(serialization_alias="recordsFiltered")

    @classmethod
    async def convert(
        cls, dt_query: DataTableRequest, query: QuerySet[Any], search_filter: Callable[[str], Any]
    ) -> "BFFDeviceResponse":
        dt_query = dt_query.restricted(searchable_names(DeviceColumns), orderable_names(DeviceColumns))
        total_records = await query.count()
        if dt_query.search.value:
            query = query.filter(search_filter(dt_query.search.value))

        target_software_search: str | None = None
        for column in dt_query.columns:
            if column.name == TARGET_SOFTWARE_COLUMN and column.search.value is not None:
                target_software_search = column.search.value
                continue
            enum_cls = ENUM_SEARCH_COLUMNS.get(column.name)
            if enum_cls is not None and column.search.value is not None:
                column_query = _enum_search_query(column.name, enum_cls, column.search.value)
            else:
                column_query = column.query
            query = query.filter(column_query)

        if dt_query.order_query:
            query = query.order_by(dt_query.order_query)

        if target_software_search is None:
            filtered_records = await query.count()

            if dt_query.length is not None:
                query = query.limit(dt_query.length)

            devices = await query.offset(dt_query.start).all()
        else:
            # resolve the target software of every remaining device, then filter and page in memory
            devices = [d for d in await query.all() if await _target_software_matches(d, target_software_search)]
            filtered_records = len(devices)
            end = None if dt_query.length is None else dt_query.start + dt_query.length
            devices = devices[dt_query.start : end]

        data = [DeviceSchema.model_validate(d) for d in devices]

        return cls(data=data, draw=dt_query.draw, records_total=total_records, records_filtered=filtered_records)
