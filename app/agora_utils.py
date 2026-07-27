from agora_token_builder import RtcTokenBuilder as PyRtcTokenBuilder, RtmTokenBuilder as PyRtmTokenBuilder
from app.config import settings

class RtcTokenBuilder:
    ROLE_PUBLISHER = 1
    ROLE_SUBSCRIBER = 2

    @classmethod
    def generate_rtc_token(cls, channel_name: str, uid: int, role: int = 1, expire_seconds: int = 3600) -> str:
        app_id = settings.AGORA_APP_ID
        app_certificate = settings.AGORA_PRIMARY_CERTIFICATE

        if not app_id or not app_certificate:
            raise ValueError("AGORA_APP_ID and AGORA_PRIMARY_CERTIFICATE must be configured in settings/.env")

        import time
        current_ts = int(time.time())
        privilege_expired_ts = current_ts + expire_seconds

        token_role = 1 if role == cls.ROLE_PUBLISHER else 2

        # Generates valid AccessToken
        return PyRtcTokenBuilder.buildTokenWithUid(
            app_id,
            app_certificate,
            channel_name,
            uid,
            token_role,
            privilege_expired_ts
        )


class RtmTokenBuilder:
    @classmethod
    def generate_rtm_token(cls, user_account: str, expire_seconds: int = 3600) -> str:
        app_id = settings.AGORA_APP_ID
        app_certificate = settings.AGORA_PRIMARY_CERTIFICATE

        if not app_id or not app_certificate:
            raise ValueError("AGORA_APP_ID and AGORA_PRIMARY_CERTIFICATE must be configured in settings/.env")

        import time
        current_ts = int(time.time())
        privilege_expired_ts = current_ts + expire_seconds

        return PyRtmTokenBuilder.buildToken(
            app_id,
            app_certificate,
            user_account,
            1, # Role RtmUser
            privilege_expired_ts
        )
