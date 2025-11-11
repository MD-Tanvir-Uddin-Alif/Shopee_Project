from pydantic import BaseModel
from typing import Optional, Union


class DeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    cookies: Optional[Union[dict, list]] = None
