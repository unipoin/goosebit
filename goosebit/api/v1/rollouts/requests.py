from pydantic import BaseModel


class RolloutsPutRequest(BaseModel):
    name: str
    feed: str
    software_id: int
    # create the rollout paused, devices only get the update once it is resumed
    paused: bool = False


class RolloutsPatchRequest(BaseModel):
    ids: list[int]
    paused: bool


class RolloutsDeleteRequest(BaseModel):
    ids: list[int]
