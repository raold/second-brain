"""
Base use case class.

Provides common functionality for all use cases.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.application.dependencies import Dependencies
from src.infrastructure.logging import get_logger

InputDTO = TypeVar("InputDTO")
OutputDTO = TypeVar("OutputDTO")

logger = get_logger(__name__)


class UseCase(ABC, Generic[InputDTO, OutputDTO]):
    """
    Abstract base class for use cases.
    
    Implements the command pattern for business logic.
    """
    
    def __init__(self, dependencies: Dependencies):
        """
        Initialize use case with dependencies.
        
        Args:
            dependencies: Dependency injection container
        """
        self.deps = dependencies
    
    @abstractmethod
    async def execute(self, request: InputDTO) -> OutputDTO:
        """
        Execute the use case.
        
        Args:
            request: Input DTO containing request data
            
        Returns:
            Output DTO containing response data
        """
        pass
    
    async def __call__(self, request: InputDTO) -> OutputDTO:
        """
        Make the use case callable.
        
        Args:
            request: Input DTO
            
        Returns:
            Output DTO
        """
        logger.info(
            f"Executing {self.__class__.__name__}",
            request_type=type(request).__name__,
        )
        
        try:
            result = await self.execute(request)
            
            logger.info(
                f"Successfully executed {self.__class__.__name__}",
                response_type=type(result).__name__,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Error executing {self.__class__.__name__}",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise