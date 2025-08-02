import logging
import os
import threading
import traceback
import asyncio
import time
import json
import concurrent.futures
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.meal_models import Meal
from app.models.task_models import Task, TaskStatus
from app.utils.gpt_client import GPTClient
from app.utils.food_analyzer import analyze_food_image
from app.storage.weixin_cloud_storage import WeixinCloudStorage

logger = logging.getLogger(__name__)

# Create a thread pool executor for processing tasks
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# Flag to control the task processor thread
task_processor_running = True

# --- Nutrition lookup loaded once at module level ---
try:
    with open("app/data/ingredients.json", "r", encoding="utf-8") as f:
        _nutrition_data = json.load(f)
    _nutrition_lookup = {}
    for item in _nutrition_data:
        aliases = item.get("aliases", [])
        for alias in aliases:
            _nutrition_lookup[alias] = item
    for item in _nutrition_lookup.values():
        if "carbos" in item:
            item["carbs_per_100g"] = item.pop("carbos")
except Exception as e:
    logger.error(f"Failed to load nutrition data: {str(e)}")
    _nutrition_lookup = {}

def get_nutrition_lookup():
    """Return the nutrition lookup dictionary loaded from ingredients.json."""
    return _nutrition_lookup

# Function to process tasks from the database
def process_pending_tasks():
    """Background thread that continuously processes pending tasks from the database."""
    logger.info(f"Starting task processor thread - Process ID: {os.getpid()}, Thread ID: {threading.get_ident()}")
    
    while task_processor_running:
        try:
            # Create a new database session for this iteration
            from app.database.database import SessionLocal
            db = SessionLocal()
            
            try:
                # Find the oldest pending task
                task = db.query(Task).filter(
                    Task.status == TaskStatus.PENDING
                ).order_by(Task.created_at).first()
                
                if task:
                    logger.info(f"Found pending task {task.id} to process")
                    
                    # Get the task parameters
                    params = task.params or {}
                    file_id = params.get("file_id")
                    user_comment = params.get("user_comment")
                    
                    if file_id:
                        # Submit the task to the thread pool
                        thread_pool.submit(
                            process_image_background_thread,
                            task_id=task.id,
                            file_id=file_id,
                            user_comment=user_comment
                        )
                    else:
                        # Mark the task as failed if it doesn't have required parameters
                        task.update_status(
                            TaskStatus.FAILED, 
                            error="Missing required parameters"
                        )
                        db.commit()
                
            finally:
                # Always close the database session
                db.close()
                
            # Sleep for a short time before checking for more tasks
            # This prevents excessive database queries
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in task processor thread: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Sleep a bit longer after an error to prevent rapid failure loops
            time.sleep(5)


# Function to process image in a background thread
def process_image_background_thread(
    task_id: int,
    file_id: str,
    analysis: Optional[Meal] = None,
    user_comment: Optional[str] = None,
):
    """Background task for processing an image, designed to run in a separate thread."""
    logger.info(f"Starting threaded background task for image processing: {task_id} - Process ID: {os.getpid()}, Thread ID: {threading.get_ident()}")
    
    # Create new database session
    from app.database.database import SessionLocal
    db = SessionLocal()
    
    # Create new GPT client
    gpt_client = GPTClient()
    
    # Create new storage client
    from app.dependencies import get_storage
    storage = get_storage()
    
    try:
        # Get task from database
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found")
            return
        
        # Update task status to processing
        task.update_status(TaskStatus.PROCESSING, progress=10)
        db.commit()
        logger.info(f"Task {task_id} updated: status={task.status}, progress={task.progress}")
        
        # Process image URL
        if file_id.startswith("cloud://"):
            img_url = storage.get_download_url(file_id)
        else:
            img_url = file_id
            
        # Update progress
        task.update_status(TaskStatus.PROCESSING, progress=20)
        db.commit()
        
        # Prepare context if needed
        context = None
        if analysis or user_comment:
            context = {}
            if analysis:
                context["previous_analysis"] = analysis.model_dump()
            if user_comment:
                context["user_comment"] = user_comment
                
        # Update progress
        task.update_status(TaskStatus.PROCESSING, progress=30)
        db.commit()
        
        # First get ingredients analysis using asyncio.run
        gpt_analysis = asyncio.run(analyze_food_image(img_url, gpt_client, context))

        # Use nutrition lookup loaded at module level
        nutrition_lookup = get_nutrition_lookup()

        # Replace nutrition info for known ingredients
        if gpt_analysis and "ingredients" in gpt_analysis:
            for ing in gpt_analysis["ingredients"]:
                name = ing.get("name")
                if name in nutrition_lookup:
                    logger.info(f"Found nutrition data for {name} in lookup")
                    lookup = nutrition_lookup[name]
                    ing["gi"] = lookup.get("gi", ing.get("gi"))
                    ing["carbs_per_100g"] = lookup.get("carbs_per_100g", ing.get("carbs_per_100g"))
                    ing["protein_per_100g"] = lookup.get("protein_per_100g", ing.get("protein_per_100g"))
                    ing["fat_per_100g"] = lookup.get("fat_per_100g", ing.get("fat_per_100g"))

        # Update progress
        task.update_status(TaskStatus.PROCESSING, progress=50)
        db.commit()
        
        # Then get meal notes with the ingredients analysis as context
        # notes = gpt_analysis["notes"]
        
        # Update progress
        # task.update_status(TaskStatus.PROCESSING, progress=90)
        # db.commit()
            
        # Create meal response
        # meal = {
        #     "ingredients": ingredients,
        #     "notes": notes,
        # }
        
        # Update task with result
        task.update_status(TaskStatus.COMPLETED, progress=100, result=gpt_analysis)
        db.commit()
        
        logger.info(f"Successfully completed threaded background task for image processing: {task_id}")
            
    except Exception as e:
        logger.error(f"Threaded background task error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Update task status to failed
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.update_status(TaskStatus.FAILED, error=str(e))
                db.commit()
        except Exception as inner_e:
            logger.error(f"Failed to update task status: {str(inner_e)}")
    finally:
        # Always close the database session
        db.close()


# Start the task processor thread when the module is loaded
task_processor_thread = threading.Thread(target=process_pending_tasks, daemon=True)
task_processor_thread.start()


def shutdown_background_tasks():
    """Shutdown the background task processor thread and thread pool."""
    global task_processor_running
    logger.info("Shutting down task processor thread")
    task_processor_running = False
    # Wait for the thread pool to complete all tasks
    thread_pool.shutdown(wait=True) 