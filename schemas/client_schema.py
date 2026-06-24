from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Optional, List
from datetime import datetime


class ClientType(str, Enum):
    customer = "Customer"
    vender = "Vender"


class AddressType(str, Enum):
    office = "Office"
    home = "Home"
    other = "Other"


class ClientAddressCreate(BaseModel):
    address_line_1: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    country: str = Field(default="Pakistan", min_length=1)
    address_type: Optional[AddressType] = AddressType.office
    is_primary: Optional[bool] = True
    address_line_2: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class ClientAddressResponse(BaseModel):
    address_id: str
    client_id: str
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: str
    address_type: str
    is_primary: bool
    status: bool
    created_on: datetime
    updated_on: datetime


class ClientPOCCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)

class ClientPOCResponse(BaseModel):
    poc_id: str
    client_id: str
    address_id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    status: bool
    created_on: datetime
    updated_on: datetime

class ClientAddressWithPOC(BaseModel):
    address: ClientAddressCreate
    poc: ClientPOCCreate

class ClientCreateRequest(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=50)
    client_type: ClientType = ClientType.customer
    locations: List[ClientAddressWithPOC] = Field(..., min_length=1)

    @field_validator("locations")
    @classmethod
    def at_least_one_primary(cls, v: List[ClientAddressWithPOC]):
        if not any(loc.address.is_primary for loc in v):
            raise ValueError("At least one address must be marked as primary")
        return v


class ClientUpdateRequest(BaseModel):
    client_name: Optional[str] = Field(None, min_length=2, max_length=50)
    client_type: Optional[ClientType] = None
    status: Optional[bool] = None


class ClientListItem(BaseModel):
    client_id: str
    client_name: str
    client_type: str
    status: bool
    created_by: str
    updated_by: str
    created_on: datetime
    updated_on: datetime
    addresses: List[ClientAddressResponse] = []
    pocs: List[ClientPOCResponse] = []


class ClientListResponse(BaseModel):
    success: bool
    message: str
    count: int
    data: List[ClientListItem]


class ClientDetailResponse(BaseModel):
    success: bool
    message: str
    client_id: str
    client_name: str
    client_type: str
    status: bool
    created_by: str
    updated_by: str
    created_on: datetime
    updated_on: datetime
    addresses: List[ClientAddressResponse] = []
    pocs: List[ClientPOCResponse] = []
    


class ClientAddressUpdate(BaseModel):
    address_line_1: Optional[str] = Field(None, min_length=1)
    address_line_2: Optional[str] = None
    city: Optional[str] = Field(default="Pakistan", min_length=1)
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    address_type: Optional[AddressType] = None
    is_primary: Optional[bool] = None
    status: Optional[bool] = None


class ClientPOCUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    address_id: Optional[str] = None
    status: Optional[bool] = None
    
class ClientEntityType(str, Enum):
    client = "client"
    address = "address"
    poc = "poc"


class ClientDeleteRequest(BaseModel):
    entity_type: ClientEntityType
    entity_id: str
    

    