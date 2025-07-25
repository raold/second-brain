"""
Application use cases.

Contains the business logic for the application.
"""

from .memory_use_cases import (
    CreateMemoryUseCase,
    GetMemoryUseCase,
    UpdateMemoryUseCase,
    DeleteMemoryUseCase,
    SearchMemoriesUseCase,
    LinkMemoriesUseCase,
)
from .user_use_cases import (
    RegisterUserUseCase,
    LoginUserUseCase,
    GetUserUseCase,
    UpdateUserUseCase,
    DeleteUserUseCase,
)
from .session_use_cases import (
    CreateSessionUseCase,
    GetSessionUseCase,
    UpdateSessionUseCase,
    CloseSessionUseCase,
    AddMessageUseCase,
)
from .tag_use_cases import (
    CreateTagUseCase,
    GetTagUseCase,
    UpdateTagUseCase,
    DeleteTagUseCase,
    GetUserTagsUseCase,
)

__all__ = [
    # Memory use cases
    "CreateMemoryUseCase",
    "GetMemoryUseCase",
    "UpdateMemoryUseCase",
    "DeleteMemoryUseCase",
    "SearchMemoriesUseCase",
    "LinkMemoriesUseCase",
    
    # User use cases
    "RegisterUserUseCase",
    "LoginUserUseCase",
    "GetUserUseCase",
    "UpdateUserUseCase",
    "DeleteUserUseCase",
    
    # Session use cases
    "CreateSessionUseCase",
    "GetSessionUseCase",
    "UpdateSessionUseCase",
    "CloseSessionUseCase",
    "AddMessageUseCase",
    
    # Tag use cases
    "CreateTagUseCase",
    "GetTagUseCase",
    "UpdateTagUseCase",
    "DeleteTagUseCase",
    "GetUserTagsUseCase",
]