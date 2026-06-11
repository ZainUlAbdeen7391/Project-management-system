from fastapi import APIRouter, HTTPException, Depends
from configurations.database import get_db
import schemas.client_schema as Client_schemas
from utilities.dependencies import get_current_user, require_permission
from repositories import client_repository

router = APIRouter(prefix="/client", tags=["Client"])


#create client
@router.post("/", response_model=Client_schemas.ClientDetailResponse, status_code=201)
async def create_client(
    payload: Client_schemas.ClientCreateRequest,
    cur=Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        data = await client_repository.create_client(cur, payload, current_user["user_id"])
        return Client_schemas.ClientDetailResponse(
            success=True,
            message="Client created successfully",
            **data["client"],
            addresses=data["addresses"],
            pocs=data["pocs"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


#get all clients
@router.get("/",response_model=Client_schemas.ClientListResponse)
async def get_clients(cur=Depends(get_db),current_user=Depends(require_permission("clients", "client", "read")),):
    try:
        data = await client_repository.list_clients(cur)

        return {
            "success": True,
            "message": "Clients retrieved successfully",
            "count": len(data),
            "data": data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )


#get client detail by single id
@router.get("/{client_id}", response_model=Client_schemas.ClientDetailResponse)
async def get_client(client_id: int,cur=Depends(get_db),current_user=Depends(require_permission("clients", "client", "read")),):
    try:
        data = await client_repository.get_client(cur, client_id)
        return Client_schemas.ClientDetailResponse(
            success=True,
            message="Client retrieved successfully",
            **data["client"],
            addresses=data["addresses"],
            pocs=data["pocs"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

#update client information including full_anme, type and status
@router.put("/{client_id}", response_model=Client_schemas.ClientDetailResponse)
async def update_client(
    client_id: int,
    payload: Client_schemas.ClientUpdateRequest,
    cur=Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        data = await client_repository.update_client(cur, client_id, payload, current_user["user_id"])
        return Client_schemas.ClientDetailResponse(
            success=True,
            message="Client updated successfully",
            **data["client"],
            addresses=data["addresses"],
            pocs=data["pocs"],
        )
    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
    
#update client address

@router.put("/{client_id}/addressess/{address_id}", response_model=Client_schemas.ClientDetailResponse)
async def update_address(client_id:int, address_id:int, payload: Client_schemas.ClientAddressUpdate, 
                         cur=Depends(get_db),current_user=Depends(get_current_user),):
    try:
        await client_repository.update_address(cur, client_id, address_id, payload, current_user["user_id"])
        data = await client_repository.fetch_client_detail(cur, client_id)
        return Client_schemas.ClientDetailResponse(
            success=True,
            message="Address updated successfully",
            **data["client"],
            addresses=data["addresses"],
            pocs=data["pocs"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
#uopdate poc detail endpoint

@router.put("/{client_id}/pocs/{poc_id}", response_model=Client_schemas.ClientDetailResponse)
async def update_poc(client_id:int, poc_id:int, payload: Client_schemas.ClientPOCUpdate, cur=Depends(get_db),
                     current_user=Depends(get_current_user),):
    try:
        await client_repository.update_poc(cur, client_id, poc_id, payload, current_user["user_id"])
        data = await client_repository.fetch_client_detail(cur, client_id)
        return Client_schemas.ClientDetailResponse(
            success=True,
            message="POC updated successfully",
            **data["client"],
            addresses=data["addresses"],
            pocs = data["pocs"],
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

#delete client softly
@router.delete("/{client_id}")
async def delete_client(
    client_id: int,
    cur=Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        result = await client_repository.delete_client(cur, client_id, current_user["user_id"])
        return {
            "success": True,
            "message": "Client deleted successfully",
            "client_id": result["client_id"],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
    
    
    