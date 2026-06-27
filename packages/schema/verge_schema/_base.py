"""Shared base model. Wire format is camelCase (API <-> TS); Python is snake_case."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class VergeModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_enum_values=True,
        extra="forbid",
    )
