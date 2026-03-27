import time
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from app.auth import verify_api_key
from app.services.parser_service import parse_pdf, ParseError
from app.services.response_transformer import transform_full, transform_summary
from app.services.planilha_transformer import transform_to_planilha

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])

MAX_SIZE = 16 * 1024 * 1024  # 16MB


async def _read_and_validate(file: UploadFile) -> bytes:
    if not file.filename:
        raise HTTPException(status_code=400, detail={
            "success": False, "message": "Empty filename", "error_code": "EMPTY_FILENAME",
        })
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail={
            "success": False, "message": "Only PDF files are allowed", "error_code": "INVALID_FILE_TYPE",
        })

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail={
            "success": False, "message": "File too large (max 16MB)", "error_code": "FILE_TOO_LARGE",
        })
    return content


def _parse_and_respond(content: bytes, transformer):
    start = time.time()
    try:
        raw = parse_pdf(content)
        data = transformer(raw)
        elapsed = int((time.time() - start) * 1000)
        return {
            "success": True,
            "message": "CNIS parsed successfully",
            "processing_time_ms": elapsed,
            "data": data,
        }
    except ParseError as e:
        elapsed = int((time.time() - start) * 1000)
        raise HTTPException(status_code=422, detail={
            "success": False,
            "message": str(e),
            "error_code": "PARSE_ERROR",
            "processing_time_ms": elapsed,
        })


@router.post("/parse")
async def parse_cnis(file: UploadFile = File(...)):
    """Parse CNIS PDF and return full structured data."""
    content = await _read_and_validate(file)
    return _parse_and_respond(content, transform_full)


@router.post("/parse/summary")
async def parse_cnis_summary(file: UploadFile = File(...)):
    """Parse CNIS PDF and return summary (without remuneracoes)."""
    content = await _read_and_validate(file)
    return _parse_and_respond(content, transform_summary)


@router.post("/parse/planilha")
async def parse_cnis_planilha(file: UploadFile = File(...)):
    """Parse CNIS PDF and return data in Planilha.spreadsheet_data schema."""
    content = await _read_and_validate(file)
    return _parse_and_respond(content, transform_to_planilha)
