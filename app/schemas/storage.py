from pydantic import BaseModel, Field

class TempUrlResponse(BaseModel):
    temp_url: str = Field(..., description="Temporary download URL for the cloud file") 