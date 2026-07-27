import json, time, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.config import settings
from app.database import get_db
from app.models import User, CallHistory, ChatMessage, Notification
from app.schemas import CallInitiateRequest, CallStatusUpdateRequest, CallResponse
from app.auth import get_current_user
from app.agora_utils import RtcTokenBuilder

router = APIRouter(prefix="/api/v1/calls", tags=["Calls"])

@router.post("/initiate", response_model=CallResponse)
def initiate_call(
    call_in: CallInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if call_in.receiver_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot call yourself")

    receiver = db.query(User).filter(User.id == call_in.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Target user to call not found")

    channel_name = f"call_{current_user.id}_{receiver.id}_{int(time.time())}"

    # Generate RTC Tokens for caller and receiver
    caller_token = RtcTokenBuilder.generate_rtc_token(
        channel_name=channel_name,
        uid=current_user.id,
        role=RtcTokenBuilder.ROLE_PUBLISHER,
        expire_seconds=3600
    )

    receiver_token = RtcTokenBuilder.generate_rtc_token(
        channel_name=channel_name,
        uid=receiver.id,
        role=RtcTokenBuilder.ROLE_PUBLISHER,
        expire_seconds=3600
    )

    # 1. Create Call History record
    call_record = CallHistory(
        caller_id=current_user.id,
        receiver_id=receiver.id,
        channel_name=channel_name,
        call_type=call_in.call_type,
        status="initiated",
        started_at=datetime.datetime.utcnow()
    )
    db.add(call_record)
    db.flush()

    # 2. Insert into Chat History as required: "if i call anyone that should count also as a chat history and stored"
    call_msg_text = f"[{call_in.call_type.capitalize()} Call Initiated] Channel: {channel_name}"
    chat_log = ChatMessage(
        sender_id=current_user.id,
        receiver_id=receiver.id,
        message=call_msg_text,
        msg_type="call_log"
    )
    db.add(chat_log)

    # 3. Create Notification for receiver
    notification = Notification(
        user_id=receiver.id,
        title=f"Incoming {call_in.call_type.capitalize()} Call",
        body=f"{current_user.username} is calling you",
        type="call",
        data=json.dumps({
            "call_id": call_record.id,
            "caller_id": current_user.id,
            "caller_username": current_user.username,
            "channel_name": channel_name,
            "call_type": call_in.call_type,
            "rtc_token": receiver_token,
            "agora_app_id": settings.AGORA_APP_ID
        })
    )
    db.add(notification)

    db.commit()
    db.refresh(call_record)

    return CallResponse(
        id=call_record.id,
        caller_id=current_user.id,
        caller_username=current_user.username,
        receiver_id=receiver.id,
        receiver_username=receiver.username,
        channel_name=channel_name,
        call_type=call_record.call_type,
        status=call_record.status,
        started_at=call_record.started_at,
        ended_at=call_record.ended_at,
        duration_seconds=call_record.duration_seconds,
        caller_rtc_token=caller_token,
        receiver_rtc_token=receiver_token,
        agora_app_id=settings.AGORA_APP_ID
    )

@router.post("/status", response_model=CallResponse)
def update_call_status(
    status_in: CallStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    call_record = db.query(CallHistory).filter(CallHistory.id == status_in.call_id).first()
    if not call_record:
        raise HTTPException(status_code=404, detail="Call record not found")

    if current_user.id not in (call_record.caller_id, call_record.receiver_id):
        raise HTTPException(status_code=403, detail="Not authorized to update this call")

    new_status = status_in.status.lower()
    call_record.status = new_status

    if new_status in ("ended", "rejected", "missed"):
        call_record.ended_at = datetime.datetime.utcnow()
        if call_record.started_at:
            delta = call_record.ended_at - call_record.started_at
            call_record.duration_seconds = int(delta.total_seconds())

    # Add chat log & notification on missed call
    caller = db.query(User).filter(User.id == call_record.caller_id).first()
    receiver = db.query(User).filter(User.id == call_record.receiver_id).first()

    if new_status == "missed":
        # Add notification for missed call
        missed_notif = Notification(
            user_id=call_record.receiver_id,
            title="Missed Call",
            body=f"You missed a {call_record.call_type} call from {caller.username if caller else 'User'}",
            type="call",
            data=json.dumps({"call_id": call_record.id, "caller_id": call_record.caller_id})
        )
        db.add(missed_notif)

        # Log missed call in chat
        chat_log = ChatMessage(
            sender_id=call_record.caller_id,
            receiver_id=call_record.receiver_id,
            message=f"[Missed {call_record.call_type.capitalize()} Call]",
            msg_type="call_log"
        )
        db.add(chat_log)

    elif new_status == "ended":
        chat_log = ChatMessage(
            sender_id=call_record.caller_id,
            receiver_id=call_record.receiver_id,
            message=f"[{call_record.call_type.capitalize()} Call Ended - Duration: {call_record.duration_seconds}s]",
            msg_type="call_log"
        )
        db.add(chat_log)

    elif new_status == "rejected":
        chat_log = ChatMessage(
            sender_id=call_record.receiver_id,
            receiver_id=call_record.caller_id,
            message=f"[{call_record.call_type.capitalize()} Call Rejected]",
            msg_type="call_log"
        )
        db.add(chat_log)

    db.commit()
    db.refresh(call_record)

    return CallResponse(
        id=call_record.id,
        caller_id=call_record.caller_id,
        caller_username=caller.username if caller else "",
        receiver_id=call_record.receiver_id,
        receiver_username=receiver.username if receiver else "",
        channel_name=call_record.channel_name,
        call_type=call_record.call_type,
        status=call_record.status,
        started_at=call_record.started_at,
        ended_at=call_record.ended_at,
        duration_seconds=call_record.duration_seconds,
        agora_app_id=settings.AGORA_APP_ID
    )

@router.get("/history", response_model=List[CallResponse])
def get_call_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    calls = db.query(CallHistory).filter(
        or_(CallHistory.caller_id == current_user.id, CallHistory.receiver_id == current_user.id)
    ).order_by(CallHistory.started_at.desc()).all()

    res = []
    for call in calls:
        caller = db.query(User).filter(User.id == call.caller_id).first()
        receiver = db.query(User).filter(User.id == call.receiver_id).first()
        res.append(CallResponse(
            id=call.id,
            caller_id=call.caller_id,
            caller_username=caller.username if caller else "",
            receiver_id=call.receiver_id,
            receiver_username=receiver.username if receiver else "",
            channel_name=call.channel_name,
            call_type=call.call_type,
            status=call.status,
            started_at=call.started_at,
            ended_at=call.ended_at,
            duration_seconds=call.duration_seconds,
            agora_app_id=settings.AGORA_APP_ID
        ))
    return res
