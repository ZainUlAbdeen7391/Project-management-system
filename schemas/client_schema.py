from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
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
    address_id: int
    poc_id: int
    address_line_1: str
    address_line_2: Optional[str] = None
    city: Optional[str] = None
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
    poc_id: int
    client_id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    status: bool
    created_on: datetime
    updated_on: datetime


class ClientCreateRequest(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=50)
    client_type: ClientType = ClientType.customer
    address: ClientAddressCreate      
    poc: ClientPOCCreate             


class ClientUpdateRequest(BaseModel):
    client_name: Optional[str] = Field(None, min_length=2, max_length=50)
    client_type: Optional[ClientType] = None
    status: Optional[bool] = None


class ClientResponse(BaseModel):
    success: bool
    message: str
    client_id: int
    client_name: str
    client_type: str
    status: bool
    created_by: int
    updated_by: int
    created_on: datetime
    updated_on: datetime


class ClientListItem(BaseModel):
    client_id: int
    client_name: str
    client_type: str
    status: bool
    created_by: int
    updated_by: int
    created_on: datetime
    updated_on: datetime


class ClientListResponse(BaseModel):
    success: bool
    message: str
    count: int
    data: list[ClientListItem]


class ClientDetailResponse(BaseModel):
    success: bool
    message: str
    client_id: int
    client_name: str
    client_type: str
    status: bool
    created_by: int
    updated_by: int
    created_on: datetime
    updated_on: datetime
    addresses: list[ClientAddressResponse] = []
    pocs: list[ClientPOCResponse] = []
    
    
    