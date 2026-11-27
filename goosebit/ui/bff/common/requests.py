from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Iterable

from pydantic import BaseModel, BeforeValidator, Field, computed_field
from tortoise.expressions import Q


class DataTableSearchSchema(BaseModel):
    value: str | None = None
    regex: bool | None = False


class DataTableOrderDirection(StrEnum):
    ASCENDING = "asc"
    DESCENDING = "desc"


class DataTableOrderSchema(BaseModel):
    column: int | None = None
    dir: DataTableOrderDirection | None = None
    name: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def direction(self) -> str:
        return "-" if self.dir == DataTableOrderDirection.DESCENDING else ""


class DataTableColumnSearchSchema(BaseModel):
    fixed: list[str] = Field(default_factory=list)
    regex: bool = False
    value: Annotated[str | None, BeforeValidator(lambda x: x if not x == "" else None)] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def searchable(self) -> bool:
        return self.value is not None


class DataTableColumnSchema(BaseModel):
    data: str
    name: str
    orderable: bool = False
    search: DataTableColumnSearchSchema = DataTableColumnSearchSchema()

    @property
    def query(self) -> Q:
        if not self.search.searchable:
            return Q()
        if self.name == "":
            return Q()
        searches = self.name.split("|")
        queries = [Q(**{f"{search}__icontains": self.search.value}) for search in searches]
        return Q(*queries, join_type="OR")


class DataTableRequest(BaseModel):
    draw: int = 1
    order: list[DataTableOrderSchema] = list()
    start: int = 0
    length: Annotated[int | None, BeforeValidator(lambda value: None if value == -1 else value)] = None
    search: DataTableSearchSchema = DataTableSearchSchema()
    columns: list[DataTableColumnSchema] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def order_query(self) -> str | None:
        try:
            if len(self.order) == 0 or self.order[0].direction is None or self.order[0].name is None:
                return None
            return f"{self.order[0].direction}{self.order[0].name}"
        except LookupError:
            return None

    def restricted(self, searchable: Iterable[str], orderable: Iterable[str]) -> DataTableRequest:
        """Return a copy that only filters and orders by the given column names.

        Column and order names are sent by the client and are used as ORM field paths, which can traverse
        relations (e.g. "compatibility__devices__auth_token"). Only names defined by the table columns are
        allowed, everything else is ignored.
        """
        searchable_names = set(searchable)
        orderable_names = set(orderable)

        request = self.model_copy(deep=True)
        for column in request.columns:
            if column.name not in searchable_names:
                column.search = DataTableColumnSearchSchema()
        request.order = [order for order in request.order if order.name in orderable_names]
        return request
