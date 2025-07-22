"""
Pydantic models for pagination system.
"""

from typing import Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

T = TypeVar('T')


class PaginationDirection(str, Enum):
    """Direction of pagination"""
    FORWARD = "forward"
    BACKWARD = "backward"


class PaginationParams(BaseModel):
    """Standard pagination parameters for API requests"""
    
    # Traditional pagination (will be deprecated)
    limit: int = Field(default=50, ge=1, le=1000, description="Number of items per page")
    offset: Optional[int] = Field(default=0, ge=0, description="Number of items to skip")
    
    # Cursor pagination
    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    direction: PaginationDirection = Field(
        default=PaginationDirection.FORWARD,
        description="Direction of pagination"
    )
    
    # Keyset pagination
    after_id: Optional[str] = Field(None, description="ID to start after (exclusive)")
    before_id: Optional[str] = Field(None, description="ID to start before (exclusive)")
    
    # Sorting
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field(default="desc", regex="^(asc|desc)$", description="Sort order")
    
    # Filtering hints for optimization
    include_total: bool = Field(
        default=False, 
        description="Include total count (expensive for large datasets)"
    )
    
    @validator('limit')
    def validate_limit(cls, v):
        """Ensure reasonable limits for performance"""
        if v > 100:
            # Log warning for large limits
            pass
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "limit": 50,
                "cursor": "eyJpZCI6ICIxMjM0NSIsICJ0cyI6ICIyMDI0LTAxLTE1VDEwOjAwOjAwWiJ9",
                "direction": "forward",
                "sort_by": "created_at",
                "sort_order": "desc"
            }
        }


class PageInfo(BaseModel):
    """Information about the current page"""
    has_next_page: bool = Field(..., description="Whether there are more items after this page")
    has_previous_page: bool = Field(..., description="Whether there are items before this page")
    start_cursor: Optional[str] = Field(None, description="Cursor of the first item in the page")
    end_cursor: Optional[str] = Field(None, description="Cursor of the last item in the page")
    
    class Config:
        schema_extra = {
            "example": {
                "has_next_page": True,
                "has_previous_page": False,
                "start_cursor": "eyJpZCI6ICIxMDAwMCIsICJ0cyI6ICIyMDI0LTAxLTE1VDEwOjAwOjAwWiJ9",
                "end_cursor": "eyJpZCI6ICIxMDA1MCIsICJ0cyI6ICIyMDI0LTAxLTE1VDEwOjMwOjAwWiJ9"
            }
        }


class PaginationMetadata(BaseModel):
    """Comprehensive pagination metadata"""
    page_info: PageInfo
    total_count: Optional[int] = Field(None, description="Total number of items (if requested)")
    page_size: int = Field(..., description="Number of items in this page")
    
    # Performance metrics
    query_time_ms: Optional[float] = Field(None, description="Query execution time in milliseconds")
    
    # Navigation helpers
    first_page_url: Optional[str] = Field(None, description="URL to fetch the first page")
    last_page_url: Optional[str] = Field(None, description="URL to fetch the last page")
    next_page_url: Optional[str] = Field(None, description="URL to fetch the next page")
    previous_page_url: Optional[str] = Field(None, description="URL to fetch the previous page")
    
    class Config:
        schema_extra = {
            "example": {
                "page_info": {
                    "has_next_page": True,
                    "has_previous_page": True,
                    "start_cursor": "cursor_start",
                    "end_cursor": "cursor_end"
                },
                "total_count": 10000,
                "page_size": 50,
                "query_time_ms": 45.2,
                "next_page_url": "/api/memories?cursor=cursor_end&direction=forward",
                "previous_page_url": "/api/memories?cursor=cursor_start&direction=backward"
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper"""
    data: List[T] = Field(..., description="The page of items")
    pagination: PaginationMetadata = Field(..., description="Pagination metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "data": ["...items..."],
                "pagination": {
                    "page_info": {
                        "has_next_page": True,
                        "has_previous_page": False
                    },
                    "page_size": 50
                }
            }
        }


class CursorData(BaseModel):
    """Data encoded in a cursor"""
    id: str = Field(..., description="Primary key of the item")
    timestamp: datetime = Field(..., description="Timestamp for stable ordering")
    sort_value: Optional[Any] = Field(None, description="Value of the sort field")
    
    def encode(self) -> str:
        """Encode cursor data to base64 string"""
        import base64
        import json
        
        data = {
            "id": self.id,
            "ts": self.timestamp.isoformat(),
            "sv": self.sort_value
        }
        
        json_str = json.dumps(data, separators=(',', ':'))
        return base64.urlsafe_b64encode(json_str.encode()).decode()
    
    @classmethod
    def decode(cls, cursor: str) -> 'CursorData':
        """Decode cursor from base64 string"""
        import base64
        import json
        
        try:
            json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
            data = json.loads(json_str)
            
            return cls(
                id=data["id"],
                timestamp=datetime.fromisoformat(data["ts"]),
                sort_value=data.get("sv")
            )
        except Exception as e:
            raise ValueError(f"Invalid cursor format: {e}")


class KeysetData(BaseModel):
    """Data for keyset pagination"""
    columns: Dict[str, Any] = Field(..., description="Column values for keyset")
    direction: PaginationDirection = Field(..., description="Direction of pagination")
    
    def to_where_clause(self, table_alias: str = "") -> tuple[str, List[Any]]:
        """Convert to SQL WHERE clause for keyset pagination"""
        if not self.columns:
            return "", []
        
        conditions = []
        values = []
        
        # Build compound comparison for keyset
        # Example: (created_at, id) > ('2024-01-15', '12345')
        col_names = list(self.columns.keys())
        col_values = list(self.columns.values())
        
        if table_alias:
            qualified_cols = [f"{table_alias}.{col}" for col in col_names]
        else:
            qualified_cols = col_names
        
        # Create tuple comparison
        if self.direction == PaginationDirection.FORWARD:
            op = ">"
        else:
            op = "<"
        
        condition = f"({', '.join(qualified_cols)}) {op} ({', '.join(['%s'] * len(col_values))})"
        
        return condition, col_values