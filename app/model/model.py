import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class QuestionRequest(BaseModel):
   question: str
   session_id: Optional[str] = None
   language: Optional[str] = "ru"

 
class ResponseFormat(BaseModel):
   response: str
   category: int


class CategoryCreate(BaseModel):
   category_name: str = Field(..., min_length=1, max_length=255, description="Name of the category")


class CategoryUpdate(BaseModel):
   category_id: int = Field(..., gt=0, description="ID of the category")
   category_name: str = Field(..., min_length=1, max_length=255, description="New name of the category")


class FileCreate(BaseModel):
   file_name: str = Field(..., min_length=1, max_length=255, description="Name of the file")
   category_id: int = Field(..., gt=0, description="ID of the category this file belongs to")


class TextCreate(BaseModel):
   question: str = Field(..., description="The question content")
   answer: str = Field(..., description="The answer content")
   text_author: str = Field(..., min_length=1, description="The author of the text entry")
   

class TextCreateBatch(BaseModel):
   texts: List[TextCreate] = Field(..., description="List of text entries to create")


class TextUpdate(BaseModel):
   text_id: str = Field(..., description="The text ID to update")
   question: str = Field(..., description="The question content")
   answer: str = Field(..., description="The answer content")
   text_author: str = Field(..., min_length=1, description="The author of the text entry")


class TextUpdateBatch(BaseModel):
   texts: List[TextUpdate] = Field(..., description="List of text entries to update")


class TextDelete(BaseModel):
   text_id: str = Field(..., description="The text ID to delete")


class TextDeleteBatch(BaseModel):
   text_ids: List[str] = Field(..., description="List of text IDs to delete")


class CategoryResponse(BaseModel):
   category_id: int
   category_name: str
   files: List[Dict[str, Any]]


class TextResponse(BaseModel):
   text_id: str
   question: str
   answer: str
   text_author: str
   file_name: str
   created_at: datetime.datetime
   updated_at: datetime.datetime


class FileTextsResponse(BaseModel):
   file_id: int
   file_name: str
   texts: List[TextResponse]
   total_count: int


class SearchResponse(BaseModel):
   query: str
   texts: List[TextResponse]
   current_page: int
   page_size: int
   total_texts: int
   

class IncidentResponse(BaseModel):
   incident_id: int
   incident_name: str
   incident_description: str
   incident_script: str
   incident_startdate: datetime.datetime
   incident_enddate: datetime.datetime
   

class IncidentCreate(BaseModel):
   incident_name: str
   incident_description: str
   incident_script: str
   incident_startdate: datetime.datetime
   incident_enddate: datetime.datetime


class IncidentUpdate(BaseModel):
   incident_id: int
   incident_name: Optional[str] = None
   incident_description: Optional[str] = None
   incident_script: Optional[str] = None
   incident_startdate: Optional[datetime.datetime] = None
   incident_enddate: Optional[datetime.datetime] = None