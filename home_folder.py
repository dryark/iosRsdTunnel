# Copyright (c) 2024 Dry Ark LLC
from pathlib import Path

LOCAL_PAIRING_RECORD_PATH = Path.home() / '.iosRsdTunnel'

def get_home_folder() -> Path:
    LOCAL_PAIRING_RECORD_PATH.mkdir(
        exist_ok=True,
    )
    return LOCAL_PAIRING_RECORD_PATH