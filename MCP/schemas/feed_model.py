from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict
from collections import defaultdict

class FeedMetadata(BaseModel):
	model_config = ConfigDict(extra="ignore")
    
	title: str
	link: str

class FeedMetadataResponse(BaseModel):
	model_config = ConfigDict(extra="ignore")

	result: Dict[str, List[FeedMetadata]] = Field(
        default_factory=lambda: defaultdict(list)
    )

class StrList(BaseModel):
	results: List[str]
