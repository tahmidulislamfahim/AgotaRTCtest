import hmac
import hashlib
import base64
import struct
import time
import secrets
import zlib

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
        app_id = "5d14aebdcf754f92a51247ee5f0bfed0"
        app_certificate = "cb91ccc8a20d4620aef13c49e4fdc0ad"

        current_ts = int(time.time())
        privilege_expired_ts = current_ts + expire_seconds
        salt = secrets.randbelow(99999999) + 1

        # 1. Derive Signing Key
        # key1 = HMac(app_certificate, uint32_le(current_ts))
        # signing_key = HMac(key1, uint32_le(salt))
        issue_ts_bytes = cls._pack_uint32(current_ts)
        salt_bytes = cls._pack_uint32(salt)

        key1 = hmac.new(app_certificate.encode('utf-8'), issue_ts_bytes, hashlib.sha256).digest()
        signing_key = hmac.new(key1, salt_bytes, hashlib.sha256).digest()

        # 2. Build signing_info payload:
        # putString(app_id) + issue_ts + expire_ts + salt + service_count(1)
        payload = (
            cls._pack_string(app_id) +
            cls._pack_uint32(current_ts) +
            cls._pack_uint32(privilege_expired_ts) +
            cls._pack_uint32(salt) +
            cls._pack_uint16(1) # service_count = 1
        )

        # Service 1 (RTC)
        service_type = 1
        privileges = {
            1: privilege_expired_ts,
            2: privilege_expired_ts if role == cls.ROLE_PUBLISHER else 0,
            3: privilege_expired_ts if role == cls.ROLE_PUBLISHER else 0,
            4: privilege_expired_ts if role == cls.ROLE_PUBLISHER else 0,
        }

        uid_str = str(uid) if uid != 0 else ""
        service_bytes = (
            cls._pack_uint16(service_type) +
            cls._pack_map_uint32(privileges) +
            cls._pack_string(channel_name) +
            cls._pack_string(uid_str)
        )

        signing_info = payload + service_bytes

        # 3. Signature = HMAC-SHA256(signing_key, signing_info)
        signature = hmac.new(signing_key, signing_info, hashlib.sha256).digest()

        # 4. Content = putString(signature) + signing_info
        content = cls._pack_string(signature.decode('latin1')) if False else (cls._pack_uint16(len(signature)) + signature + signing_info)

        # 5. Compress using zlib (deflate)
        compressed = zlib.compress(content)

        return "007" + base64.b64encode(compressed).decode('utf-8')


if __name__ == '__main__':
    t = RtcTokenBuilder.generate_rtc_token("test_channel_123", 2)
    print("Python Generated Token:")
    print(t)
