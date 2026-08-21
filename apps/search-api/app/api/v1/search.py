from fastapi import APIRouter, Request, Response

from app.services.search_service import REQUEST_ID_HEADER, search_assets


router = APIRouter()


@router.get("/")
async def search(request: Request, response: Response) -> dict:
    """Delegate governed-discovery filters to the authoritative catalog API."""
    result, upstream_request_id = await search_assets(
        dict(request.query_params),
        request.headers.get("Authorization"),
        request.headers.get(REQUEST_ID_HEADER),
    )
    if upstream_request_id:
        response.headers[REQUEST_ID_HEADER] = upstream_request_id
    return result
