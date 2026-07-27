import hmac
import hashlib
import base64
import struct
import time
import secrets
from app.config import settings

class RtcTokenBuilder:
    ROLE_PUBLISHER = 1
    ROLE_SUBSCRIBER = 2

    @staticmethod
    def _pack_uint16(val):
        return struct.pack('<H', val)

    @staticmethod
    def _pack_uint32(val):
        return struct.pack('<I', val)

    @staticmethod
    def _pack_string(val):
        val_bytes = val.encode('utf-8')
        return struct.pack('<H', len(val_bytes)) + val_bytes

    @staticmethod
    def _pack_map_uint32(val_map):
        res = struct.pack('<H', len(val_map))
        for k, v in sorted(val_map.items()):
            res += struct.pack('<H', k) + struct.pack('<I', v)
        return res

    @classmethod
    def generate_rtc_token(cls, channel_name: str, uid: int, role: int = 1, expire_seconds: int = 3600) -> str:
        app_id = settings.AGORA_APP_ID
        app_certificate = settings.AGORA_PRIMARY_CERTIFICATE

        if not app_id or not app_certificate:
            raise ValueError("AGORA_APP_ID and AGORA_PRIMARY_CERTIFICATE must be configured in .env")

        current_ts = int(time.time())
        privilege_expired_ts = current_ts + expire_seconds
        salt = secrets.randbelow(99999999) + 1

        # RTC Service ID = 1
        # Privileges: 1 = kJoinChannel, 2 = kPublishAudioStream, 3 = kPublishVideoStream, 4 = kPublishDataStream
        privileges = {
            1: privilege_expired_ts,
            2: privilege_expired_ts if role == cls.ROLE_PUBLISHER else 0,
            3: privilege_expired_ts if role == cls.ROLE_PUBLISHER else 0,
            4: privilege_expired_ts if role == cls.ROLE_PUBLISHER else 0,
        }

        # Build message payload for signature
        uid_str = str(uid) if uid != 0 else ""
        
        # Build AccessToken2 (v007)
        # Service 1 (RTC)
        service_type = 1
        service_bytes = cls._pack_uint16(service_type) + cls._pack_string(channel_name) + cls._pack_string(uid_str) + cls._pack_map_uint32(privileges)

        # Main AccessToken2 Content
        # Version 007
        version = "007"
        
        # Unsigned token payload: app_id + issue_ts + expire_ts + salt + services_count + services
        services_count = 1
        payload = (
            cls._pack_string(app_id) +
            cls._pack_uint32(current_ts) +
            cls._pack_uint32(privilege_expired_ts) +
            cls._pack_uint32(salt) +
            cls._pack_uint16(services_count) +
            service_bytes
        )

        # Signature: HMAC-SHA256(app_certificate, payload)
        signature = hmac.new(app_certificate.encode('utf-8'), payload, hashlib.sha256).digest()

        # Final Token: version (3 bytes) + base64(signature + payload)
        final_binary = signature + payload
        token = version + base64.b64encode(final_binary).decode('utf-8')
        return token


class RtmTokenBuilder:
    @classmethod
    def generate_rtm_token(cls, user_account: str, expire_seconds: int = 3600) -> str:
        app_id = settings.AGORA_APP_ID
        app_certificate = settings.AGORA_PRIMARY_CERTIFICATE

        if not app_id or not app_certificate:
            raise ValueError("AGORA_APP_ID and AGORA_PRIMARY_CERTIFICATE must be configured in .env")

        current_ts = int(time.time())
        privilege_expired_ts = current_ts + expire_seconds
        salt = secrets.randbelow(99999999) + 1

        # RTM / Chat Service ID = 2
        # Privilege 1 = Login RTM
        privileges = {1: privilege_expired_ts}

        # Service 2 (RTM)
        service_type = 2
        service_bytes = RtcTokenBuilder._pack_uint16(service_type) + RtcTokenBuilder._pack_string(user_account) + RtcTokenBuilder._pack_map_uint32(privileges)

        version = "007"
        services_count = 1
        payload = (
            RtcTokenBuilder._pack_string(app_id) +
            RtcTokenBuilder._pack_uint32(current_ts) +
            RtcTokenBuilder._pack_uint32(privilege_expired_ts) +
            RtcTokenBuilder._pack_uint32(salt) +
            RtcTokenBuilder._pack_uint16(services_count) +
            service_bytes
        )

        signature = hmac.new(app_certificate.encode('utf-8'), payload, hashlib.sha256).digest()
        token = version + base64.b64encode(signature + payload).decode('utf-8')
        return token
