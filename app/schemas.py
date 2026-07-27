import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr

# Auth Schemas
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str

# User Schemas
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_online: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Chat Schemas
class ChatMessageCreate(BaseModel):
    receiver_id: int
    message: str

class ChatMessageResponse(BaseModel):
    id: int
    sender_id: int
    sender_username: str
    receiver_id: int
    receiver_username: str
    message: str
    msg_type: str
    timestamp: datetime.datetime
    is_read: bool

    class Config:
        from_attributes = True

# Call Schemas
class CallInitiateRequest(BaseModel):
    receiver_id: int
    call_type: str # "audio" or "video"

class CallStatusUpdateRequest(BaseModel):
    call_id: int
    status: str # "accepted", "rejected", "missed", "ended"

class CallResponse(BaseModel):
    id: int
    caller_id: int
    caller_username: str
    receiver_id: int
    receiver_username: str
    channel_name: str
    call_type: str
    status: str
    started_at: datetime.datetime
    ended_at: Optional[datetime.datetime] = None
    duration_seconds: int
    caller_rtc_token: Optional[str] = None
    receiver_rtc_token: Optional[str] = None
    agora_app_id: Optional[str] = None

    class Config:
        from_attributes = True

# Notification Schemas
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    body: str
    type: str
    data: Optional[str] = None
    is_read: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Agora Token Schemas
class AgoraRtcTokenRequest(BaseModel):
    channel_name: str
    uid: int = 0
    role: str = "publisher" # "publisher" or "subscriber"
    expire_seconds: int = 3600

class AgoraRtcTokenResponse(BaseModel):
    app_id: str
    channel_name: str
    uid: int
    token: str

class AgoraRtmTokenRequest(BaseModel):
    user_account: str
    expire_seconds: int = 3600

class AgoraRtmTokenResponse(BaseModel):
    app_id: str
    user_account: str
    token: str
