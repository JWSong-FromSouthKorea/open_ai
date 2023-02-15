from pydantic import BaseModel
from typing import TypeVar, Optional, Union

T = TypeVar('T')


class CommonResponse(BaseModel):
    data: Union[Optional[T]]
    result: bool
