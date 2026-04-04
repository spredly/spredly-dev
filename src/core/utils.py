import datetime
import secrets
from datetime import datetime, timedelta

import pytz
from passlib.context import CryptContext

from src.core.constants import PERIODS
from src.parser.config import sports_ids

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def format_key(key: str):
    return ";".join(key.split(";")[:3])


def get_period_title(sport_id: int, key: str, relation: str | None):
    key = format_key(key)
    sport = PERIODS[sports_ids[sport_id].lower()]
    if relation:
        sport = sport.get(relation)
    return sport.get(key)


def get_yesterday_ymd():
    yesterday_utc = datetime.utcnow() - timedelta(days=1)
    formatted = yesterday_utc.strftime("%Y-%m-%d")
    return formatted


def generate_invite_code(length: int = 12):
    return secrets.token_urlsafe(length)[:length]


def iso_to_utc(iso_str: str):
    return datetime.fromisoformat(iso_str.replace("Z", ""))


def gmt_to_utc(gmt_str: str):
    return datetime.strptime(gmt_str, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=None)


def utc_to_msc(utc_data: str):
    msc_zone = pytz.timezone("Europe/Moscow")
    msc_time = utc_data.astimezone(msc_zone)
    return msc_time


def calc_coeff(price):
    if price > 0:
        return round(price / 100 + 1, 3)
    return round(abs(100 / price) + 1, 3)


def to_dict_for_insert(obj, extra_fields=None):
    data = {}
    for col in obj.__table__.columns:
        value = getattr(obj, col.name)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        data[col.name] = value
    if extra_fields:
        data.update(extra_fields)
    return data
