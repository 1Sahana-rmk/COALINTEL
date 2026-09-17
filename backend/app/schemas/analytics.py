from typing import List
from pydantic import BaseModel, ConfigDict


class WordCloudTopicItem(BaseModel):
    word: str
    weight: int
    category: str


class WordCloudResponse(BaseModel):
    topics: List[WordCloudTopicItem]

    model_config = ConfigDict(from_attributes=True)
