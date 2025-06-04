from pydantic import BaseModel

class ParseWebsiteRequest(BaseModel):
    url: str
    max_depth: int = 3
    format: str = "graphml"

class ParseStatusResponse(BaseModel):
    status: str
    progress: int
    result: str | None = None