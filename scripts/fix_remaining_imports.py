#!/usr/bin/env python3
"""
Fix remaining import issues based on common patterns
"""

import re
import subprocess


def fix_missing_imports():
    """Fix remaining import issues"""

    # Run docker logs to find errors
    print("Checking for import errors...")
    while True:
        # Restart container
        subprocess.run(["docker", "restart", "secondbrain-app"], capture_output=True)
        import time
        time.sleep(5)

        # Get logs
        result = subprocess.run(
            ["docker", "logs", "secondbrain-app", "--tail", "50"],
            capture_output=True,
            text=True
        )

        # Look for NameError in both stdout and stderr
        output = result.stdout + result.stderr
        error_match = re.search(r'NameError: name \'(\w+)\' is not defined', output)
        if not error_match:
            print("No more NameErrors found!")
            break

        missing_name = error_match.group(1)

        # Find the file with the error
        file_match = re.search(r'File "(/app/[^"]+)", line \d+', output)
        if not file_match:
            print(f"Could not find file for error: {missing_name}")
            break

        error_file = file_match.group(1).replace('/app/', '/Users/dro/Documents/second-brain/')

        print(f"\nFound missing import: {missing_name} in {error_file}")

        # Common imports to try
        import_map = {
            # Typing imports
            'TypeVar': 'from typing import TypeVar',
            'Generic': 'from typing import Generic',
            'Protocol': 'from typing import Protocol',
            'Callable': 'from typing import Callable',
            'Optional': 'from typing import Optional',
            'Dict': 'from typing import Dict',
            'List': 'from typing import List',
            'Any': 'from typing import Any',
            'Union': 'from typing import Union',
            'Tuple': 'from typing import Tuple',
            'Set': 'from typing import Set',
            'AsyncIterable': 'from typing import AsyncIterable',
            'Awaitable': 'from typing import Awaitable',
            'Iterable': 'from typing import Iterable',
            'Iterator': 'from typing import Iterator',
            'Type': 'from typing import Type',
            'cast': 'from typing import cast',
            'overload': 'from typing import overload',
            'Final': 'from typing import Final',
            'Literal': 'from typing import Literal',
            'ClassVar': 'from typing import ClassVar',

            # Standard library
            'ABC': 'from abc import ABC',
            'abstractmethod': 'from abc import abstractmethod',
            'dataclass': 'from dataclasses import dataclass',
            'field': 'from dataclasses import field',
            'Enum': 'from enum import Enum',
            'datetime': 'from datetime import datetime',
            'timedelta': 'from datetime import timedelta',
            'date': 'from datetime import date',
            'time': 'from datetime import time',
            'timezone': 'from datetime import timezone',
            'defaultdict': 'from collections import defaultdict',
            'Counter': 'from collections import Counter',
            'deque': 'from collections import deque',
            'OrderedDict': 'from collections import OrderedDict',
            'ChainMap': 'from collections import ChainMap',
            'namedtuple': 'from collections import namedtuple',
            'lru_cache': 'from functools import lru_cache',
            'partial': 'from functools import partial',
            'wraps': 'from functools import wraps',
            'reduce': 'from functools import reduce',
            'cached_property': 'from functools import cached_property',
            'singledispatch': 'from functools import singledispatch',
            're': 'import re',
            'json': 'import json',
            'os': 'import os',
            'sys': 'import sys',
            'asyncio': 'import asyncio',
            'threading': 'import threading',
            'multiprocessing': 'import multiprocessing',
            'subprocess': 'import subprocess',
            'logging': 'import logging',
            'hashlib': 'import hashlib',
            'uuid': 'import uuid',
            'random': 'import random',
            'math': 'import math',
            'statistics': 'import statistics',
            'itertools': 'import itertools',
            'contextlib': 'import contextlib',
            'pathlib': 'import pathlib',
            'Path': 'from pathlib import Path',
            'io': 'import io',
            'csv': 'import csv',
            'pickle': 'import pickle',
            'base64': 'import base64',
            'urllib': 'import urllib',
            'http': 'import http',
            'socket': 'import socket',
            'ssl': 'import ssl',
            'email': 'import email',
            'html': 'import html',
            'xml': 'import xml',
            'sqlite3': 'import sqlite3',
            'decimal': 'import decimal',
            'fractions': 'import fractions',
            'copy': 'import copy',
            'deepcopy': 'from copy import deepcopy',
            'pprint': 'import pprint',
            'traceback': 'import traceback',
            'inspect': 'import inspect',
            'warnings': 'import warnings',
            'weakref': 'import weakref',
            'gc': 'import gc',
            'atexit': 'import atexit',
            'signal': 'import signal',
            'errno': 'import errno',
            'tempfile': 'import tempfile',
            'shutil': 'import shutil',
            'glob': 'import glob',
            'fnmatch': 'import fnmatch',
            'zipfile': 'import zipfile',
            'tarfile': 'import tarfile',
            'configparser': 'import configparser',
            'argparse': 'import argparse',
            'getopt': 'import getopt',
            'readline': 'import readline',
            'rlcompleter': 'import rlcompleter',
            'pdb': 'import pdb',
            'profile': 'import profile',
            'cProfile': 'import cProfile',
            'timeit': 'import timeit',
            'time': 'import time',

            # Third party
            'asyncpg': 'import asyncpg',
            'HTTPException': 'from fastapi import HTTPException',
            'APIRouter': 'from fastapi import APIRouter',
            'Depends': 'from fastapi import Depends',
            'Query': 'from fastapi import Query',
            'Body': 'from fastapi import Body',
            'Path': 'from fastapi import Path',
            'Header': 'from fastapi import Header',
            'Cookie': 'from fastapi import Cookie',
            'File': 'from fastapi import File',
            'Form': 'from fastapi import Form',
            'UploadFile': 'from fastapi import UploadFile',
            'status': 'from fastapi import status',
            'BackgroundTasks': 'from fastapi import BackgroundTasks',
            'Request': 'from fastapi import Request',
            'Response': 'from fastapi import Response',
            'WebSocket': 'from fastapi import WebSocket',
            'WebSocketDisconnect': 'from fastapi import WebSocketDisconnect',
            'BaseModel': 'from pydantic import BaseModel',
            'Field': 'from pydantic import Field',
            'validator': 'from pydantic import validator',
            'root_validator': 'from pydantic import root_validator',
            'ValidationError': 'from pydantic import ValidationError',
            'constr': 'from pydantic import constr',
            'conint': 'from pydantic import conint',
            'confloat': 'from pydantic import confloat',
            'conlist': 'from pydantic import conlist',
            'conset': 'from pydantic import conset',
            'condict': 'from pydantic import condict',
            'HttpUrl': 'from pydantic import HttpUrl',
            'EmailStr': 'from pydantic import EmailStr',
            'SecretStr': 'from pydantic import SecretStr',
            'UUID4': 'from pydantic import UUID4',
            'FilePath': 'from pydantic import FilePath',
            'DirectoryPath': 'from pydantic import DirectoryPath',
            'AnyUrl': 'from pydantic import AnyUrl',
            'AnyHttpUrl': 'from pydantic import AnyHttpUrl',
            'PostgresDsn': 'from pydantic import PostgresDsn',
            'RedisDsn': 'from pydantic import RedisDsn',

            # App specific - these might need adjustment based on actual module structure
            'MemoryType': 'from app.models.memory import MemoryType',
            'MemoryCreate': 'from app.models.memory import MemoryCreate',
            'MemoryUpdate': 'from app.models.memory import MemoryUpdate',
            'MemoryResponse': 'from app.models.memory import MemoryResponse',
            'UserCreate': 'from app.models.user import UserCreate',
            'UserUpdate': 'from app.models.user import UserUpdate',
            'UserResponse': 'from app.models.user import UserResponse',
            'SessionCreate': 'from app.models.session import SessionCreate',
            'SessionUpdate': 'from app.models.session import SessionUpdate',
            'SessionResponse': 'from app.models.session import SessionResponse',
            'Database': 'from app.database import Database',
            'get_database': 'from app.database import get_database',
            'get_logger': 'from app.utils.logging_config import get_logger',
            'SecondBrainException': 'from app.core.exceptions import SecondBrainException',
            'NotFoundException': 'from app.core.exceptions import NotFoundException',
            'ValidationException': 'from app.core.exceptions import ValidationException',
            'DatabaseException': 'from app.core.exceptions import DatabaseException',
            'UnauthorizedException': 'from app.core.exceptions import UnauthorizedException',
            'ForbiddenException': 'from app.core.exceptions import ForbiddenException',
        }

        if missing_name in import_map:
            import_line = import_map[missing_name]

            # Read the file
            try:
                with open(error_file) as f:
                    content = f.read()

                # Check if import already exists
                if import_line in content:
                    print(f"Import already exists: {import_line}")
                    continue

                # Add import after other imports
                lines = content.split('\n')
                last_import_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        last_import_idx = i

                # Insert the import
                lines.insert(last_import_idx + 1, import_line)

                # Write back
                with open(error_file, 'w') as f:
                    f.write('\n'.join(lines))

                print(f"Added import: {import_line}")

            except Exception as e:
                print(f"Error fixing {error_file}: {e}")
        else:
            print(f"No known import for: {missing_name}")
            print("You may need to add it manually or check the module structure")
            break

if __name__ == "__main__":
    fix_missing_imports()
