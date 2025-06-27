from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from database.session import get_db
from schemas.template import (
    MessageTemplate, MessageTemplateCreate, MessageTemplateUpdate,
    TemplatePreviewRequest, TemplatePreviewResponse,
    TemplateRenderRequest, TemplateRenderResponse
)
from crud.template import (
    get_template_by_id, get_templates, create_template, update_template,
    soft_delete_template, restore_template, get_template_count
)
from services.template_service import (
    render_template_with_product, preview_template_with_product,
    get_template_placeholders, validate_template_content
)
from api.models.responses import SuccessResponse, PaginatedResponse, PaginationInfo, DeleteResponse
from exceptions.base import ValidationException
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/templates", tags=["Message Templates"])


def calculate_pagination(page: int, per_page: int, total: int) -> PaginationInfo:
    """Calculate pagination information."""
    pages = (total + per_page - 1) // per_page  # Ceiling division
    return PaginationInfo(
        page=page,
        per_page=per_page,
        total=total,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1
    )


@router.get("", response_model=PaginatedResponse[MessageTemplate])
async def list_templates(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    active_only: bool = Query(False, description="Return only active templates"),
    include_deleted: bool = Query(False, description="Include soft-deleted templates"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of message templates.
    
    Supports filtering by active status and including deleted templates.
    """
    logger.info(f"Fetching templates list - page: {page}, per_page: {per_page}")
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get templates
    templates = get_templates(
        db, 
        skip=offset, 
        limit=per_page, 
        include_deleted=include_deleted,
        active_only=active_only
    )
    
    # Get total count
    total = get_template_count(db, include_deleted=include_deleted, active_only=active_only)
    
    # Calculate pagination info
    pagination = calculate_pagination(page, per_page, total)
    
    logger.info(f"Retrieved {len(templates)} templates (page {page}/{pagination.pages})")
    
    return PaginatedResponse(
        data=templates,
        pagination=pagination,
        message=f"Retrieved {len(templates)} templates"
    )


@router.get("/{template_id}", response_model=SuccessResponse[MessageTemplate])
async def get_template(
    template_id: int = Path(..., ge=1, description="Template ID"),
    db: Session = Depends(get_db)
):
    """Get a specific template by ID."""
    logger.info(f"Fetching template with ID: {template_id}")
    
    template = get_template_by_id(db, template_id=template_id)
    if not template:
        logger.warning(f"Template not found with ID: {template_id}")
        raise HTTPException(status_code=404, detail="Template not found")
    
    logger.info(f"Retrieved template: {template.name}")
    
    return SuccessResponse(
        data=template,
        message="Template retrieved successfully"
    )


@router.post("", response_model=SuccessResponse[MessageTemplate])
async def create_new_template(
    template: MessageTemplateCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new message template.
    
    Template content can include placeholders like {product_name}, {product_price}, etc.
    """
    logger.info(f"Creating new template: {template.name}")
    
    try:
        # Validate template content
        validation_result = validate_template_content(template.template_content)
        if not validation_result["is_valid"]:
            raise ValidationException(
                message="Template contains invalid placeholders",
                details=validation_result
            )
        
        # Create template
        created_template = create_template(db=db, template=template)
        
        logger.info(f"Successfully created template with ID: {created_template.id}")
        
        return SuccessResponse(
            data=created_template,
            message="Template created successfully"
        )
        
    except ValidationException as e:
        logger.warning(f"Template validation failed: {e.message}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{template_id}", response_model=SuccessResponse[MessageTemplate])
async def update_existing_template(
    template_update: MessageTemplateUpdate,
    template_id: int = Path(..., ge=1, description="Template ID"),
    db: Session = Depends(get_db)
):
    """Update an existing template."""
    logger.info(f"Updating template with ID: {template_id}")
    
    try:
        # Validate template content if being updated
        if template_update.template_content:
            validation_result = validate_template_content(template_update.template_content)
            if not validation_result["is_valid"]:
                raise ValidationException(
                    message="Template contains invalid placeholders",
                    details=validation_result
                )
        
        # Check if template exists
        existing_template = get_template_by_id(db, template_id=template_id)
        if not existing_template:
            logger.warning(f"Template not found with ID: {template_id}")
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Update template
        updated_template = update_template(db=db, template_id=template_id, template_update=template_update)
        
        logger.info(f"Successfully updated template with ID: {template_id}")
        
        return SuccessResponse(
            data=updated_template,
            message="Template updated successfully"
        )
        
    except ValidationException as e:
        logger.warning(f"Template validation failed: {e.message}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{template_id}", response_model=DeleteResponse)
async def delete_template(
    template_id: int = Path(..., ge=1, description="Template ID"),
    db: Session = Depends(get_db)
):
    """Soft delete a template."""
    logger.info(f"Deleting template with ID: {template_id}")
    
    # Check if template exists
    existing_template = get_template_by_id(db, template_id=template_id)
    if not existing_template:
        logger.warning(f"Template not found with ID: {template_id}")
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Soft delete template
    success = soft_delete_template(db=db, template_id=template_id)
    if not success:
        logger.error(f"Failed to delete template with ID: {template_id}")
        raise HTTPException(status_code=500, detail="Failed to delete template")
    
    logger.info(f"Successfully deleted template with ID: {template_id}")
    
    return DeleteResponse(
        deleted_id=template_id,
        message="Template deleted successfully"
    )


@router.post("/{template_id}/restore", response_model=SuccessResponse[MessageTemplate])
async def restore_deleted_template(
    template_id: int = Path(..., ge=1, description="Template ID"),
    db: Session = Depends(get_db)
):
    """Restore a soft-deleted template."""
    logger.info(f"Restoring soft-deleted template with ID: {template_id}")
    
    # Check if template exists and is soft-deleted
    existing_template = get_template_by_id(db, template_id=template_id, include_deleted=True)
    if not existing_template:
        logger.warning(f"Template not found with ID: {template_id}")
        raise HTTPException(status_code=404, detail="Template not found")
    
    if existing_template.deleted_at is None:
        logger.warning(f"Template {template_id} is not soft-deleted")
        raise HTTPException(status_code=400, detail="Template is not deleted and cannot be restored")
    
    # Restore template
    success = restore_template(db=db, template_id=template_id)
    if not success:
        logger.error(f"Failed to restore template with ID: {template_id}")
        raise HTTPException(status_code=500, detail="Failed to restore template")
    
    # Get restored template
    restored_template = get_template_by_id(db, template_id=template_id)
    
    logger.info(f"Successfully restored template with ID: {template_id}")
    
    return SuccessResponse(
        data=restored_template,
        message="Template restored successfully"
    )


@router.post("/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    preview_request: TemplatePreviewRequest,
    db: Session = Depends(get_db)
):
    """
    Preview a template with a specific product to see how placeholders will be replaced.
    """
    logger.info(f"Previewing template with product ID: {preview_request.product_id}")
    
    try:
        result = preview_template_with_product(
            db=db,
            template_content=preview_request.template_content,
            product_id=preview_request.product_id
        )
        
        return TemplatePreviewResponse(
            rendered_content=result["rendered_content"],
            available_placeholders=result["available_placeholders"]
        )
        
    except ValidationException as e:
        logger.warning(f"Template preview failed: {e.message}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/render", response_model=TemplateRenderResponse)
async def render_template(
    render_request: TemplateRenderRequest,
    db: Session = Depends(get_db)
):
    """
    Render a template with a specific product.
    """
    logger.info(f"Rendering template ID {render_request.template_id} with product ID {render_request.product_id}")
    
    try:
        result = render_template_with_product(
            db=db,
            template_id=render_request.template_id,
            product_id=render_request.product_id
        )
        
        return TemplateRenderResponse(
            template_name=result["template_name"],
            rendered_content=result["rendered_content"],
            product_name=result["product_name"],
            product_url=result["product_url"]
        )
        
    except ValidationException as e:
        logger.warning(f"Template rendering failed: {e.message}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/placeholders/available", response_model=SuccessResponse[dict])
async def get_available_placeholders():
    """
    Get all available template placeholders with their descriptions.
    """
    logger.info("Fetching available template placeholders")
    
    placeholders = get_template_placeholders()
    
    return SuccessResponse(
        data={
            "placeholders": placeholders,
            "count": len(placeholders)
        },
        message=f"Retrieved {len(placeholders)} available placeholders"
    )


@router.post("/validate", response_model=SuccessResponse[dict])
async def validate_template(
    template_content: str = Query(..., description="Template content to validate")
):
    """
    Validate template content and check for invalid placeholders.
    """
    logger.info("Validating template content")
    
    validation_result = validate_template_content(template_content)
    
    return SuccessResponse(
        data=validation_result,
        message="Template validation completed"
    )