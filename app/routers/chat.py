import json, datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from app.models import User, ChatMessage, Notification
from app.schemas import ChatMessageCreate, ChatMessageResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])

@router.post("/send", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
def send_chat_message(
    chat_in: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if chat_in.receiver_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot send message to yourself")

    receiver = db.query(User).filter(User.id == chat_in.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver user not found")

    # 1. Save chat message to DB
    new_message = ChatMessage(
        sender_id=current_user.id,
        receiver_id=receiver.id,
        message=chat_in.message,
        msg_type="text"
    )
    db.add(new_message)
    db.flush() # get id

    # 2. Automatically save Notification record for receiver in DB
    notification = Notification(
        user_id=receiver.id,
        title=f"New Message from {current_user.username}",
        body=chat_in.message[:100],
        type="chat",
        data=json.dumps({"sender_id": current_user.id, "message_id": new_message.id})
    )
    db.add(notification)

    db.commit()
    db.refresh(new_message)

    return ChatMessageResponse(
        id=new_message.id,
        sender_id=current_user.id,
        sender_username=current_user.username,
        receiver_id=receiver.id,
        receiver_username=receiver.username,
        message=new_message.message,
        msg_type=new_message.msg_type,
        timestamp=new_message.timestamp,
        is_read=new_message.is_read
    )

@router.get("/history/{other_user_id}", response_model=List[ChatMessageResponse])
def get_chat_history(
    other_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    other_user = db.query(User).filter(User.id == other_user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch messages between current_user and other_user
    messages = db.query(ChatMessage).filter(
        or_(
            and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == other_user_id),
            and_(ChatMessage.sender_id == other_user_id, ChatMessage.receiver_id == current_user.id)
        )
    ).order_by(ChatMessage.timestamp.asc()).all()

    # Mark unread messages from other_user as read
    db.query(ChatMessage).filter(
        ChatMessage.sender_id == other_user_id,
        ChatMessage.receiver_id == current_user.id,
        ChatMessage.is_read == False
    ).update({"is_read": True})
    db.commit()

    res = []
    for msg in messages:
        sender_name = current_user.username if msg.sender_id == current_user.id else other_user.username
        receiver_name = other_user.username if msg.sender_id == current_user.id else current_user.username
        res.append(ChatMessageResponse(
            id=msg.id,
            sender_id=msg.sender_id,
            sender_username=sender_name,
            receiver_id=msg.receiver_id,
            receiver_username=receiver_name,
            message=msg.message,
            msg_type=msg.msg_type,
            timestamp=msg.timestamp,
            is_read=msg.is_read
        ))
    return res
