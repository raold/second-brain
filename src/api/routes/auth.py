"""
Authentication endpoints.

Handles user registration and login.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_dependencies
from src.application import Dependencies
from src.application.dto.user_dto import CreateUserDTO, LoginDTO, TokenDTO, UserDTO
from src.application.use_cases.user_use_cases import LoginUserUseCase, RegisterUserUseCase

router = APIRouter()


@router.post("/register", response_model=UserDTO, status_code=status.HTTP_201_CREATED)
async def register(
    request: CreateUserDTO,
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Register a new user.
    
    Creates a new user account with the provided information.
    """
    use_case = RegisterUserUseCase(deps)
    return await use_case(request)


@router.post("/login", response_model=TokenDTO)
async def login(
    request: LoginDTO,
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Login user.
    
    Authenticates user and returns access tokens.
    """
    use_case = LoginUserUseCase(deps)
    return await use_case(request)