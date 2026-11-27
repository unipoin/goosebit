import pytest

from goosebit.ui.bff.common.columns import (
    DeviceColumns,
    RolloutColumns,
    SettingsUsersColumns,
    SoftwareColumns,
    orderable_names,
    searchable_names,
)
from goosebit.ui.bff.common.responses import DTColumnDescription
from goosebit.ui.bff.common.requests import DataTableRequest


def test_restricted_drops_unknown_filters_and_order() -> None:
    request = DataTableRequest.model_validate(
        {
            "columns": [
                {"data": "id", "name": "id", "search": {"value": "dev"}},
                {
                    "data": "x",
                    "name": "assigned_software__compatibility__devices__auth_token",
                    "search": {"value": "a"},
                },
            ],
            "order": [{"name": "auth_token", "dir": "asc"}],
        }
    )

    restricted = request.restricted(searchable_names(DeviceColumns), orderable_names(DeviceColumns))

    assert restricted.columns[0].search.value == "dev"
    assert restricted.columns[1].search.value is None
    assert restricted.order == []
    assert restricted.order_query is None
    # the original request is not modified
    assert request.columns[1].search.value == "a"


def test_restricted_keeps_known_order() -> None:
    request = DataTableRequest.model_validate({"order": [{"name": "last_seen", "dir": "desc"}]})

    restricted = request.restricted(searchable_names(DeviceColumns), orderable_names(DeviceColumns))

    assert restricted.order_query == "-last_seen"


def test_device_column_names() -> None:
    assert "hardware__model" in searchable_names(DeviceColumns)
    assert "auth_token" not in searchable_names(DeviceColumns)
    assert "last_seen" in orderable_names(DeviceColumns)


@pytest.mark.parametrize("columns", [DeviceColumns, RolloutColumns, SettingsUsersColumns, SoftwareColumns])
def test_searchable_and_orderable_columns_have_names(columns: type) -> None:
    # columns without a name are silently ignored by DataTableRequest.restricted()
    for attribute, column in vars(columns).items():
        if isinstance(column, DTColumnDescription) and (column.searchable or column.orderable):
            assert column.name, f"{columns.__name__}.{attribute} is searchable/orderable but has no name"
