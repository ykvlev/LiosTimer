import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

DEFAULT_TON_WALLET = "UQBrsw7tct-MO8ZkSGsWUZtwH5LImu_Kmjad5kng1mho6RSt"


@dataclass
class Config:
    bot_token: str
    admin_id: int
    ton_wallet: str
    server_name: str = "CEO-734"


def load_config() -> Config:
    bot_token = (os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Add it to .env or environment variables.")

    admin_id_raw = os.getenv("ADMIN_ID", "0").strip()
    try:
        admin_id = int(admin_id_raw)
    except ValueError as exc:
        raise RuntimeError(f"ADMIN_ID is invalid: {admin_id_raw!r}") from exc

    ton_wallet = (os.getenv("TON_WALLET") or DEFAULT_TON_WALLET).strip()
    return Config(
        bot_token=bot_token,
        admin_id=admin_id,
        ton_wallet=ton_wallet,
    )
