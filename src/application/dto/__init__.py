"""
Data Transfer Objects (DTOs) for the application layer.

DTOs are used to transfer data between layers and external APIs.
"""

from .memory_dto import (
    CreateMemoryDTO,
    UpdateMemoryDTO,
    MemoryDTO,
    MemoryListDTO,
)
from .user_dto import (
    CreateUserDTO,
    UpdateUserDTO,
    UserDTO,
    LoginDTO,
    TokenDTO,
)
from .session_dto import (
    CreateSessionDTO,
    UpdateSessionDTO,
    SessionDTO,
    SessionListDTO,
    AddMessageDTO,
)
from .tag_dto import (
    CreateTagDTO,
    UpdateTagDTO,
    TagDTO,
    TagListDTO,
)

__all__ = [
    # Memory DTOs
    "CreateMemoryDTO",
    "UpdateMemoryDTO",
    "MemoryDTO",
    "MemoryListDTO",
    
    # User DTOs
    "CreateUserDTO",
    "UpdateUserDTO",
    "UserDTO",
    "LoginDTO",
    "TokenDTO",
    
    # Session DTOs
    "CreateSessionDTO",
    "UpdateSessionDTO",
    "SessionDTO",
    "SessionListDTO",
    "AddMessageDTO",
    
    # Tag DTOs
    "CreateTagDTO",
    "UpdateTagDTO",
    "TagDTO",
    "TagListDTO",
]