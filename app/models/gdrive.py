"""
Google Drive integration data models.
SQLAlchemy models for Google Drive file tracking and OAuth credentials.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Text, BigInteger, DateTime, Boolean, Integer, ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

# from app.database import Base
# Note: Base not available in current database module
# This model is for future SQLAlchemy ORM implementation

class UserGoogleCredentials:  # (Base) - uncomment when Base is available
    """User's encrypted Google OAuth credentials"""
    
    __tablename__ = "user_google_credentials"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True)
    encrypted_refresh_token = Column(Text, nullable=False)
    access_token_hash = Column(String(255), nullable=True)  # For cache validation
    drive_permissions = Column(JSONB, default={})
    quota_info = Column(JSONB, default={})
    webhook_resource_id = Column(String(255), nullable=True)
    webhook_expiration = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GDriveFile:  # (Base) - uncomment when Base is available
    """Google Drive file metadata and processing status"""
    
    __tablename__ = "gdrive_files"
    
    file_id = Column(String(255), primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(Text, nullable=False)
    mime_type = Column(String(255), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    md5_checksum = Column(String(255), nullable=True)
    modified_time = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    memory_id = Column(UUID(as_uuid=True), nullable=True)
    parent_folders = Column(ARRAY(String), default=[])
    drive_metadata = Column(JSONB, default={})
    processing_status = Column(String(50), default='pending')
    processing_priority = Column(Integer, default=5)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    ai_extracted_entities = Column(JSONB, default={})
    document_structure = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GDriveFolder:  # (Base) - uncomment when Base is available
    """Google Drive folder hierarchy and sync preferences"""
    
    __tablename__ = "gdrive_folders"
    
    folder_id = Column(String(255), primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(Text, nullable=False)
    parent_folder_id = Column(String(255), nullable=True)
    sync_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GDriveJob:  # (Base) - uncomment when Base is available
    """Background processing jobs for Google Drive files"""
    
    __tablename__ = "gdrive_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    file_id = Column(String(255), nullable=True)
    folder_id = Column(String(255), nullable=True)
    job_type = Column(String(50), nullable=False)  # 'initial_sync', 'file_update', etc.
    status = Column(String(50), default='queued')  # 'queued', 'processing', etc.
    priority = Column(Integer, default=5)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    job_data = Column(JSONB, default={})
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class GDriveChangeNotification:  # (Base) - uncomment when Base is available
    """Google Drive webhook change notifications"""
    
    __tablename__ = "gdrive_change_notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    file_id = Column(String(255), nullable=True)
    change_type = Column(String(50), nullable=True)  # 'add', 'update', 'remove', 'trash'
    notification_data = Column(JSONB, default={})
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class GDriveMetrics:  # (Base) - uncomment when Base is available
    """Performance and usage metrics for Google Drive operations"""
    
    __tablename__ = "gdrive_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    metric_type = Column(String(100), nullable=False)
    metric_value = Column(String(255), nullable=True)  # Flexible for different metric types
    file_type = Column(String(100), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    metadata = Column(JSONB, default={})
    recorded_at = Column(DateTime, default=datetime.utcnow)