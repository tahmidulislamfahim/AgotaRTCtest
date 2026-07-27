import hmac, hashlib, json, datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import CallHistory, ChatMessage, Notification, User
from app.schemas import (
    AgoraRtcTokenRequest, AgoraRtcTokenResponse,
    AgoraRtmTokenRequest, AgoraRtmTokenResponse
)
from app.auth import get_current_user
from app.agora_utils import RtcTokenBuilder, RtmTokenBuilder

router = APIRouter(prefix="/api/v1/agora", tags=["Agora"])

@router.post("/rtc-token", response_model=AgoraRtcTokenResponse)
def get_rtc_token(
    request: AgoraRtcTokenRequest,
    current_user: User = Depends(get_current_user)
):
    role = RtcTokenBuilder.ROLE_PUBLISHER if request.role.lower() == "publisher" else RtcTokenBuilder.ROLE_SUBSCRIBER
    uid = request.uid if request.uid != 0 else current_user.id

    token = RtcTokenBuilder.generate_rtc_token(
        channel_name=request.channel_name,
        uid=uid,
        role=role,
        expire_seconds=request.expire_seconds
    )

    return AgoraRtcTokenResponse(
        app_id=settings.AGORA_APP_ID,
        channel_name=request.channel_name,
        uid=uid,
        token=token
    )

@router.post("/rtm-token", response_model=AgoraRtmTokenResponse)
def get_rtm_token(
    request: AgoraRtmTokenRequest,
    current_user: User = Depends(get_current_user)
):
    account = request.user_account or current_user.username

    token = RtmTokenBuilder.generate_rtm_token(
        user_account=account,
        expire_seconds=request.expire_seconds
    )

    return AgoraRtmTokenResponse(
        app_id=settings.AGORA_APP_ID,
        user_account=account,
        token=token
    )

@router.post("/webhook")
async def agora_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Agora Webhook Callback Endpoint.
    Handles RTC Channel Events (101: channel create, 102: channel destroy, 103: broadcaster join, 104: leave)
    """
    body_bytes = await request.body()
    
    # Verify signature if Agora signature header is present
    agora_signature = request.headers.get("Agora-Signature") or request.headers.get("agora-signature")
    if settings.AGORA_WEBHOOK_SECRET and agora_signature:
        expected_sig = hmac.new(settings.AGORA_WEBHOOK_SECRET.encode('utf-8'), body_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, agora_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        data = json.loads(body_bytes.decode('utf-8'))
    except Exception:
        return {"status": "ignored", "reason": "invalid json payload"}

    event_type = data.get("noticeId") or data.get("eventType") or data.get("event_type")
    payload = data.get("payload", {})
    channel_name = payload.get("channelName") or data.get("channelName")

    if channel_name:
        call_record = db.query(CallHistory).filter(CallHistory.channel_name == channel_name).first()
        if call_record:
            if event_type in (102, "channel destroy", "channel_destroy"):
                # Channel destroyed (call ended)
                if call_record.status == "initiated":
                    call_record.status = "missed"
                    # Log missed call
                    missed_notif = Notification(
                        user_id=call_record.receiver_id,
                        title="Missed Call",
                        body=f"You missed a call on channel {channel_name}",
                        type="call",
                        data=json.dumps({"call_id": call_record.id})
                    )
                    db.add(missed_notif)
                else:
                    call_record.status = "ended"

                call_record.ended_at = datetime.datetime.utcnow()
                if call_record.started_at:
                    delta = call_record.ended_at - call_record.started_at
                    call_record.duration_seconds = int(delta.total_seconds())

                db.commit()

    return {"status": "success", "received_event": event_type}
