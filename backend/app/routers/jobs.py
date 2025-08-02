import logging
import traceback
from datetime import datetime
from typing import Union

from fastapi import APIRouter, HTTPException, Depends, Security
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user_models import User, WeixinUser
from app.models.meal_models import Meal
from app.models.task_models import Task, TaskStatus, TaskResponse, TaskStatusResponse, ProcessImageAsyncRequest
from app.storage.weixin_cloud_storage import WeixinCloudStorage
from app.utils.background_tasks import shutdown_background_tasks
from app.schemas.storage import TempUrlResponse
from app.dependencies import get_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


class TempUrlRequest(BaseModel):
    cloud_id: str


@router.post("/process-image-async", response_model=TaskResponse)
async def process_image_async(
    request: ProcessImageAsyncRequest,
    db: Session = Depends(get_db),
    current_user: Union[User, WeixinUser] = Security(get_current_user),
) -> TaskResponse:
    """Start an asynchronous task to process an image and return the task ID."""
    logger.info("Received async image processing request")
    
    try:
        # Check if the system is overloaded by counting active tasks
        active_tasks_count = db.query(Task.id).filter(
            Task.status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING])
        ).count()
        
        # Set a reasonable limit for concurrent tasks
        MAX_CONCURRENT_TASKS = 100
        if active_tasks_count >= MAX_CONCURRENT_TASKS:
            logger.warning(f"System is overloaded with {active_tasks_count} active tasks")
            raise HTTPException(
                status_code=503,
                detail="Server is currently overloaded. Please try again later."
            )
        
        # Create a new task in the database
        task = Task(
            task_type="process_image",
            status=TaskStatus.PENDING,
            progress=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            params={
                "file_id": request.file_id,
                "user_comment": request.user_comment,
                # We don't store the analysis in params as it could be large
            }
        )
        
        # Associate with the correct user type
        if isinstance(current_user, User):
            task.user_id = current_user.id
        else:
            task.weixin_user_id = current_user.id
            
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # The task processor thread will pick up this task from the database
        logger.info(f"Created task {task.id} in PENDING state")
        
        return task
        
    except Exception as e:
        logger.error(f"Error starting async image processing: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to start image processing task",
                "message": str(e),
                "type": type(e).__name__,
            },
        )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Union[User, WeixinUser] = Security(get_current_user),
) -> TaskStatusResponse:
    """
    Get the status of a task.
    
    Args:
        task_id: The ID of the task to get the status of
        
    Returns:
        TaskStatusResponse: The status of the task
    """
    logger.info(f"Getting status for task {task_id}")
    
    # Query for the task
    task = None
    if isinstance(current_user, User):
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.user_id == current_user.id
        ).first()
    else:
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.weixin_user_id == current_user.id
        ).first()
        
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found or you don't have permission to access it"
        )
    logger.info(f"Task {task_id} status: {task.status}")
    if task.status == TaskStatus.COMPLETED:
        try:
            task.result = Meal(**task.result).model_dump()
        except Exception as e:
            logger.error(f"Error parsing task result: {e}")
            task.result = None
            task.status = TaskStatus.FAILED
    return task


@router.post("/temp-url", response_model=TempUrlResponse)
async def get_temp_url(
    request: TempUrlRequest,
    current_user: Union[User, WeixinUser] = Security(get_current_user),
    storage: WeixinCloudStorage = Depends(get_storage),
):
    """Get a temporary download URL from a cloud id."""
    try:
        temp_url = storage.get_download_url(request.cloud_id)
        return TempUrlResponse(temp_url=temp_url)
    except Exception as e:
        logger.error(f"Failed to get temp url for {request.cloud_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get temp url")


# Add a shutdown event handler to stop the task processor thread
@router.on_event("shutdown")
def shutdown_event():
    logger.info("Shutting down task processor thread")
    shutdown_background_tasks()
