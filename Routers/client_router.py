from fastapi import APIRouter, HTTPException, Depends
from configurations.database import get_db
import schemas.client_schema as Client_schemas
from utilities.dependencies import get_current_user, require_permission
from repositories import client_repository

router = APIRouter(prefix="/client", tags=["Client"])


# ── 1. Create client ──
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


# ── 2. List all clients ──
@router.get("/", response_model=Client_schemas.ClientListResponse)
async def get_clients(
    cur=Depends(get_db),
    current_user=Depends(require_permission("clients", "client", "read")),
):
    try:
        data = await client_repository.list_clients(cur)
        return {
            "success": True,
            "message": "Clients retrieved successfully",
            "count": len(data),
            "data": data,
        }
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 3. Get client by ID ──
@router.get("/{client_id}", response_model=Client_schemas.ClientDetailResponse)
async def get_client(
    client_id: int,
    cur=Depends(get_db),
    current_user=Depends(require_permission("clients", "client", "read")),
):
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


# ── 4. Update client ──
@router.put("/{client_id}", response_model=Client_schemas.ClientDetailResponse)
async def update_client(
    client_id: int,
    payload: Client_schemas.ClientUpdateRequest,
    cur=Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await client_repository.update_client(cur, client_id, payload, current_user["user_id"])
        data = await client_repository.get_client(cur, client_id)

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


# ── 5. Delete client ──
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
    
    
    
    