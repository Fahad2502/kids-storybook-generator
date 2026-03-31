"""
models.py — Pydantic request/response models
"""
from typing import List, Optional
from pydantic import BaseModel


class StoryRequest(BaseModel):
    name:          str
    age:           int
    theme:         str
    length:        Optional[str] = "medium"   # short | medium | long
    gender:        Optional[str] = "boy"      # boy | girl | both
    extra_details: Optional[str] = None       # user's custom story details


class StoryPage(BaseModel):
    page_number:  int
    text:         str
    image_prompt: Optional[str] = ""


class StoryResponse(BaseModel):
    title:    str
    theme:    str
    pages:    List[StoryPage]
    story_id: Optional[int] = None

    class Config:
        extra = "allow"   # allows story_id, char_desc etc. to pass through
