from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime, timezone

from models.template import MessageTemplate
from schemas.template import MessageTemplateCreate, MessageTemplateUpdate
from utils.logger import get_logger
from utils.database import atomic_transaction
from exceptions.base import DatabaseException, ValidationException

logger = get_logger(__name__)


def get_template_by_id(db: Session, template_id: int, include_deleted: bool = False) -> Optional[MessageTemplate]:
    """
    Get a template by its ID.
    
    Args:
        db: Database session
        template_id: Template ID to search for
        include_deleted: Whether to include soft-deleted templates
        
    Returns:
        Template instance if found, None otherwise
    """
    logger.debug(f"Searching for template with ID: {template_id}")

    try:
        query = db.query(MessageTemplate).filter(MessageTemplate.id == template_id)

        if not include_deleted:
            query = query.filter(MessageTemplate.deleted_at.is_(None))

        template = query.first()

        if template:
            logger.debug(f"Found template: {template.name}")
        else:
            logger.debug(f"No template found for ID: {template_id}")

        return template

    except Exception as e:
        logger.error(f"Error retrieving template by ID {template_id}: {e}")
        raise DatabaseException(
            message="Failed to retrieve template by ID",
            operation="get_template_by_id",
            table="message_templates",
            details={"template_id": template_id},
            original_exception=e
        )


def get_template_by_name(db: Session, name: str, include_deleted: bool = False) -> Optional[MessageTemplate]:
    """
    Get a template by its name.
    
    Args:
        db: Database session
        name: Template name to search for
        include_deleted: Whether to include soft-deleted templates
        
    Returns:
        Template instance if found, None otherwise
    """
    logger.debug(f"Searching for template with name: {name}")

    try:
        query = db.query(MessageTemplate).filter(MessageTemplate.name == name)

        if not include_deleted:
            query = query.filter(MessageTemplate.deleted_at.is_(None))

        template = query.first()

        if template:
            logger.debug(f"Found template with ID: {template.id}")
        else:
            logger.debug(f"No template found for name: {name}")

        return template

    except Exception as e:
        logger.error(f"Error retrieving template by name {name}: {e}")
        raise DatabaseException(
            message="Failed to retrieve template by name",
            operation="get_template_by_name",
            table="message_templates",
            details={"name": name},
            original_exception=e
        )


def get_templates(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        active_only: bool = False
) -> List[MessageTemplate]:
    """
    Get a list of templates with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        include_deleted: Whether to include soft-deleted templates
        active_only: Whether to return only active templates
        
    Returns:
        List of templates
    """
    logger.debug(f"Fetching templates with skip={skip}, limit={limit}")

    try:
        query = db.query(MessageTemplate)

        if not include_deleted:
            query = query.filter(MessageTemplate.deleted_at.is_(None))

        if active_only:
            query = query.filter(MessageTemplate.is_active == True)

        # Order by updated_at desc to show most recently modified first
        query = query.order_by(MessageTemplate.updated_at.desc())

        templates = query.offset(skip).limit(limit).all()
        logger.debug(f"Retrieved {len(templates)} templates")

        return templates

    except Exception as e:
        logger.error(f"Error retrieving templates: {e}")
        raise DatabaseException(
            message="Failed to retrieve templates list",
            operation="get_templates",
            table="message_templates",
            details={"skip": skip, "limit": limit},
            original_exception=e
        )


def create_template(db: Session, template: MessageTemplateCreate) -> MessageTemplate:
    """
    Create a new message template.
    
    Args:
        db: Database session
        template: Template data to create
        
    Returns:
        Created template instance
        
    Raises:
        ValidationException: If template data validation fails
        DatabaseException: If database operation fails
    """
    logger.info(f"Creating template: {template.name}")

    try:
        with atomic_transaction(db):
            # Check if template with same name already exists
            existing_template = get_template_by_name(db, template.name)
            if existing_template:
                raise ValidationException(
                    message="Template with this name already exists",
                    details={"name": template.name, "existing_id": existing_template.id}
                )

            # Create the template
            db_template = MessageTemplate(
                name=template.name,
                description=template.description,
                template_content=template.template_content,
                is_active=template.is_active
            )

            db.add(db_template)
            db.flush()

            logger.info(f"Successfully created template with ID: {db_template.id}")

    except ValidationException:
        raise  # Re-raise validation exceptions
    except IntegrityError as e:
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)

        if "UNIQUE constraint failed: message_templates.name" in error_msg:
            raise ValidationException(
                message="Template name already exists",
                details={"name": template.name},
                original_exception=e
            )
        else:
            raise DatabaseException(
                message="Database constraint violation during template creation",
                operation="create_template",
                table="message_templates",
                details={"name": template.name, "error": error_msg},
                original_exception=e
            )
    except Exception as e:
        raise DatabaseException(
            message="Failed to create template",
            operation="create_template",
            table="message_templates",
            details={"name": template.name},
            original_exception=e
        )

    return db_template


def update_template(db: Session, template_id: int, template_update: MessageTemplateUpdate) -> MessageTemplate:
    """
    Update an existing template.
    
    Args:
        db: Database session
        template_id: ID of the template to update
        template_update: Template data to update
        
    Returns:
        Updated template instance
        
    Raises:
        ValidationException: If template not found or update fails
        DatabaseException: If database operation fails
    """
    logger.info(f"Updating template with ID: {template_id}")

    try:
        with atomic_transaction(db):
            # Get existing template
            template = get_template_by_id(db, template_id)
            if not template:
                raise ValidationException(
                    message="Template not found for update",
                    details={"template_id": template_id}
                )

            # Update fields that are provided (not None)
            update_data = template_update.model_dump(exclude_unset=True, exclude_none=True)

            if update_data:
                # Check for name uniqueness if name is being updated
                if 'name' in update_data and update_data['name'] != template.name:
                    existing_template = get_template_by_name(db, update_data['name'])
                    if existing_template and existing_template.id != template_id:
                        raise ValidationException(
                            message="Template name already exists",
                            details={"name": update_data['name'], "existing_id": existing_template.id}
                        )

                # Apply updates
                for field, value in update_data.items():
                    setattr(template, field, value)

                # Update the updated_at timestamp manually since we're not using onupdate
                template.updated_at = datetime.now(timezone.utc)

                db.flush()
                logger.debug(f"Updated template fields: {list(update_data.keys())}")

    except ValidationException:
        raise  # Re-raise validation exceptions
    except IntegrityError as e:
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)

        if "UNIQUE constraint failed: message_templates.name" in error_msg:
            raise ValidationException(
                message="Template name already exists",
                details={"template_id": template_id},
                original_exception=e
            )
        else:
            raise DatabaseException(
                message="Database constraint violation during template update",
                operation="update_template",
                table="message_templates",
                details={"template_id": template_id, "error": error_msg},
                original_exception=e
            )
    except Exception as e:
        raise DatabaseException(
            message="Failed to update template",
            operation="update_template",
            table="message_templates",
            details={"template_id": template_id},
            original_exception=e
        )

    logger.info(f"Successfully updated template ID: {template_id}")
    return template


def soft_delete_template(db: Session, template_id: int) -> bool:
    """
    Soft delete a template by setting deleted_at timestamp.
    
    Args:
        db: Database session
        template_id: ID of the template to soft delete
        
    Returns:
        True if soft deletion was successful
        
    Raises:
        ValidationException: If template not found
        DatabaseException: If database operation fails
    """
    logger.info(f"Soft deleting template with ID: {template_id}")

    try:
        with atomic_transaction(db):
            # Get existing template (including already soft-deleted ones)
            template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
            if not template:
                raise ValidationException(
                    message="Template not found for soft deletion",
                    details={"template_id": template_id}
                )

            # Check if already soft deleted
            if template.deleted_at is not None:
                logger.warning(f"Template {template_id} is already soft deleted at {template.deleted_at}")
                return True

            # Soft delete the template
            template.deleted_at = datetime.now(timezone.utc)
            template.is_active = False  # Also mark as inactive
            db.flush()

            logger.info(f"Successfully soft deleted template ID: {template_id}")

        return True

    except ValidationException:
        raise  # Re-raise validation exceptions
    except Exception as e:
        logger.error(f"Error soft deleting template {template_id}: {e}")
        raise DatabaseException(
            message="Failed to soft delete template",
            operation="soft_delete_template",
            table="message_templates",
            details={"template_id": template_id},
            original_exception=e
        )


def restore_template(db: Session, template_id: int) -> bool:
    """
    Restore a soft-deleted template.
    
    Args:
        db: Database session
        template_id: ID of the template to restore
        
    Returns:
        True if restoration was successful
        
    Raises:
        ValidationException: If template not found or not soft deleted
        DatabaseException: If database operation fails
    """
    logger.info(f"Restoring soft-deleted template with ID: {template_id}")

    try:
        with atomic_transaction(db):
            # Get soft-deleted template
            template = db.query(MessageTemplate).filter(
                MessageTemplate.id == template_id,
                MessageTemplate.deleted_at.isnot(None)
            ).first()

            if not template:
                # Check if template exists but is not soft deleted
                existing_template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
                if existing_template:
                    raise ValidationException(
                        message="Template is not soft deleted and cannot be restored",
                        details={"template_id": template_id}
                    )
                else:
                    raise ValidationException(
                        message="Template not found for restoration",
                        details={"template_id": template_id}
                    )

            # Restore the template
            template.deleted_at = None
            template.is_active = True  # Also mark as active
            db.flush()

            logger.info(f"Successfully restored template ID: {template_id}")

        return True

    except ValidationException:
        raise  # Re-raise validation exceptions
    except Exception as e:
        logger.error(f"Error restoring template {template_id}: {e}")
        raise DatabaseException(
            message="Failed to restore template",
            operation="restore_template",
            table="message_templates",
            details={"template_id": template_id},
            original_exception=e
        )


def get_template_count(db: Session, include_deleted: bool = False, active_only: bool = False) -> int:
    """
    Get the total count of templates.
    
    Args:
        db: Database session
        include_deleted: Whether to include soft-deleted templates
        active_only: Whether to count only active templates
        
    Returns:
        Total number of templates
    """
    try:
        query = db.query(MessageTemplate)

        if not include_deleted:
            query = query.filter(MessageTemplate.deleted_at.is_(None))

        if active_only:
            query = query.filter(MessageTemplate.is_active == True)

        count = query.count()
        logger.debug(f"Total template count: {count}")
        return count
    except Exception as e:
        logger.error(f"Error getting template count: {e}")
        raise DatabaseException(
            message="Failed to get template count",
            operation="get_template_count",
            table="message_templates",
            original_exception=e
        )
