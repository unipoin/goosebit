from goosebit.ui.bff.common.columns import DeviceColumns, orderable_names, searchable_names
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
