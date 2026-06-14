import asyncio
import json
import os
import random
import re
import shutil
import tempfile
import time
import zipfile
from copy import deepcopy
from datetime import datetime, timedelta
from html import escape
from pathlib import Path

import requests
from telegram import KeyboardButton, InlineKeyboardButton as TelegramInlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeCustomEmoji, ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telethon import TelegramClient, utils
from telethon.errors import (
    FloodWaitError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SendCodeUnavailableError,
    SessionPasswordNeededError,
    UserAlreadyParticipantError,
)
from telethon.tl.functions.messages import ImportChatInviteRequest


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
SESSION_FILE = BASE_DIR / "userbot"
STICKER_DIR = BASE_DIR / "stickers"
IMAGE_DIR = BASE_DIR / "prediction_images"

API_URLS = [
    "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json",
]
API_URL = API_URLS[0]

# Deployment credentials live here. Runtime state still uses config.json so
# subscriptions, channels, and prediction history survive restarts.
BOT_TOKEN = "8636559552:AAF6yFKtetqEi4X2N9CghTAR5Mdjd-Pspp8"
TELEGRAM_API_ID = "39052980"
TELEGRAM_API_HASH = "5b0b6f9aedd2113a4a591dbcde61be43"
USERBOT_PHONE = "916005368965"
ADMIN_IDS = [8776447116]

DEFAULT_CONFIG = {
    "bot_token": BOT_TOKEN,
    "admin_ids": ADMIN_IDS,
    "channel_id": "",
    "channel_username": "",
    "channels": [],
    "sender_mode": "userbot",
    "channel_assignments": {},
    "channel_prediction_images": {},
    "prediction_images": {
        "BIG": {"enabled": False, "path": "", "file_id": ""},
        "SMALL": {"enabled": False, "path": "", "file_id": ""},
    },
    "users": {},
    "trial_days": 2,
    "api_urls": API_URLS,
    "prediction_active": False,
    "auto_mode": False,
    "auto_interval": 60,
    "prediction_prepare_seconds": 2,
    "mode": "24x7",
    "sessions": [],
    "session_presets": {
        "morning": ["08:00"],
        "evening": ["18:00"],
        "four_sessions": ["08:00", "12:00", "16:00", "20:00"],
        "full_day": ["00:00-23:59"],
    },
    "schedule_monitor_interval": 2,
    "session_started_by_schedule": False,
    "active_session_key": "",
    "completed_session_keys": [],
    "stop_after_wins": 0,
    "session_wins": 0,
    "send_prediction_message": True,
    "send_win_message": True,
    "send_loss_message": False,
    "martingale": {"enabled": True, "base_bet": 1, "multiplier": 2, "level": 0, "max_level": 4},
    "api_id": TELEGRAM_API_ID,
    "api_hash": TELEGRAM_API_HASH,
    "phone": USERBOT_PHONE,
    "login_phone_code_hash": "",
    "stickers": {
        "start": "AgADiBcAAg7l2VY",
        "end": "AgADUyEAAnIL2VY",
        "win": "AgADbBIAAtaN2VY",
        "loss": "AgADgUwAAuveiUs",
    },
    "sticker_files": {
        "start": "",
        "end": "",
        "win": "",
        "loss": "",
    },
    "templates": {
        "prediction": (
            "🎯 PREDICTION\n\n"
            "Period: {period}\n"
            "Number: {number_emoji} ({number})\n"
            "Size: {size_icon} {size}\n"
            "Color: {color_icon} {color}\n"
            "Confidence: {confidence}%\n\n"
            "Time: {time}\n"
            "Play safe."
        ),
        "win": (
            "✅ WIN\n\n"
            "Period: {period}\n"
            "Prediction: {pred_number} | {pred_size} | {pred_color}\n"
            "Result: {actual_number} | {actual_size} | {actual_color}\n"
            "Matched: {matched}"
        ),
        "loss": (
            "❌ LOSS\n\n"
            "Period: {period}\n"
            "Prediction: {pred_number} | {pred_size} | {pred_color}\n"
            "Result: {actual_number} | {actual_size} | {actual_color}"
        ),
    },
    "history": [],
    "stats": {"total": 0, "wins": 0, "losses": 0},
    "current_prediction": None,
    "pending_predictions": [],
    "last_period_sent": "",
}

NUMBER_EMOJI = {
    0: "0️⃣",
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣",
    7: "7️⃣",
    8: "8️⃣",
    9: "9️⃣",
}

COLOR_ICON = {
    "RED": "🔴",
    "GREEN": "🟢",
    "RED+VIOLET": "🔴🟣",
    "GREEN+VIOLET": "🟢🟣",
}

SIZE_ICON = {"BIG": "🔷", "SMALL": "🔶"}

PE_IDS = {
    "eyes": "5210956306952758910", "smile": "5461117441612462242", "zap": "5456140674028019486",
    "comet": "5224607267797606837", "shop": "5229064374403998351", "stop": "5260293700088511294",
    "no": "5240241223632954241", "excl": "5274099962655816924", "q": "5436113877181941026",
    "warn": "5447644880824181073", "globe": "5447410659077661506", "chat": "5443038326535759644",
    "chart": "5231200819986047254", "check": "5206607081334906820", "cross": "5210952531676504517",
    "bell": "5458603043203327669", "free": "5406756500108501710", "party": "5461151367559141950",
    "pin": "5397782960512444700", "money": "5409048419211682843", "fire": "5424972470023104089",
    "boom": "5276032951342088188", "mega": "5424818078833715060", "search": "5231012545799666522",
    "shield": "5251203410396458957", "link": "5271604874419647061", "info": "5334544901428229844",
    "thumb": "5337080053119336309", "hundred": "5341498088408234504", "red": "5411225014148014586",
    "green": "5416081784641168838", "star": "5300751802390558772", "crystal": "5298839605640967919",
    "eye": "5300841391113387083", "candle": "5301272202102978654",
    "pumpkin": "5301253879772494275", "blackcat": "5298571372048430494", "ghost": "5301072507598550489",
    "leaf": "5299000473641041282", "pot": "5298588027931605905", "web": "5301087956595915859",
    "candy": "5298899309981351959", "moon": "5298614811347664472", "spider": "5300945294962210459",
    "tophat": "5300963565753091828", "witch": "5298907998700189550", "coffin": "5298532944976034951",
    "bear": "5301157513591273190", "zombie": "5301167533749972632", "skull2": "5298600693790160850",
    "skull": "5301259549129325864", "castle": "5298780807538685579", "knife": "5298659199834668012",
    "axe": "5298529109570239315", "bat": "5298598765349847151", "grin": "5300932912571496037",
    "devil": "5298810614611722954", "grave": "5298725402460568410", "crow": "5298676001746731942",
    "vampire": "5298937071333817643", "lolly": "5301222298877967960",
}

EMOJI = {
    "eyes": "👀", "smile": "🙂", "zap": "⚡", "comet": "☄️", "shop": "🛍", "stop": "⛔", "no": "🚫",
    "excl": "❗", "q": "❓",
    "warn": "⚠️", "globe": "🌐", "chat": "💬", "chart": "📊", "check": "✅", "cross": "❌",
    "bell": "🔔", "free": "🆓", "party": "🎉", "pin": "📌", "money": "💵", "fire": "🔥",
    "boom": "💥", "mega": "📣", "search": "🔍", "shield": "🛡", "link": "🔗", "info": "ℹ️",
    "thumb": "👍", "hundred": "💯", "red": "🔴", "green": "🟢", "star": "⭐️",
    "crystal": "🔮", "eye": "👁", "candle": "🕯",
    "pumpkin": "🎃", "blackcat": "🐈‍⬛", "ghost": "👻", "leaf": "🍁", "pot": "🍲", "web": "🕸",
    "candy": "🍬", "moon": "🌙", "spider": "🕷", "tophat": "🎩", "witch": "🧙‍♀️", "coffin": "⚰️",
    "bear": "🧸", "zombie": "🧟", "skull2": "☠️", "skull": "💀", "castle": "🏰", "knife": "🔪",
    "axe": "🪓", "bat": "🦇", "grin": "😀", "devil": "😈", "grave": "🪦", "crow": "🐦‍⬛",
    "vampire": "🧛‍♂️", "lolly": "🍭",
}

config = {}
user_client = None
api_cache = {"time": 0.0, "data": None}
api_status = {"last_error": "", "last_url": "", "last_success": ""}


def public_service_error():
    return "Prediction service is temporarily unavailable. Please try again shortly."


def pe(name):
    return f'<tg-emoji emoji-id="{PE_IDS[name]}">{EMOJI.get(name, "⭐")}</tg-emoji>'


def InlineKeyboardButton(text, *args, callback_data=None, style=None, icon_custom_emoji_id=None, **kwargs):
    label = str(text).lower()
    action = str(callback_data or "").lower()
    if style is None:
        if any(word in label + action for word in ["remove", "reset", "expire", "logout", "clear", "cancel", "loss"]):
            style = "danger"
        elif any(word in label + action for word in ["send", "verify", "test", "add", "connect", "save", "win", "enable"]):
            style = "success"
        else:
            style = "primary"
    if icon_custom_emoji_id is None:
        if style == "danger":
            icon_custom_emoji_id = PE_IDS["cross"]
        elif style == "success":
            icon_custom_emoji_id = PE_IDS["check"]
        else:
            icon_custom_emoji_id = PE_IDS["star"]
    return TelegramInlineKeyboardButton(
        text,
        *args,
        callback_data=callback_data,
        style=style,
        icon_custom_emoji_id=icon_custom_emoji_id,
        **kwargs,
    )


def btn(text, callback_data, icon="star", style=None):
    if style is None:
        if any(word in callback_data for word in ["remove", "reset", "expire", "logout", "stop", "clear"]):
            style = "danger"
        elif any(word in callback_data for word in ["send", "verify", "test", "toggle", "set", "add", "connect", "premium"]):
            style = "success"
        else:
            style = "primary"
    return InlineKeyboardButton(text, callback_data=callback_data, icon_custom_emoji_id=PE_IDS.get(icon), style=style)


def back_btn(callback_data="home"):
    return btn("Back", callback_data, "no")


async def react(update, name="check"):
    message = update.callback_query.message if update.callback_query else update.effective_message
    if not message:
        return
    try:
        await update.get_bot().set_message_reaction(
            chat_id=message.chat_id,
            message_id=message.message_id,
            reaction=[ReactionTypeCustomEmoji(PE_IDS[name])],
            is_big=True,
        )
    except Exception:
        try:
            await update.get_bot().set_message_reaction(
                chat_id=message.chat_id,
                message_id=message.message_id,
                reaction="⚡",
                is_big=True,
            )
        except Exception:
            pass


def deep_merge(default, saved):
    result = deepcopy(default)
    for key, value in saved.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config():
    if CONFIG_FILE.exists():
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            saved = json.load(f)
        loaded = deep_merge(DEFAULT_CONFIG, saved)
    else:
        loaded = deepcopy(DEFAULT_CONFIG)
    loaded["bot_token"] = BOT_TOKEN
    loaded["api_id"] = TELEGRAM_API_ID
    loaded["api_hash"] = TELEGRAM_API_HASH
    loaded["phone"] = USERBOT_PHONE
    loaded["admin_ids"] = list(dict.fromkeys([*ADMIN_IDS, *loaded.get("admin_ids", [])]))
    return loaded


def save_config():
    saved = deepcopy(config)
    for key in ["bot_token", "api_id", "api_hash", "phone"]:
        saved.pop(key, None)
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(saved, f, indent=2, ensure_ascii=False)


def create_full_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(tempfile.gettempdir()) / f"wingo_full_backup_{timestamp}.zip"
    excluded = {"__pycache__", ".git"}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in BASE_DIR.rglob("*"):
            if not item.is_file() or any(part in excluded for part in item.parts):
                continue
            if item.resolve() == path.resolve() or item.suffix in {".pyc", ".journal"}:
                continue
            archive.write(item, item.relative_to(BASE_DIR))
    return path


def restore_runtime_backup(path):
    allowed_roots = {"config.json", "stickers", "prediction_images", "userbot.session"}
    restored = 0
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir).resolve()
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                member_path = (temp_root / member.filename).resolve()
                if temp_root not in member_path.parents and member_path != temp_root:
                    raise ValueError("Unsafe backup path detected")
                archive.extract(member, temp_root)
        for item in temp_root.rglob("*"):
            if not item.is_file():
                continue
            relative = item.relative_to(temp_root)
            root_name = relative.parts[0]
            if root_name not in allowed_roots and not root_name.startswith("userbot.session"):
                continue
            target = (BASE_DIR / relative).resolve()
            if BASE_DIR.resolve() not in target.parents:
                raise ValueError("Unsafe restore target detected")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            restored += 1
    return restored


def get_user_profile(user_id, create=True):
    user_id = str(user_id)
    users = config.setdefault("users", {})
    if user_id not in users and create:
        now = datetime.now()
        users[user_id] = {
            "created_at": now.isoformat(timespec="seconds"),
            "subscription_until": (now + timedelta(days=int(config.get("trial_days", 2)))).isoformat(timespec="seconds"),
            "plan": "free_trial",
            "premium_access": False,
            "overrides": {},
            "channels": [],
            "stats": {"total": 0, "wins": 0, "losses": 0},
            "prediction_active": False,
            "current_prediction": None,
            "last_period_sent": "",
        }
        save_config()
    return users.get(user_id, {})


def user_has_access(user_id):
    if is_admin(user_id):
        return True
    profile = get_user_profile(user_id)
    try:
        return datetime.now() <= datetime.fromisoformat(profile.get("subscription_until", ""))
    except ValueError:
        return False


def effective_user_settings(user_id):
    profile = get_user_profile(user_id)
    defaults = {
        "sender_mode": "main_bot",
        "channels": deepcopy(profile.get("channels", [])),
        "prediction_images": deepcopy(config.get("prediction_images", {})),
        "auto_interval": config.get("auto_interval", 60),
        "auto_mode": config.get("auto_mode", False),
        "predictions_enabled": True,
        "mode": config.get("mode", "24x7"),
        "sessions": deepcopy(config.get("sessions", [])),
    }
    return deep_merge(defaults, profile.get("overrides", {}))


def user_is_premium(user_id):
    return is_admin(user_id) or bool(get_user_profile(user_id).get("premium_access"))


def user_job_name(user_id):
    return f"user_prediction:{user_id}"


def user_in_schedule_window(user_id):
    settings = effective_user_settings(user_id)
    if settings.get("mode", "24x7") != "scheduled":
        return True
    now_minutes = datetime.now().hour * 60 + datetime.now().minute
    for session in settings.get("sessions", []):
        parsed = parse_session(session)
        if not parsed:
            continue
        _, start_minutes, end_minutes, _ = parsed
        if start_minutes <= end_minutes and start_minutes <= now_minutes <= end_minutes:
            return True
        if start_minutes > end_minutes and (now_minutes >= start_minutes or now_minutes <= end_minutes):
            return True
    return False


async def remove_user_prediction_jobs(context, user_id):
    for job in context.job_queue.get_jobs_by_name(user_job_name(user_id)):
        job.schedule_removal()


def schedule_user_prediction(context, user_id, chat_id, delay=None):
    settings = effective_user_settings(user_id)
    interval = max(45, int(settings.get("auto_interval", 60)))
    context.job_queue.run_once(
        user_prediction_job,
        when=delay if delay is not None else interval,
        chat_id=chat_id,
        user_id=int(user_id),
        name=user_job_name(user_id),
        data={"user_id": int(user_id)},
        job_kwargs={"misfire_grace_time": 15},
    )


async def send_user_profile_prediction(user_id, bot):
    profile = get_user_profile(user_id)
    settings = effective_user_settings(user_id)
    channels = settings.get("channels") or []
    if not profile.get("prediction_active"):
        return False, "Predictions are stopped"
    if not channels:
        return False, "Connect your channel first"

    api = await asyncio.to_thread(fetch_api)
    if not api["ok"]:
        return False, public_service_error()
    period = next_period(api["period"])
    if profile.get("last_period_sent") == period:
        return False, f"Prediction already sent for {period}"

    number, size, color, confidence = build_prediction(api["records"])
    values = {
        "period": period, "number": number, "number_emoji": NUMBER_EMOJI[number],
        "size": size, "size_icon": SIZE_ICON[size], "color": color, "color_icon": COLOR_ICON[color],
        "confidence": confidence, "time": datetime.now().strftime("%I:%M:%S %p"),
        "bet_level": 0, "bet_amount": 1,
    }
    template = settings.get("prediction_template") or config["templates"].get("prediction", DEFAULT_CONFIG["templates"]["prediction"])
    try:
        text = template.format(**values)
    except KeyError as exc:
        return False, f"Template error: missing {exc}"

    ok, msg = await send_user_message(
        text,
        bot=bot,
        channels=channels,
        sender_mode="main_bot",
        prediction_size=size,
    )
    if not ok:
        return False, msg
    profile["current_prediction"] = {
        "period": period, "number": number, "size": size, "color": color,
        "confidence": confidence, "verified": False,
    }
    profile["last_period_sent"] = period
    save_config()
    return True, f"Prediction sent for {period}"


async def verify_user_profile_prediction(user_id, bot):
    profile = get_user_profile(user_id)
    settings = effective_user_settings(user_id)
    current = profile.get("current_prediction")
    if not current or current.get("verified"):
        return True, "No pending result"
    api = await asyncio.to_thread(fetch_api)
    if not api["ok"]:
        return False, public_service_error()
    result_record, actual_number = find_result_record(api, current["period"])
    if not result_record:
        if prediction_is_stale(api, current["period"]) or prediction_is_behind_latest(api, current["period"]):
            current["verified"] = True
            current["result"] = "STALE_SKIPPED"
            profile["current_prediction"] = None
            save_config()
            return True, f"Stale prediction skipped: {current['period']}"
        return False, f"Result not ready for {current['period']}"
    actual_number, actual_size, actual_color = analyze(actual_number)
    is_win = actual_number == current["number"] or actual_size == current["size"] or actual_color == current["color"]
    values = {
        "period": current["period"], "pred_number": current["number"], "pred_size": current["size"],
        "pred_color": current["color"], "actual_number": actual_number, "actual_size": actual_size,
        "actual_color": actual_color, "matched": "Number / Size / Color" if is_win else "None",
    }
    result_name = "win" if is_win else "loss"
    await send_sticker_to_channels(result_name, settings.get("channels", []), bot)
    should_send = config.get("send_win_message", True) if is_win else config.get("send_loss_message", False)
    if should_send:
        await send_user_message(
            format_template(result_name, values),
            bot=bot,
            channels=settings.get("channels", []),
            sender_mode="main_bot",
        )
    stats = profile.setdefault("stats", {"total": 0, "wins": 0, "losses": 0})
    stats["total"] += 1
    stats["wins" if is_win else "losses"] += 1
    current["verified"] = True
    save_config()
    return True, "WIN" if is_win else "LOSS"


async def user_prediction_job(context: ContextTypes.DEFAULT_TYPE):
    user_id = int((context.job.data or {}).get("user_id") or context.job.user_id)
    profile = get_user_profile(user_id)
    if not profile.get("prediction_active") or not user_has_access(user_id):
        return
    if not user_in_schedule_window(user_id):
        schedule_user_prediction(context, user_id, context.job.chat_id, delay=30)
        return
    ok, msg = await verify_user_profile_prediction(user_id, context.bot)
    if not ok and "Result not ready" in msg:
        schedule_user_prediction(context, user_id, context.job.chat_id, delay=10)
        return
    ok, msg = await send_user_profile_prediction(user_id, context.bot)
    print(f"user {user_id} auto prediction: {msg}")
    if profile.get("prediction_active"):
        schedule_user_prediction(context, user_id, context.job.chat_id)


USER_MENU_ACTIONS = {
    "Connect": "connect",
    "My Channels": "channels",
    "Plans": "plans",
    "Status": "status",
    "Help": "help",
    "About": "about",
}


def user_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton("Connect", icon_custom_emoji_id=PE_IDS["link"], style="success"),
                KeyboardButton("My Channels", icon_custom_emoji_id=PE_IDS["globe"], style="primary"),
            ],
            [
                KeyboardButton("Plans", icon_custom_emoji_id=PE_IDS["money"], style="primary"),
                KeyboardButton("Status", icon_custom_emoji_id=PE_IDS["chart"], style="success"),
            ],
            [
                KeyboardButton("Help", icon_custom_emoji_id=PE_IDS["q"], style="primary"),
                KeyboardButton("About", icon_custom_emoji_id=PE_IDS["info"], style="primary"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choose an option...",
    )


def prediction_image(size, channel=None):
    if channel is not None:
        override = config.get("channel_prediction_images", {}).get(str(channel), {}).get(size, {})
        override_path = str(override.get("path") or "")
        if override.get("enabled") and override_path and Path(override_path).exists():
            return override_path
    default = config.get("prediction_images", {}).get(size, {})
    path = str(default.get("path") or "")
    if default.get("enabled") and path and Path(path).exists():
        return path
    return ""


def channel_sender_mode(channel):
    return config.get("channel_assignments", {}).get(str(channel), config.get("sender_mode", "userbot"))


def get_channels():
    channels = []
    for channel in config.get("channels", []):
        channel = str(channel).strip()
        if channel and channel not in channels:
            channels.append(channel)

    old_channel = str(config.get("channel_id") or "").strip()
    if old_channel and old_channel not in channels:
        channels.insert(0, old_channel)
    return channels


def set_channels(channels):
    clean = []
    for channel in channels:
        channel = str(channel).strip()
        if channel and channel not in clean:
            clean.append(channel)
    config["channels"] = clean
    config["channel_id"] = clean[0] if clean else ""
    config["channel_username"] = config["channel_id"]


def channel_id_to_ref(chat_id):
    chat_id = int(chat_id)
    if chat_id < 0 and not str(chat_id).startswith("-100"):
        return str(chat_id)
    return str(chat_id)


def extract_invite_hash(value):
    value = str(value).strip()
    patterns = [
        r"(?:https?://)?t\.me/\+([A-Za-z0-9_-]+)",
        r"(?:https?://)?telegram\.me/\+([A-Za-z0-9_-]+)",
        r"(?:https?://)?t\.me/joinchat/([A-Za-z0-9_-]+)",
        r"(?:https?://)?telegram\.me/joinchat/([A-Za-z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group(1)
    return ""


def extract_forwarded_channel_ref(message):
    origin = getattr(message, "forward_origin", None)
    origin_chat = getattr(origin, "chat", None)
    if origin_chat:
        return channel_id_to_ref(origin_chat.id), getattr(origin_chat, "title", "") or getattr(origin_chat, "username", "")

    fwd_chat = getattr(message, "forward_from_chat", None)
    if fwd_chat:
        return channel_id_to_ref(fwd_chat.id), getattr(fwd_chat, "title", "") or getattr(fwd_chat, "username", "")

    return "", ""


async def normalize_channel_ref(value):
    value = str(value).strip()
    invite_hash = extract_invite_hash(value)
    if invite_hash:
        client = await get_user_client()
        if not client or not await client.is_user_authorized():
            return False, "Userbot login first, then add private invite link."
        try:
            updates = await client(ImportChatInviteRequest(invite_hash))
            chats = getattr(updates, "chats", []) or []
            if chats:
                return True, channel_id_to_ref(f"-100{chats[0].id}")
        except UserAlreadyParticipantError:
            return False, "Userbot already joined. Forward any post from that private channel to add it."
        except Exception as exc:
            return False, f"Invite join failed: {exc}"
        return False, "Invite joined but channel could not be detected. Forward a channel post to add it."

    return True, value


async def resolve_channel_target(client, channel):
    channel = str(channel).strip()
    invite_hash = extract_invite_hash(channel)
    if invite_hash:
        updates = await client(ImportChatInviteRequest(invite_hash))
        chats = getattr(updates, "chats", []) or []
        if chats:
            return chats[0]

    if re.fullmatch(r"-?\d+", channel):
        numeric_id = int(channel)
        try:
            return await client.get_entity(numeric_id)
        except Exception:
            real_id, peer_type = utils.resolve_id(numeric_id)
            return peer_type(real_id)

    return channel


def parse_session(session):
    session = str(session).strip()
    try:
        if "-" in session:
            start, end = [part.strip() for part in session.split("-", 1)]
            sh, sm = [int(x) for x in start.split(":", 1)]
            eh, em = [int(x) for x in end.split(":", 1)]
            kind = "range"
        else:
            sh, sm = [int(x) for x in session.split(":", 1)]
            eh, em = 23, 59
            kind = "start"
    except Exception:
        return None
    if not (0 <= sh <= 23 and 0 <= eh <= 23 and 0 <= sm <= 59 and 0 <= em <= 59):
        return None
    label = f"{sh:02d}:{sm:02d}" if kind == "start" else f"{sh:02d}:{sm:02d}-{eh:02d}:{em:02d}"
    return label, sh * 60 + sm, eh * 60 + em, kind


def normalized_sessions():
    clean = []
    for session in config.get("sessions", [])[:4]:
        parsed = parse_session(session)
        if parsed and parsed[0] not in clean:
            clean.append(parsed[0])
    return clean


def current_session_key(now=None):
    if config.get("mode") != "scheduled":
        return "24x7"

    sessions = normalized_sessions()
    if not sessions:
        return ""

    now = now or datetime.now()
    now_minutes = now.hour * 60 + now.minute
    today = now.strftime("%Y%m%d")
    yesterday = datetime.fromtimestamp(time.time() - 86400).strftime("%Y%m%d")

    for index, session in enumerate(sessions):
        parsed = parse_session(session)
        if not parsed:
            continue
        label, start_minutes, end_minutes, kind = parsed
        if kind == "start":
            next_starts = []
            for other in sessions:
                other_parsed = parse_session(other)
                if other_parsed and other_parsed[3] == "start":
                    next_starts.append(other_parsed[1])
            later_starts = sorted(minute for minute in next_starts if minute > start_minutes)
            effective_end = (later_starts[0] - 1) if later_starts else 1439
            if start_minutes <= now_minutes <= effective_end:
                return f"{today}:{index}:{label}"
            continue
        if start_minutes <= end_minutes:
            if start_minutes <= now_minutes <= end_minutes:
                return f"{today}:{index}:{label}"
        elif now_minutes >= start_minutes:
            return f"{today}:{index}:{label}"
        elif now_minutes <= end_minutes:
            return f"{yesterday}:{index}:{label}"
    return ""


def in_schedule_window():
    return bool(current_session_key())


def mark_session_completed(key):
    completed = [item for item in config.get("completed_session_keys", []) if isinstance(item, str)]
    if key and key not in completed:
        completed.append(key)
    config["completed_session_keys"] = completed[-20:]


def utf16_offset_to_index(text, offset):
    units = 0
    for index, char in enumerate(text):
        if units >= offset:
            return index
        units += len(char.encode("utf-16-le")) // 2
    return len(text)


def template_to_html_from_message(message):
    text = message.text or ""
    html_text = getattr(message, "text_html", None)
    if html_text:
        return html_text

    entities = list(message.entities or [])
    custom_entities = [e for e in entities if str(getattr(e, "type", "")).lower().endswith("custom_emoji")]
    if not custom_entities:
        return text

    pieces = []
    cursor = 0
    for entity in sorted(custom_entities, key=lambda e: e.offset):
        start = utf16_offset_to_index(text, entity.offset)
        end = utf16_offset_to_index(text, entity.offset + entity.length)
        emoji_text = text[start:end] or "🙂"
        pieces.append(escape(text[cursor:start], quote=False))
        pieces.append(f'<tg-emoji emoji-id="{entity.custom_emoji_id}">{escape(emoji_text, quote=False)}</tg-emoji>')
        cursor = end
    pieces.append(escape(text[cursor:], quote=False))
    return "".join(pieces)


def is_admin(user_id):
    admins = config.get("admin_ids", [])
    return not admins or user_id in admins


def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id if update.effective_user else 0
        if not is_admin(user_id):
            if update.callback_query:
                await update.callback_query.answer("Admin only", show_alert=True)
            elif update.message:
                await update.message.reply_text("Admin only.")
            return

        if not config.get("admin_ids"):
            config["admin_ids"] = [user_id]
            save_config()

        return await func(update, context)

    return wrapper


def fetch_api():
    cached = api_cache.get("data")
    if cached and time.time() - api_cache.get("time", 0) < 1.5:
        return deepcopy(cached)
    errors = []
    data = None
    used_url = ""
    header_profiles = [
        {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://ar-lottery01.com",
            "Referer": "https://ar-lottery01.com/",
            "Cache-Control": "no-cache",
        },
        {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/124.0 Mobile Safari/537.36",
            "Accept": "*/*",
            "Referer": "https://ar-lottery01.com/",
        },
    ]
    for url in config.get("api_urls", API_URLS):
        for headers in header_profiles:
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params={"pageNo": 1, "pageSize": 20, "ts": int(time.time() * 1000)},
                    timeout=8,
                )
                response.raise_for_status()
                data = response.json()
                used_url = url
                break
            except Exception as exc:
                errors.append(f"{url}: {exc}")
        if data is not None:
            break
    if data is None:
        error = " | ".join(errors[-3:]) or "API request failed"
        api_status["last_error"] = error
        print(f"API private error: {error}")
        return {"ok": False, "err": error}

    try:
        records = None
        if isinstance(data, dict):
            data_obj = data.get("data")
            if isinstance(data_obj, dict):
                records = data_obj.get("list") or data_obj.get("records") or data_obj.get("data")
            elif isinstance(data_obj, list):
                records = data_obj
            records = records or data.get("list") or data.get("records")
            if not records and isinstance(data.get("result"), dict):
                records = data["result"].get("list") or data["result"].get("records")
            elif not records and isinstance(data.get("result"), list):
                records = data["result"]
        elif isinstance(data, list):
            records = data

        if not records:
            return {"ok": False, "err": "API returned empty history"}

        latest = records[0]
        period = record_period(latest)
        number = record_number(latest)
        if not period or not number:
            return {"ok": False, "err": "API response missing period or number"}

        result = {"ok": True, "period": period, "number": number, "raw": latest, "records": records[:20]}
        api_cache["time"] = time.time()
        api_cache["data"] = result
        api_status["last_error"] = ""
        api_status["last_url"] = used_url
        api_status["last_success"] = datetime.now().isoformat(timespec="seconds")
        return deepcopy(result)
    except Exception as exc:
        api_status["last_error"] = str(exc)
        return {"ok": False, "err": str(exc)}


def next_period(period):
    digits = "".join(ch for ch in str(period) if ch.isdigit())
    if not digits:
        return f"{period}+1"
    nxt = str(int(digits) + 1)
    return nxt.zfill(len(digits))


def analyze(value):
    digits = re.findall(r"\d", str(value))
    if not digits:
        return None, None, None
    number = int(digits[-1])
    size = "BIG" if number >= 5 else "SMALL"
    colors = {
        0: "RED+VIOLET",
        1: "GREEN",
        2: "RED",
        3: "GREEN",
        4: "RED",
        5: "GREEN+VIOLET",
        6: "RED",
        7: "GREEN",
        8: "RED",
        9: "GREEN",
    }
    return number, size, colors[number]


def record_period(record):
    return str(
        record.get("issueNumber")
        or record.get("issue")
        or record.get("period")
        or record.get("id")
        or ""
    )


def record_number(record):
    return str(record.get("number") or record.get("winNumber") or record.get("result") or "")


def find_result_record(api, period):
    for record in api.get("records", []):
        if record_period(record) == str(period):
            number = record_number(record)
            if number:
                return record, number
    return None, ""


def period_number(period):
    digits = "".join(ch for ch in str(period) if ch.isdigit())
    return int(digits) if digits else None


def prediction_is_stale(api, period):
    target = period_number(period)
    available = [period_number(record_period(record)) for record in api.get("records", [])]
    available = [value for value in available if value is not None]
    if target is None or not available:
        return False
    return target < min(available)


def prediction_is_behind_latest(api, period, tolerance=2):
    target = period_number(period)
    latest = period_number(api.get("period"))
    if target is None or latest is None:
        return False
    return latest - target > tolerance


def skip_stale_global_prediction(current, verifying_pending):
    current["verified"] = True
    current["result"] = "STALE_SKIPPED"
    if verifying_pending:
        config["pending_predictions"] = config.get("pending_predictions", [])[1:]
    elif str((config.get("current_prediction") or {}).get("period")) == str(current.get("period")):
        config["current_prediction"] = None
    save_config()


def recover_stale_global_state(api):
    changed = False
    pending = []
    for item in config.get("pending_predictions", []):
        if item and not item.get("verified") and (
            prediction_is_stale(api, item.get("period")) or prediction_is_behind_latest(api, item.get("period"))
        ):
            changed = True
            continue
        pending.append(item)
    config["pending_predictions"] = pending[-5:]
    current = config.get("current_prediction")
    if current and not current.get("verified") and (
        prediction_is_stale(api, current.get("period")) or prediction_is_behind_latest(api, current.get("period"))
    ):
        config["current_prediction"] = None
        changed = True
    if changed:
        save_config()
    return changed


def build_prediction(records):
    recent = []
    for item in records[:8]:
        number, size, color = analyze(item.get("number") or item.get("winNumber") or item.get("result"))
        if number is not None:
            recent.append({"number": number, "size": size, "color": color})

    big_count = sum(1 for item in recent if item["size"] == "BIG")
    red_count = sum(1 for item in recent if "RED" in item["color"])

    target_size = "SMALL" if big_count >= 5 else "BIG" if big_count <= 3 else random.choice(["BIG", "SMALL"])
    target_red = red_count <= 3
    candidates = []
    for number in range(10):
        _, size, color = analyze(number)
        if size == target_size and (("RED" in color) == target_red):
            candidates.append(number)
    if not candidates:
        candidates = list(range(10))

    number = random.choice(candidates)
    _, size, color = analyze(number)
    confidence = random.randint(82, 96)
    return number, size, color, confidence


def format_template(name, values):
    template = config["templates"].get(name, DEFAULT_CONFIG["templates"][name])
    try:
        return template.format(**values)
    except KeyError as exc:
        return f"Template error: missing {exc}\n\n{template}"


async def get_user_client(connect=True):
    global user_client
    api_id = str(config.get("api_id") or "").strip()
    api_hash = str(config.get("api_hash") or "").strip()
    if not api_id or not api_hash:
        return None

    if user_client is None:
        user_client = TelegramClient(str(SESSION_FILE), int(api_id), api_hash)
    if connect and not user_client.is_connected():
        await user_client.connect()
    return user_client


async def userbot_status():
    client = await get_user_client()
    if not client:
        return "Not configured"
    try:
        return "Logged in" if await client.is_user_authorized() else "Login needed"
    except Exception as exc:
        return f"Error: {exc}"


async def logout_userbot(delete_session=True):
    global user_client
    client = await get_user_client(connect=True)
    if client:
        try:
            if await client.is_user_authorized():
                await client.log_out()
        except Exception as exc:
            print(f"userbot logout error: {exc}")
        try:
            await client.disconnect()
        except Exception:
            pass
    user_client = None

    config["phone"] = ""
    config["login_phone_code_hash"] = ""
    config["prediction_active"] = False
    config["auto_mode"] = False
    save_config()

    if delete_session:
        for path in BASE_DIR.glob("userbot.session*"):
            try:
                path.unlink()
            except Exception as exc:
                print(f"session delete failed ({path}): {exc}")

    return True


async def send_login_code(phone):
    config["phone"] = phone
    save_config()

    client = await get_user_client()
    if not client:
        return False, "API config missing. API ID/API HASH are not saved."
    if await client.is_user_authorized():
        return True, "already_logged_in"

    try:
        sent = await client.send_code_request(phone)
        config["login_phone_code_hash"] = sent.phone_code_hash
        save_config()
        return True, "code_sent"
    except SendCodeUnavailableError:
        return False, (
            "Telegram ne OTP resend limit temporarily block kar di hai. "
            "Agar OTP pehle aa chuka hai to wahi OTP bhejo, warna 10-30 minutes wait karke Resend OTP dabao."
        )
    except FloodWaitError as exc:
        minutes = max(1, int(exc.seconds // 60) + (1 if exc.seconds % 60 else 0))
        return False, f"Telegram flood wait laga raha hai. {minutes} minute baad try karo."
    except PhoneNumberInvalidError:
        return False, "Phone number invalid hai. Country code ke saath number bhejo."
    except Exception as exc:
        return False, f"OTP send failed: {exc}"


async def sign_in_with_code(code):
    client = await get_user_client()
    if not client:
        return False, "Userbot is not configured"
    try:
        await client.sign_in(
            phone=config.get("phone"),
            code=code,
            phone_code_hash=config.get("login_phone_code_hash") or None,
        )
        config["login_phone_code_hash"] = ""
        save_config()
        return True, "logged_in"
    except SessionPasswordNeededError:
        return False, "password_needed"
    except PhoneCodeInvalidError:
        return False, "invalid_code"
    except Exception as exc:
        return False, str(exc)


async def sign_in_with_password(password):
    client = await get_user_client()
    if not client:
        return False, "Userbot is not configured"
    try:
        await client.sign_in(password=password)
        return True, "logged_in"
    except Exception as exc:
        return False, str(exc)


async def send_user_message(text, image_path="", bot=None, channels=None, sender_mode=None, prediction_size=None):
    channels = channels if channels is not None else get_channels()
    if not channels:
        return False, "No channel set"

    failed = []
    html_tags = ["<tg-emoji", "<b>", "<strong>", "<i>", "<em>", "<u>", "<s>", "<strike>", "<del>", "<code>", "<pre>", "<a ", "<blockquote", "<span"]
    parse_mode = "html" if any(tag in text for tag in html_tags) else None
    for channel in channels:
        try:
            mode = sender_mode or channel_sender_mode(channel)
            selected_image = prediction_image(prediction_size, channel) if prediction_size else image_path
            if mode == "main_bot":
                if not bot:
                    raise RuntimeError("Main bot is unavailable")
                if selected_image:
                    try:
                        with Path(selected_image).open("rb") as image:
                            await bot.send_photo(chat_id=channel, photo=image, caption=text, parse_mode=ParseMode.HTML if parse_mode else None)
                    except Exception as image_exc:
                        print(f"image send failed for {channel}; using text fallback: {image_exc}")
                        await bot.send_message(chat_id=channel, text=text, parse_mode=ParseMode.HTML if parse_mode else None)
                else:
                    await bot.send_message(chat_id=channel, text=text, parse_mode=ParseMode.HTML if parse_mode else None)
            else:
                client = await get_user_client()
                if not client or not await client.is_user_authorized():
                    raise RuntimeError("Userbot is not logged in")
                target = await resolve_channel_target(client, channel)
                if selected_image:
                    try:
                        await client.send_file(target, selected_image, caption=text, parse_mode=parse_mode)
                    except Exception as image_exc:
                        print(f"userbot image send failed for {channel}; using text fallback: {image_exc}")
                        await client.send_message(target, text, parse_mode=parse_mode)
                else:
                    await client.send_message(target, text, parse_mode=parse_mode)
        except Exception as exc:
            failed.append(f"{channel}: {exc}")
    if failed:
        return False, "; ".join(failed)
    return True, f"sent to {len(channels)} channel(s)"


async def send_sticker(kind, bot=None):
    channels = get_channels()
    if not channels:
        return False

    sticker_id = config.get("stickers", {}).get(kind)
    if not sticker_id:
        print(f"sticker file_id missing ({kind}). Set it from admin panel.")
        return False
    if not bot:
        print(f"main bot unavailable; sticker skipped ({kind})")
        return False

    sent_any = False
    for channel in channels:
        try:
            await bot.send_sticker(chat_id=channel, sticker=sticker_id)
            sent_any = True
        except Exception as exc:
            print(f"sticker send failed ({kind}) to {channel}: {exc}")
    return sent_any


async def send_sticker_to_channels(kind, channels, bot):
    sticker_id = config.get("stickers", {}).get(kind)
    if not sticker_id or not bot:
        return False
    sent = False
    for channel in channels:
        try:
            await bot.send_sticker(chat_id=channel, sticker=sticker_id)
            sent = True
        except Exception as exc:
            print(f"sticker send failed ({kind}) to {channel}: {exc}")
    return sent


async def send_prediction(bot=None, wait_until=None):
    if not config.get("prediction_active"):
        return False, "Prediction is stopped"
    if not in_schedule_window():
        return False, "Outside scheduled session"

    api = await asyncio.to_thread(fetch_api)
    if not api["ok"]:
        return False, public_service_error()

    period = next_period(api["period"])
    if config.get("last_period_sent") == period:
        return False, f"Prediction already sent for {period}"

    previous = config.get("current_prediction")
    if previous and not previous.get("verified"):
        pending = config.setdefault("pending_predictions", [])
        if not any(str(item.get("period")) == str(previous.get("period")) for item in pending):
            pending.append(previous)
            config["pending_predictions"] = pending[-5:]

    number, size, color, confidence = build_prediction(api["records"])
    now = datetime.now().strftime("%I:%M:%S %p")

    values = {
        "period": period,
        "number": number,
        "number_emoji": NUMBER_EMOJI[number],
        "size": size,
        "size_icon": SIZE_ICON[size],
        "color": color,
        "color_icon": COLOR_ICON[color],
        "confidence": confidence,
        "time": now,
        "bet_level": config.get("martingale", {}).get("level", 0),
        "bet_amount": config.get("martingale", {}).get("base_bet", 1)
        * (config.get("martingale", {}).get("multiplier", 2) ** config.get("martingale", {}).get("level", 0)),
    }
    text = format_template("prediction", values)

    if wait_until:
        delay = wait_until - time.time()
        if delay > 0:
            await asyncio.sleep(delay)

    if config.get("send_prediction_message", True):
        ok, msg = await send_user_message(text, bot=bot, prediction_size=size)
        if not ok:
            return False, msg

    config["current_prediction"] = {
        "period": period,
        "number": number,
        "size": size,
        "color": color,
        "confidence": confidence,
        "time": now,
        "verified": False,
    }
    config["last_period_sent"] = period
    save_config()
    return True, f"Prediction sent for {period}"


async def verify_prediction(bot=None):
    pending = config.get("pending_predictions", [])
    current = pending[0] if pending else config.get("current_prediction")
    verifying_pending = bool(pending)
    if not current:
        return False, "No prediction to verify"
    if current.get("verified"):
        return False, "Already verified"

    api = await asyncio.to_thread(fetch_api)
    if not api["ok"]:
        return False, public_service_error()

    result_record, actual_number = find_result_record(api, current["period"])
    if not result_record:
        if prediction_is_stale(api, current["period"]) or prediction_is_behind_latest(api, current["period"]):
            skip_stale_global_prediction(current, verifying_pending)
            return True, f"Stale prediction skipped: {current['period']}"
        return False, f"Result not ready. Latest: {api['period']} Waiting: {current['period']}"

    actual_number, actual_size, actual_color = analyze(actual_number)
    number_win = actual_number == current["number"]
    size_win = actual_size == current["size"]
    color_win = actual_color == current["color"]
    is_win = size_win or color_win or number_win

    matched = []
    if number_win:
        matched.append("Number")
    if size_win:
        matched.append("Size")
    if color_win:
        matched.append("Color")

    values = {
        "period": current["period"],
        "pred_number": current["number"],
        "pred_size": current["size"],
        "pred_color": current["color"],
        "actual_number": actual_number,
        "actual_size": actual_size,
        "actual_color": actual_color,
        "matched": ", ".join(matched) if matched else "None",
    }

    text = format_template("win" if is_win else "loss", values)
    await send_sticker("win" if is_win else "loss", bot)
    should_send_result_message = config.get("send_win_message", True) if is_win else config.get("send_loss_message", False)
    if should_send_result_message:
        ok, msg = await send_user_message(text, bot=bot)
        if not ok:
            return False, msg

    config["stats"]["total"] += 1
    if is_win:
        config["stats"]["wins"] += 1
        config["session_wins"] = config.get("session_wins", 0) + 1
        config["martingale"]["level"] = 0
    else:
        config["stats"]["losses"] += 1
        if config.get("martingale", {}).get("enabled", True):
            max_level = config["martingale"].get("max_level", 4)
            config["martingale"]["level"] = min(config["martingale"].get("level", 0) + 1, max_level)

    config["history"].insert(
        0,
        {
            "period": current["period"],
            "predicted": {
                "number": current["number"],
                "size": current["size"],
                "color": current["color"],
            },
            "actual": {"number": actual_number, "size": actual_size, "color": actual_color},
            "result": "WIN" if is_win else "LOSS",
            "time": datetime.now().strftime("%I:%M:%S %p"),
        },
    )
    config["history"] = config["history"][:100]
    current["verified"] = True
    if verifying_pending:
        config["pending_predictions"] = pending[1:]
    elif config.get("current_prediction") and str(config["current_prediction"].get("period")) == str(current.get("period")):
        config["current_prediction"] = current
    stop_after = int(config.get("stop_after_wins") or 0)
    if is_win and stop_after > 0 and config.get("session_wins", 0) >= stop_after:
        config["prediction_active"] = False
        if config.get("mode") == "scheduled":
            mark_session_completed(config.get("active_session_key") or current_session_key())
            config["session_started_by_schedule"] = False
            config["active_session_key"] = ""
        else:
            config["auto_mode"] = False
        await send_sticker("end", bot)
    save_config()
    return True, "WIN" if is_win else "LOSS"


def main_keyboard():
    active = "ON" if config.get("prediction_active") else "OFF"
    auto = "ON" if config.get("auto_mode") else "OFF"
    return InlineKeyboardMarkup(
        [
            [
                btn(f"Prediction Engine: {active}", "toggle_prediction", "zap", "success" if active == "ON" else "danger"),
                btn(f"Automation: {auto}", "toggle_auto", "comet", "success" if auto == "ON" else "danger"),
            ],
            [
                btn("Users & Access", "users_menu", "shield"),
                btn("Channels & Routing", "bot_menu", "globe"),
            ],
            [
                btn("Schedules & Sessions", "schedule_menu", "candle"),
                btn("Prediction Content", "content_menu", "chat"),
            ],
            [
                btn("Reports & Statistics", "reports_menu", "chart"),
                btn("System Controls", "system_menu", "crystal"),
            ],
        ]
    )


async def dashboard_text():
    stats = config["stats"]
    total = stats.get("total", 0)
    wr = (stats.get("wins", 0) / total * 100) if total else 0
    user_status = await userbot_status()
    current = config.get("current_prediction") or {}
    current_line = current.get("period", "None")
    channels = get_channels()
    channel = ", ".join(channels) if channels else "Not set"
    return (
        f"{pe('crystal')} <b>ADVANCED PREDICTION CONTROL</b>\n"
        f"<blockquote>{pe('zap')} Prediction: <b>{'ACTIVE' if config.get('prediction_active') else 'STOPPED'}</b>\n"
        f"{pe('comet')} Automation: <b>{'ON' if config.get('auto_mode') else 'OFF'}</b> · {config.get('auto_interval')}s\n"
        f"{pe('shield')} Sender: <b>{escape(config.get('sender_mode', 'userbot'))}</b>\n"
        f"{pe('globe')} Channels: <b>{len(channels)}</b></blockquote>\n"
        f"{pe('eye')} <b>Live Status</b>\n"
        f"Current period: <code>{escape(str(current_line))}</code>\n"
        f"Userbot: <b>{escape(user_status)}</b>\n"
        f"Mode: <b>{escape(config.get('mode', '24x7'))}</b> · Target wins: <b>{config.get('stop_after_wins') or 'OFF'}</b>\n\n"
        f"{pe('chart')} <b>Performance</b>\n"
        f"<blockquote>Total: <b>{total}</b> · Wins: <b>{stats.get('wins', 0)}</b> · Losses: <b>{stats.get('losses', 0)}</b>\n"
        f"Win rate: <b>{wr:.1f}%</b> · MG level: <b>{config.get('martingale', {}).get('level', 0)}</b></blockquote>\n"
        f"{pe('pin')} <i>Choose an action below. Changes apply instantly.</i>"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        profile = get_user_profile(user_id)
        settings = effective_user_settings(user_id)
        access = user_has_access(user_id)
        keyboard = user_keyboard()
        plan = profile.get("plan", "free_trial").replace("_", " ").title()
        features = "Premium prediction tools unlocked" if user_is_premium(user_id) else "Basic tools · Premium features locked"
        text = (
            f"{pe('party')} <b>WELCOME TO PREDICTION CONTROL</b>\n\n"
            f"<blockquote>{pe('shield')} Account: <b>{'ACTIVE' if access else 'EXPIRED'}</b>\n"
            f"{pe('money')} Plan: <b>{escape(plan)}</b>\n"
            f"{pe('candle')} Valid until: <code>{escape(profile.get('subscription_until', 'Unknown'))}</code>\n"
            f"{pe('globe')} Connected channels: <b>{len(profile.get('channels', []))}</b>\n"
            f"{pe('zap')} Sender: <b>{escape(settings.get('sender_mode', 'userbot'))}</b></blockquote>\n"
            f"{pe('info')} <i>{features}</i>\n\n"
            f"{pe('pin')} Connect your channel, check your status, or explore plans below."
        )
        if update.message:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        else:
            await update.callback_query.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        return
    if update.message:
        await update.message.reply_text(await dashboard_text(), reply_markup=main_keyboard(), parse_mode=ParseMode.HTML)
    else:
        query = update.callback_query
        await query.edit_message_text(await dashboard_text(), reply_markup=main_keyboard(), parse_mode=ParseMode.HTML)


@admin_only
async def setup_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("/setupuser <phone>\nAPI ID/API HASH already saved.")
        return

    if len(context.args) == 1:
        config["phone"] = context.args[0].strip()
    else:
        config["api_id"] = context.args[0].strip()
        config["api_hash"] = context.args[1].strip()
        if len(context.args) >= 3:
            config["phone"] = context.args[2].strip()

    save_config()
    global user_client
    if user_client:
        await user_client.disconnect()
        user_client = None
    await update.message.reply_text("Userbot setup saved. Now use /loginuser.")


@admin_only
async def login_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = (context.args[0].strip() if context.args else "") or config.get("phone") or ""
    if not phone:
        await update.message.reply_text("Send /loginuser <phone_number>")
        return

    ok, msg = await send_login_code(phone)
    if ok and msg == "already_logged_in":
        await update.message.reply_text("Userbot already logged in.")
    elif ok:
        await update.message.reply_text("OTP sent on Telegram. Reply with OTP or use /code 12345")
    else:
        await update.message.reply_text(msg)


@admin_only
async def code_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("/code <otp>")
        return
    ok, msg = await sign_in_with_code("".join(context.args))
    if ok:
        await update.message.reply_text("Userbot login done. Channel messages will now go from user account.")
        await ensure_session_monitor(context, update.effective_chat.id)
    elif msg == "password_needed":
        await update.message.reply_text("2FA enabled. Reply: /password your_password")
    elif msg == "invalid_code":
        await update.message.reply_text("Invalid OTP. Try /loginuser again.")
    else:
        await update.message.reply_text(f"Login failed: {msg}")


@admin_only
async def password_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("/password <2fa_password>")
        return
    ok, msg = await sign_in_with_password(" ".join(context.args))
    if ok:
        await update.message.reply_text("Userbot login done.")
        await ensure_session_monitor(context, update.effective_chat.id)
    else:
        await update.message.reply_text(f"Login failed: {msg}")


@admin_only
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("/addadmin <user_id>")
        return
    admin_id = int(context.args[0])
    if admin_id not in config["admin_ids"]:
        config["admin_ids"].append(admin_id)
        save_config()
    await update.message.reply_text(f"Admin added: {admin_id}")


@admin_only
async def grant_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("/grant <user_id> <days>")
        return
    try:
        user_id, days = int(context.args[0]), int(context.args[1])
    except ValueError:
        await update.message.reply_text("User ID and days must be numbers.")
        return
    profile = get_user_profile(user_id)
    try:
        current = datetime.fromisoformat(profile.get("subscription_until", ""))
    except ValueError:
        current = datetime.now()
    profile["subscription_until"] = (max(current, datetime.now()) + timedelta(days=days)).isoformat(timespec="seconds")
    save_config()
    await update.message.reply_text(f"Subscription updated for {user_id}: {profile['subscription_until']}")


@admin_only
async def grant_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("/premium <user_id> [on/off]")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("User ID must be a number.")
        return
    profile = get_user_profile(user_id)
    enabled = len(context.args) < 2 or context.args[1].lower() not in {"off", "no", "0"}
    profile["premium_access"] = enabled
    if enabled and profile.get("plan") == "free_trial":
        profile["plan"] = "premium"
    save_config()
    await update.message.reply_text(f"Premium access {'enabled' if enabled else 'disabled'} for {user_id}.")


async def remove_auto_jobs(context):
    for name in ["auto_prediction", "auto_verify"]:
        for job in context.job_queue.get_jobs_by_name(name):
            job.schedule_removal()


async def remove_session_jobs(context):
    for job in context.job_queue.get_jobs_by_name("session_monitor"):
        job.schedule_removal()


def seconds_until_next_boundary(interval=None):
    return max(0.1, next_boundary_timestamp(interval=interval) - time.time())


def next_boundary_timestamp(after=None, interval=None):
    interval = max(15, int(interval or config.get("auto_interval", 60)))
    now = time.time() if after is None else float(after)
    delay = interval - (now % interval)
    if delay < 0.25:
        delay += interval
    return now + delay


def schedule_auto_prediction(context, chat_id, target_ts=None):
    target_ts = target_ts or next_boundary_timestamp()
    lead = max(0, float(config.get("prediction_prepare_seconds", 2)))
    context.job_queue.run_once(
        auto_prediction_job,
        when=max(0.1, target_ts - time.time() - lead),
        chat_id=chat_id,
        name="auto_prediction",
        data={"target_ts": target_ts},
    )


async def ensure_auto_job(context, chat_id):
    await remove_auto_jobs(context)
    if config.get("auto_mode") and config.get("prediction_active"):
        schedule_auto_prediction(context, chat_id)


async def ensure_session_monitor(context, chat_id):
    await remove_session_jobs(context)
    if config.get("auto_mode") and config.get("mode") == "scheduled":
        context.job_queue.run_repeating(
            session_monitor_job,
            interval=max(5, int(config.get("schedule_monitor_interval", 5))),
            first=1,
            chat_id=chat_id,
            name="session_monitor",
            job_kwargs={"coalesce": True, "max_instances": 2, "misfire_grace_time": 15},
        )


async def auto_prediction_job(context: ContextTypes.DEFAULT_TYPE):
    if not config.get("auto_mode") or not config.get("prediction_active"):
        return

    target_ts = (context.job.data or {}).get("target_ts") if context.job else None
    target_ts = target_ts or next_boundary_timestamp()
    chat_id = context.job.chat_id if context.job else None

    delay = target_ts - time.time()
    if delay > 0:
        await asyncio.sleep(delay)

    current = config.get("current_prediction")
    if current and not current.get("verified"):
        ok, msg = await verify_prediction(context.bot)
        print(f"auto verify {datetime.now().strftime('%H:%M:%S')}: {msg}")
        if not config.get("auto_mode") or not config.get("prediction_active"):
            return
        if not ok and "Result not ready" in msg:
            retry_count = int((context.job.data or {}).get("retry_count", 0)) + 1
            if retry_count >= 3:
                current = config.get("current_prediction")
                if current:
                    skip_stale_global_prediction(current, False)
                print("auto verify: retry limit reached; skipped blocked prediction")
                schedule_auto_prediction(context, chat_id, next_boundary_timestamp())
                return
            context.job_queue.run_once(
                auto_prediction_job,
                when=5,
                chat_id=chat_id,
                name="auto_prediction",
                data={"target_ts": time.time(), "retry_count": retry_count},
                job_kwargs={"misfire_grace_time": 15},
            )
            return
        if not ok:
            return

    ok, msg = await send_prediction(context.bot)
    print(f"auto send {datetime.now().strftime('%H:%M:%S')}: {msg}")
    if ok and config.get("auto_mode") and config.get("prediction_active"):
        schedule_auto_prediction(context, chat_id, next_boundary_timestamp())


async def start_scheduled_session(context, session_key):
    if session_key in config.get("completed_session_keys", []):
        return
    config["prediction_active"] = True
    config["session_started_by_schedule"] = True
    config["active_session_key"] = session_key
    config["session_wins"] = 0
    config["pending_predictions"] = []
    config["current_prediction"] = None
    config["martingale"]["level"] = 0
    save_config()
    await send_sticker("start", context.bot)
    ok, msg = await send_prediction(context.bot)
    print(f"scheduled first prediction: {msg}")
    await ensure_auto_job(context, context.job.chat_id if context.job else None)
    print(f"scheduled session started: {session_key}")


async def stop_scheduled_session(context, reason="Session ended"):
    if not config.get("prediction_active") and not config.get("session_started_by_schedule"):
        return
    config["prediction_active"] = False
    config["session_started_by_schedule"] = False
    config["active_session_key"] = ""
    config["pending_predictions"] = []
    await remove_auto_jobs(context)
    save_config()
    await send_sticker("end", context.bot)
    print(f"scheduled session stopped: {reason}")


async def session_monitor_job(context: ContextTypes.DEFAULT_TYPE):
    if not config.get("auto_mode") or config.get("mode") != "scheduled":
        await stop_scheduled_session(context, "schedule disabled")
        if context.job:
            context.job.schedule_removal()
        return

    key = current_session_key()
    active_key = config.get("active_session_key", "")
    completed = set(config.get("completed_session_keys", []))

    if key and key not in completed:
        if not config.get("prediction_active") or active_key != key:
            await start_scheduled_session(context, key)
        return

    if config.get("prediction_active") and config.get("session_started_by_schedule"):
        await stop_scheduled_session(context, "outside schedule or target reached")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    await react(update, "eyes")

    if not is_admin(update.effective_user.id):
        if data == "home":
            await start(update, context)
        elif data in ["user_connect", "user_set_channel"]:
            if not user_has_access(update.effective_user.id):
                await query.edit_message_text("Your trial/subscription has expired. Contact the admin.")
                return
            context.user_data["awaiting"] = "user_channel"
            await query.edit_message_text(
                f"{pe('link')} <b>CONNECT MY CHANNEL</b>\n\n"
                f"{pe('pin')} Add this bot as an admin in your channel first.\n"
                f"{pe('chat')} Then send the public <code>@channel</code> username or numeric channel ID here.\n\n"
                f"{pe('shield')} Your channel and settings remain separate from every other user.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[back_btn()]]),
            )
        elif data == "user_channels":
            profile = get_user_profile(update.effective_user.id)
            channels = profile.get("channels", [])
            settings = effective_user_settings(update.effective_user.id)
            premium = user_is_premium(update.effective_user.id)
            kb = InlineKeyboardMarkup(
                [
                    [btn("Connect / Replace Channel", "user_connect", "link", "primary")],
                    [btn(f"{'Stop' if profile.get('prediction_active') else 'Start'} Predictions", "user_toggle_predictions", "stop" if profile.get("prediction_active") else "zap", "danger" if profile.get("prediction_active") else "success")],
                    [btn(f"Mode: {settings.get('mode', '24x7')}", "user_toggle_schedule_mode", "candle")],
                    [btn("Custom Schedule", "user_custom_schedule", "comet"), btn("Message Template", "user_custom_template", "chat")],
                    [btn("Reset Settings", "user_reset", "no", "danger"), back_btn()],
                ]
            )
            await query.edit_message_text(
                f"{pe('globe')} <b>MY CHANNELS</b>\n\n"
                f"<blockquote>Connected: <b>{len(channels)}</b>\n"
                f"Channel: <b>{escape(channels[0]) if channels else 'Not connected'}</b>\n"
                f"Plan limit: <b>{4 if premium else 1}</b>\n"
                f"Schedule: <b>{escape(settings.get('mode', '24x7'))}</b></blockquote>\n"
                f"{pe('shield')} <i>Advanced schedule and templates require premium access.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        elif data == "user_plans":
            await query.edit_message_text(
                f"{pe('money')} <b>SUBSCRIPTION PLANS</b>\n\n"
                f"<blockquote>{pe('star')} <b>Starter — Rs.599/month</b>\n1 channel · Basic predictions\n\n"
                f"{pe('zap')} <b>Pro — Rs.999/month</b>\n2 channels · Custom schedules · Templates\n\n"
                f"{pe('crystal')} <b>Premium — Rs.1499/month</b>\n4 channels · All advanced prediction features</blockquote>\n"
                f"{pe('chat')} Contact: <b>@itsukiarai</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[back_btn()]]),
            )
        elif data == "user_status":
            profile = get_user_profile(update.effective_user.id)
            settings = effective_user_settings(update.effective_user.id)
            await query.edit_message_text(
                f"{pe('chart')} <b>ACCOUNT STATUS</b>\n\n"
                f"<blockquote>{pe('shield')} Access: <b>{'ACTIVE' if user_has_access(update.effective_user.id) else 'EXPIRED'}</b>\n"
                f"{pe('money')} Plan: <b>{escape(profile.get('plan', 'free_trial').replace('_', ' ').title())}</b>\n"
                f"{pe('globe')} Channels: <b>{len(profile.get('channels', []))}</b>\n"
                f"{pe('zap')} Predictions: <b>{'RUNNING' if profile.get('prediction_active') else 'STOPPED'}</b>\n"
                f"{pe('candle')} Mode: <b>{escape(settings.get('mode', '24x7'))}</b>\n"
                f"{pe('crystal')} Premium: <b>{'UNLOCKED' if user_is_premium(update.effective_user.id) else 'LOCKED'}</b></blockquote>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[back_btn()]]),
            )
        elif data == "user_help":
            await query.edit_message_text(
                f"{pe('q')} <b>HELP CENTER</b>\n\n"
                f"{pe('link')} <b>Connect:</b> Add the bot as channel admin, then send your channel username.\n\n"
                f"{pe('globe')} <b>My Channels:</b> Manage channel, prediction mode, schedules, and templates.\n\n"
                f"{pe('shield')} Every user's channels and settings are stored separately.\n\n"
                f"{pe('chat')} Support: <b>@itsukiarai</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[back_btn()]]),
            )
        elif data == "user_about":
            await query.edit_message_text(
                f"{pe('crystal')} <b>ABOUT THIS BOT</b>\n\n"
                f"<b>Multi-Platform Prediction Bot</b>\nVersion: <code>1.1</code>\n\n"
                f"{pe('zap')} Wingo 1 Min Auto Predictions\n"
                f"{pe('chart')} Martingale Betting Strategy\n"
                f"{pe('candle')} Multi-Session Management\n"
                f"{pe('check')} Auto Win/Loss Tracking\n"
                f"{pe('mega')} Daily & Session Reports\n\n"
                f"<b>Supported Platforms</b>\nOKWin · Sikkim Game · IN999 · 91Club · Raja Games · Jalwa\n\n"
                f"{pe('chat')} Admin Contact: <b>@itsukiarai</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[back_btn()]]),
            )
        elif data == "user_toggle_predictions":
            profile = get_user_profile(update.effective_user.id)
            if profile.get("prediction_active"):
                profile["prediction_active"] = False
                await remove_user_prediction_jobs(context, update.effective_user.id)
                await send_sticker_to_channels("end", profile.get("channels", []), context.bot)
                message = "Predictions stopped."
            else:
                if not user_has_access(update.effective_user.id):
                    await query.edit_message_text("Your trial/subscription has expired.")
                    return
                if not profile.get("channels"):
                    await query.edit_message_text("Connect your channel before starting predictions.", reply_markup=InlineKeyboardMarkup([[btn("Connect Channel", "user_connect", "link")]]))
                    return
                profile["prediction_active"] = True
                profile["current_prediction"] = None
                profile["last_period_sent"] = ""
                if not user_in_schedule_window(update.effective_user.id):
                    schedule_user_prediction(context, update.effective_user.id, query.message.chat_id, delay=30)
                    ok, message = True, "Predictions started. Waiting for your scheduled session."
                else:
                    await send_sticker_to_channels("start", profile.get("channels", []), context.bot)
                    ok, message = await send_user_profile_prediction(update.effective_user.id, context.bot)
                if ok and not context.job_queue.get_jobs_by_name(user_job_name(update.effective_user.id)):
                    schedule_user_prediction(context, update.effective_user.id, query.message.chat_id)
                else:
                    profile["prediction_active"] = False
            save_config()
            await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup([[btn("Back to My Channels", "user_channels", "globe")]]))
        elif data == "user_toggle_schedule_mode":
            if not user_is_premium(update.effective_user.id):
                await query.edit_message_text("Premium access is required for custom prediction modes.", reply_markup=InlineKeyboardMarkup([[btn("View Plans", "user_plans", "money"), back_btn()]]))
                return
            profile = get_user_profile(update.effective_user.id)
            overrides = profile.setdefault("overrides", {})
            overrides["mode"] = "scheduled" if effective_user_settings(update.effective_user.id).get("mode", "24x7") == "24x7" else "24x7"
            save_config()
            await query.edit_message_text("Prediction mode updated.", reply_markup=InlineKeyboardMarkup([[btn("Back to My Channels", "user_channels", "globe")]]))
        elif data == "user_custom_schedule":
            if not user_is_premium(update.effective_user.id):
                await query.edit_message_text("Custom schedules are a premium feature.", reply_markup=InlineKeyboardMarkup([[btn("View Plans", "user_plans", "money"), back_btn()]]))
                return
            context.user_data["awaiting"] = "user_schedule"
            await query.edit_message_text("Send sessions one per line.\nExamples:\n10:00-11:00\n12:00-13:00\n14:00-15:00", reply_markup=InlineKeyboardMarkup([[btn("Cancel", "user_channels", "no")]]))
        elif data == "user_custom_template":
            if not user_is_premium(update.effective_user.id):
                await query.edit_message_text("Custom prediction messages are a premium feature.", reply_markup=InlineKeyboardMarkup([[btn("View Plans", "user_plans", "money"), back_btn()]]))
                return
            context.user_data["awaiting"] = "user_template"
            await query.edit_message_text("Send your custom prediction template.\nVariables: {period} {number} {size} {color} {confidence} {time}", reply_markup=InlineKeyboardMarkup([[btn("Cancel", "user_channels", "no")]]))
        elif data == "user_reset":
            profile = get_user_profile(update.effective_user.id)
            profile["overrides"] = {}
            profile["channels"] = []
            save_config()
            await start(update, context)
        elif data == "user_toggle_sender":
            profile = get_user_profile(update.effective_user.id)
            overrides = profile.setdefault("overrides", {})
            current = effective_user_settings(update.effective_user.id).get("sender_mode", "userbot")
            overrides["sender_mode"] = "main_bot" if current == "userbot" else "userbot"
            save_config()
            await start(update, context)
        elif data == "user_send_prediction":
            if not user_has_access(update.effective_user.id):
                await query.edit_message_text("Your trial/subscription has expired. Contact the admin.")
                return
            profile = get_user_profile(update.effective_user.id)
            profile["prediction_active"] = True
            ok, msg = await send_user_profile_prediction(update.effective_user.id, context.bot)
            if ok:
                await remove_user_prediction_jobs(context, update.effective_user.id)
                schedule_user_prediction(context, update.effective_user.id, query.message.chat_id)
            else:
                profile["prediction_active"] = False
                save_config()
            await query.edit_message_text(msg if ok else f"Failed: {msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="home")]]))
        else:
            await query.edit_message_text("Admin only.")
        return

    if data == "toggle_prediction":
        was_active = config.get("prediction_active")
        config["prediction_active"] = not was_active
        if config["prediction_active"]:
            config["session_wins"] = 0
            config["martingale"]["level"] = 0
        save_config()
        await send_sticker("start" if config["prediction_active"] else "end", context.bot)
        if config["prediction_active"]:
            ok, msg = await send_prediction(context.bot)
            print(f"manual start prediction: {msg}")
        await ensure_auto_job(context, query.message.chat_id)
        await ensure_session_monitor(context, query.message.chat_id)
        await start(update, context)

    elif data == "toggle_auto":
        config["auto_mode"] = not config.get("auto_mode")
        save_config()
        await ensure_auto_job(context, query.message.chat_id)
        await ensure_session_monitor(context, query.message.chat_id)
        await start(update, context)

    elif data == "channels_menu":
        channels = get_channels()
        rows = [
            [btn("Add Channel", "add_channel", "globe", "primary"), btn("Replace All", "replace_channels", "comet")],
            [btn("Test Channel Delivery", "test_channels", "zap", "success")],
        ]
        for i, channel in enumerate(channels[:10]):
            rows.append([btn(f"Remove {channel}", f"remove_channel:{i}", "cross", "danger")])
        rows.append([back_btn()])
        await query.edit_message_text(
            "Channels\n\n" + ("\n".join(channels) if channels else "No channel set"),
            reply_markup=InlineKeyboardMarkup(rows),
        )

    elif data == "bot_menu":
        mode = config.get("sender_mode", "userbot")
        rows = [
            [btn(f"Default Sender: {mode}", "toggle_sender_mode", "shield", "primary")],
        ]
        for i, channel in enumerate(get_channels()[:10]):
            rows.append(
                [
                    btn(f"{channel}: {channel_sender_mode(channel)}", f"toggle_channel_sender:{i}", "zap"),
                    btn("Images", f"channel_images:{i}", "eye"),
                ]
            )
        rows.append([back_btn()])
        await query.edit_message_text(
            "Bot Management\n\nSet the default sender, or override the sender independently for each channel.",
            reply_markup=InlineKeyboardMarkup(rows),
        )

    elif data == "toggle_sender_mode":
        config["sender_mode"] = "main_bot" if config.get("sender_mode") == "userbot" else "userbot"
        save_config()
        await query.edit_message_text("Default sender updated.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="bot_menu")]]))

    elif data.startswith("toggle_channel_sender:"):
        channels = get_channels()
        idx = int(data.split(":", 1)[1])
        if 0 <= idx < len(channels):
            channel = channels[idx]
            current = channel_sender_mode(channel)
            config.setdefault("channel_assignments", {})[channel] = "main_bot" if current == "userbot" else "userbot"
            save_config()
        await query.edit_message_text("Channel sender updated.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="bot_menu")]]))

    elif data.startswith("channel_images:"):
        channels = get_channels()
        idx = int(data.split(":", 1)[1])
        if not 0 <= idx < len(channels):
            await query.edit_message_text("Channel not found.")
            return
        channel = channels[idx]
        items = config.get("channel_prediction_images", {}).get(channel, {})
        kb = InlineKeyboardMarkup(
            [
                [btn("Set BIG Override", f"channel_image_set:{idx}:BIG", "eye"), btn(f"BIG {'ON' if items.get('BIG', {}).get('enabled') else 'DEFAULT'}", f"channel_image_toggle:{idx}:BIG", "green")],
                [btn("Set SMALL Override", f"channel_image_set:{idx}:SMALL", "eye"), btn(f"SMALL {'ON' if items.get('SMALL', {}).get('enabled') else 'DEFAULT'}", f"channel_image_toggle:{idx}:SMALL", "green")],
                [back_btn("bot_menu")],
            ]
        )
        await query.edit_message_text(f"Channel Images\n\n{channel}\nDisabled/missing overrides automatically use the global BIG/SMALL image.", reply_markup=kb)

    elif data.startswith("channel_image_set:"):
        _, idx, size = data.split(":")
        context.user_data["awaiting"] = f"channel_prediction_image:{idx}:{size}"
        await query.edit_message_text(f"Send the {size} override image for this channel.")

    elif data.startswith("channel_image_toggle:"):
        _, idx, size = data.split(":")
        channels = get_channels()
        if 0 <= int(idx) < len(channels):
            channel = channels[int(idx)]
            item = config.setdefault("channel_prediction_images", {}).setdefault(channel, {}).setdefault(size, {})
            item["enabled"] = not item.get("enabled", False)
            save_config()
        await query.edit_message_text("Channel image override updated.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data=f"channel_images:{idx}")]]))

    elif data == "images_menu":
        images = config.get("prediction_images", {})
        kb = InlineKeyboardMarkup(
            [
                [btn(f"BIG Image: {'ON' if images.get('BIG', {}).get('enabled') else 'OFF'}", "image_toggle:BIG", "green" if images.get('BIG', {}).get('enabled') else "red"), btn("Upload BIG", "image_set:BIG", "eye", "primary")],
                [btn(f"SMALL Image: {'ON' if images.get('SMALL', {}).get('enabled') else 'OFF'}", "image_toggle:SMALL", "green" if images.get('SMALL', {}).get('enabled') else "red"), btn("Upload SMALL", "image_set:SMALL", "eye", "primary")],
                [btn("Preview BIG", "image_preview:BIG", "search"), btn("Preview SMALL", "image_preview:SMALL", "search")],
                [back_btn()],
            ]
        )
        await query.edit_message_text("Prediction Images\n\nUpload, replace, enable, disable, and preview separate BIG/SMALL images.", reply_markup=kb)

    elif data.startswith("image_set:"):
        size = data.split(":", 1)[1]
        context.user_data["awaiting"] = f"prediction_image:{size}"
        await query.edit_message_text(f"Send the new {size} prediction image now.")

    elif data.startswith("image_toggle:"):
        size = data.split(":", 1)[1]
        item = config.setdefault("prediction_images", {}).setdefault(size, {})
        item["enabled"] = not item.get("enabled", False)
        save_config()
        await query.edit_message_text(f"{size} image {'enabled' if item['enabled'] else 'disabled'}.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="images_menu")]]))

    elif data.startswith("image_preview:"):
        size = data.split(":", 1)[1]
        number = 7 if size == "BIG" else 2
        values = {
            "period": "PREVIEW", "number": number, "number_emoji": NUMBER_EMOJI[number],
            "size": size, "size_icon": SIZE_ICON[size], "color": analyze(number)[2],
            "color_icon": COLOR_ICON[analyze(number)[2]], "confidence": 90,
            "time": datetime.now().strftime("%I:%M:%S %p"), "bet_level": 0, "bet_amount": 1,
        }
        text = format_template("prediction", values)
        path = prediction_image(size)
        if path:
            with Path(path).open("rb") as image:
                await context.bot.send_photo(query.message.chat_id, image, caption=text, parse_mode=ParseMode.HTML)
        else:
            await context.bot.send_message(query.message.chat_id, f"{text}\n\n[No enabled {size} image; text fallback shown.]", parse_mode=ParseMode.HTML)
        await query.edit_message_text("Preview sent.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="images_menu")]]))

    elif data == "add_channel":
        context.user_data["awaiting"] = "add_channel"
        await query.edit_message_text(
            "Send channel username/ID/link to add.\n\n"
            "Public: @yourchannel\n"
            "Private: forward any post from the private channel here\n"
            "Invite: https://t.me/+xxxxx\n\n"
            "Userbot must be member/admin in that channel."
        )

    elif data == "replace_channels":
        context.user_data["awaiting"] = "replace_channels"
        await query.edit_message_text("Send all public channels/IDs one per line or comma separated.\nFor private channels, use Add Channel and forward a post.")

    elif data.startswith("remove_channel:"):
        channels = get_channels()
        idx = int(data.split(":", 1)[1])
        if 0 <= idx < len(channels):
            removed = channels.pop(idx)
            set_channels(channels)
            save_config()
            await query.edit_message_text(f"Removed {removed}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="channels_menu")]]))
        else:
            await query.edit_message_text("Channel not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="channels_menu")]]))

    elif data == "test_channels":
        ok, msg = await send_user_message("Channel sender test.", bot=context.bot)
        await query.edit_message_text(("OK: " if ok else "Failed: ") + msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="channels_menu")]]))

    elif data == "set_channel":
        context.user_data["awaiting"] = "replace_channels"
        await query.edit_message_text("Send target channel username or ID.\nExample: @yourchannel")

    elif data == "login_menu":
        context.user_data.pop("awaiting", None)
        status = await userbot_status()
        phone = config.get("phone") or "Not set"
        kb = InlineKeyboardMarkup(
            [
                [btn("Login / Change Phone", "login_phone", "link")],
                [btn("Resend OTP", "login_resend", "comet")],
                [btn("Add New Userbot", "login_new", "shield")],
                [btn("Logout Userbot", "login_logout_confirm", "stop")],
                [back_btn()],
            ]
        )
        text = (
            "Userbot Login\n\n"
            f"Status: {status}\n"
            f"Phone: {phone}\n\n"
            "Tap Login / Change Phone, then send your phone number.\n"
            "After that send OTP here. If 2FA is enabled, send password here."
        )
        await query.edit_message_text(text, reply_markup=kb)

    elif data == "login_new":
        await logout_userbot(delete_session=True)
        context.user_data["awaiting"] = "login_phone"
        await query.edit_message_text(
            "Old userbot removed.\n\nSend new Telegram phone number with country code.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="login_menu")]]),
        )

    elif data == "login_logout_confirm":
        kb = InlineKeyboardMarkup(
            [
                [btn("Yes, Logout", "login_logout", "stop", "danger")],
                [btn("Cancel", "login_menu", "no", "primary")],
            ]
        )
        await query.edit_message_text("Logout current userbot?", reply_markup=kb)

    elif data == "login_logout":
        await logout_userbot(delete_session=True)
        await query.edit_message_text(
            "Userbot logged out and session removed.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Login New", callback_data="login_phone")], [InlineKeyboardButton("Back", callback_data="home")]]),
        )

    elif data == "login_phone":
        context.user_data["awaiting"] = "login_phone"
        await query.edit_message_text(
            "Send Telegram phone number with country code.\nExample: 919876543210",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="login_menu")]]),
        )

    elif data == "login_resend":
        phone = config.get("phone")
        if not phone:
            context.user_data["awaiting"] = "login_phone"
            await query.edit_message_text("Phone not set. Send phone number first.")
        else:
            ok, msg = await send_login_code(phone)
            if ok and msg == "already_logged_in":
                await query.edit_message_text("Userbot already logged in.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="login_menu")]]))
            elif ok:
                context.user_data["awaiting"] = "login_code"
                await query.edit_message_text("OTP sent again. Send OTP here.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="login_menu")]]))
            else:
                await query.edit_message_text(f"Failed: {msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="login_menu")]]))

    elif data == "content_menu":
        kb = InlineKeyboardMarkup(
            [
                [btn("Message Templates", "templates", "chat"), btn("Prediction Images", "images_menu", "eye")],
                [btn("Start / Win / Loss Stickers", "stickers", "party")],
                [btn("Message Delivery Settings", "settings_menu", "mega")],
                [back_btn()],
            ]
        )
        await query.edit_message_text("Prediction Content\n\nControl exactly how predictions, results, images, and stickers appear.", reply_markup=kb)

    elif data == "reports_menu":
        users = config.get("users", {})
        active_users = sum(1 for user_id in users if user_has_access(user_id))
        running_users = sum(1 for profile in users.values() if profile.get("prediction_active"))
        stats = config.get("stats", {})
        kb = InlineKeyboardMarkup(
            [
                [btn("Global Statistics", "stats", "chart"), btn("Prediction History", "history", "search")],
                [btn("Live System Health", "health_check", "shield", "success")],
                [back_btn()],
            ]
        )
        await query.edit_message_text(
            f"Reports & Statistics\n\nUsers: {len(users)} | Active: {active_users} | Running: {running_users}\n"
            f"Predictions: {stats.get('total', 0)} | Wins: {stats.get('wins', 0)} | Losses: {stats.get('losses', 0)}",
            reply_markup=kb,
        )

    elif data == "system_menu":
        kb = InlineKeyboardMarkup(
            [
                [btn("Main Channels", "channels_menu", "globe"), btn("Userbot Login", "login_menu", "link")],
                [btn("Default Sender Routing", "bot_menu", "shield")],
                [btn("Default Interval", "set_interval", "candle"), btn("Trial Duration", "set_trial_days", "free")],
                [btn("Restart Automation Jobs", "restart_jobs", "comet", "success")],
                [btn("Set API Endpoint / Mirror", "set_api_url", "link", "primary")],
                [btn("Stop All User Predictions", "stop_all_users", "stop", "danger")],
                [btn("Repair Prediction State", "repair_state", "warn", "success")],
                [btn("Download Full Backup", "backup_download", "shop", "success"), btn("Restore Backup", "backup_restore", "comet")],
                [btn("Emergency Stop Everything", "emergency_stop", "stop", "danger")],
                [back_btn()],
            ]
        )
        await query.edit_message_text(
            f"System Controls\n\nDefault trial: {config.get('trial_days', 2)} days\n"
            f"Default sender: {config.get('sender_mode', 'userbot')}\n"
            f"Interval: {config.get('auto_interval', 60)} seconds",
            reply_markup=kb,
        )

    elif data == "set_trial_days":
        context.user_data["awaiting"] = "trial_days"
        await query.edit_message_text("Send default free-trial duration in days.\nThis applies to newly registered users.", reply_markup=InlineKeyboardMarkup([[back_btn("system_menu")]]))

    elif data == "set_api_url":
        context.user_data["awaiting"] = "api_url"
        await query.edit_message_text(
            "Send the allowed API endpoint or mirror URL.\nUse this when the provider blocks Railway's datacenter IP.",
            reply_markup=InlineKeyboardMarkup([[back_btn("system_menu")]]),
        )

    elif data == "backup_download":
        await query.edit_message_text("Preparing encrypted transport package...")
        backup_path = create_full_backup()
        try:
            with backup_path.open("rb") as document:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=document,
                    filename=backup_path.name,
                    caption="Admin-only full bot backup. Keep this file private.",
                )
        finally:
            backup_path.unlink(missing_ok=True)
        await query.edit_message_text("Full backup sent privately to this admin chat.", reply_markup=InlineKeyboardMarkup([[back_btn("system_menu")]]))

    elif data == "backup_restore":
        context.user_data["awaiting"] = "backup_restore"
        await query.edit_message_text(
            "Send the ZIP backup file now.\n\nThis replaces runtime data, stickers, images, and session files. Credentials remain from bot.py.",
            reply_markup=InlineKeyboardMarkup([[back_btn("system_menu")]]),
        )

    elif data == "stop_all_users":
        stopped = 0
        for user_id, profile in config.get("users", {}).items():
            if profile.get("prediction_active"):
                profile["prediction_active"] = False
                stopped += 1
            await remove_user_prediction_jobs(context, user_id)
        save_config()
        await query.edit_message_text(f"Stopped predictions for {stopped} user(s).", reply_markup=InlineKeyboardMarkup([[back_btn("system_menu")]]))

    elif data == "restart_jobs":
        await ensure_auto_job(context, query.message.chat_id)
        await ensure_session_monitor(context, query.message.chat_id)
        for user_id, profile in config.get("users", {}).items():
            await remove_user_prediction_jobs(context, user_id)
            if profile.get("prediction_active") and user_has_access(user_id):
                schedule_user_prediction(context, user_id, int(user_id), delay=3)
        await query.edit_message_text("Automation jobs restarted and synchronized.", reply_markup=InlineKeyboardMarkup([[back_btn("system_menu")]]))

    elif data == "emergency_stop":
        config["prediction_active"] = False
        config["auto_mode"] = False
        config["current_prediction"] = None
        config["pending_predictions"] = []
        await remove_auto_jobs(context)
        await remove_session_jobs(context)
        stopped = 0
        for user_id, profile in config.get("users", {}).items():
            if profile.get("prediction_active"):
                stopped += 1
            profile["prediction_active"] = False
            await remove_user_prediction_jobs(context, user_id)
        save_config()
        await query.edit_message_text(f"Emergency stop complete. Stopped global engine and {stopped} user(s).", reply_markup=InlineKeyboardMarkup([[back_btn("system_menu")]]))

    elif data == "repair_state":
        api = await asyncio.to_thread(fetch_api)
        if not api["ok"]:
            await query.edit_message_text("Repair could not run because the prediction API is offline. See Live System Health.", reply_markup=InlineKeyboardMarkup([[back_btn("system_menu")]]))
            return
        changed = recover_stale_global_state(api)
        for user_id, profile in config.get("users", {}).items():
            current = profile.get("current_prediction")
            if current and not current.get("verified") and prediction_is_stale(api, current.get("period")):
                profile["current_prediction"] = None
                changed = True
        save_config()
        await ensure_auto_job(context, query.message.chat_id)
        await query.edit_message_text(
            "Prediction state repaired." if changed else "Prediction state is already healthy.",
            reply_markup=InlineKeyboardMarkup([[back_btn("system_menu")]]),
        )

    elif data == "health_check":
        api = await asyncio.to_thread(fetch_api)
        users = config.get("users", {})
        running = sum(1 for profile in users.values() if profile.get("prediction_active"))
        auto_jobs = len(context.job_queue.get_jobs_by_name("auto_prediction"))
        stale = False
        if api["ok"]:
            stale = any(prediction_is_stale(api, item.get("period")) for item in config.get("pending_predictions", []) if item)
        await query.edit_message_text(
            "Live System Health\n\n"
            f"API: {'ONLINE' if api['ok'] else 'ERROR'}\n"
            f"Latest period: {api.get('period', 'Unknown')}\n"
            f"Last success: {api_status.get('last_success') or 'None'}\n"
            f"Private API error: {(api_status.get('last_error') or 'None')[:350]}\n"
            f"Global engine: {'RUNNING' if config.get('prediction_active') else 'STOPPED'}\n"
            f"Automation jobs: {auto_jobs}\n"
            f"Running users: {running}\n"
            f"Pending queue: {len(config.get('pending_predictions', []))}\n"
            f"Stale queue detected: {'YES' if stale else 'NO'}",
            reply_markup=InlineKeyboardMarkup([[btn("Repair State", "repair_state", "warn", "success"), back_btn("reports_menu")]]),
        )

    elif data == "users_menu":
        rows = []
        lines = ["Users / Subscriptions\n"]
        for user_id, profile in list(config.get("users", {}).items())[:10]:
            lines.append(f"{user_id}: {'RUNNING' if profile.get('prediction_active') else 'STOPPED'} | {profile.get('subscription_until', 'Unknown')}")
            rows.append(
                [
                    InlineKeyboardButton(f"Extend {user_id} +7d", callback_data=f"extend_user:{user_id}"),
                    InlineKeyboardButton("Expire", callback_data=f"expire_user:{user_id}"),
                    btn("Premium", f"premium_user:{user_id}", "crystal"),
                ]
            )
            if profile.get("prediction_active"):
                rows.append([btn(f"Stop Predictions for {user_id}", f"stop_user:{user_id}", "stop", "danger")])
        rows.append([InlineKeyboardButton("Back", callback_data="home")])
        lines.append("\nNew users automatically receive a 2-day trial. Use /grant <user_id> <days> for a custom extension.")
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("extend_user:"):
        user_id = data.split(":", 1)[1]
        profile = get_user_profile(user_id)
        try:
            current = datetime.fromisoformat(profile.get("subscription_until", ""))
        except ValueError:
            current = datetime.now()
        profile["subscription_until"] = (max(current, datetime.now()) + timedelta(days=7)).isoformat(timespec="seconds")
        save_config()
        await query.edit_message_text(f"Extended {user_id} by 7 days.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="users_menu")]]))

    elif data.startswith("expire_user:"):
        user_id = data.split(":", 1)[1]
        profile = get_user_profile(user_id)
        profile["subscription_until"] = (datetime.now() - timedelta(seconds=1)).isoformat(timespec="seconds")
        save_config()
        await query.edit_message_text(f"Expired subscription for {user_id}.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="users_menu")]]))

    elif data.startswith("premium_user:"):
        user_id = data.split(":", 1)[1]
        profile = get_user_profile(user_id)
        profile["premium_access"] = not profile.get("premium_access", False)
        save_config()
        await query.edit_message_text(
            f"Premium {'enabled' if profile['premium_access'] else 'disabled'} for {user_id}.",
            reply_markup=InlineKeyboardMarkup([[btn("Back to Users", "users_menu", "shield")]]),
        )

    elif data.startswith("stop_user:"):
        user_id = data.split(":", 1)[1]
        profile = get_user_profile(user_id)
        profile["prediction_active"] = False
        await remove_user_prediction_jobs(context, user_id)
        save_config()
        await query.edit_message_text(f"Stopped predictions for {user_id}.", reply_markup=InlineKeyboardMarkup([[btn("Back to Users", "users_menu", "shield")]]))

    elif data == "stickers":
        kb = InlineKeyboardMarkup(
            [
                [btn("Set Start", "sticker_start", "fire"), btn("Set End", "sticker_end", "stop")],
                [btn("Set Win", "sticker_win", "check"), btn("Set Loss", "sticker_loss", "cross")],
                [btn("Test Stickers", "test_stickers", "zap")],
                [back_btn()],
            ]
        )
        await query.edit_message_text("Choose sticker type. Then send sticker to this bot.", reply_markup=kb)

    elif data.startswith("sticker_"):
        kind = data.split("_", 1)[1]
        context.user_data["awaiting"] = f"sticker:{kind}"
        await query.edit_message_text(f"Send {kind.upper()} sticker now.")

    elif data == "test_stickers":
        for kind in ["start", "win", "loss", "end"]:
            await send_sticker(kind, context.bot)
            await asyncio.sleep(0.6)
        await query.edit_message_text("Sticker test done.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="stickers")]]))

    elif data == "templates":
        kb = InlineKeyboardMarkup(
            [
                [btn("Prediction Message", "tpl_prediction", "mega")],
                [btn("Win Message", "tpl_win", "check"), btn("Loss Message", "tpl_loss", "cross")],
                [btn("Premium Emoji Help", "premium_help", "crystal")],
                [back_btn()],
            ]
        )
        await query.edit_message_text("Choose message template to edit.", reply_markup=kb)

    elif data == "premium_help":
        await query.edit_message_text(
            "Premium emoji support\n\n"
            "Emoji ID dalne ki zarurat nahi.\n\n"
            "Messages panel me Prediction/Win/Loss choose karo, phir normal template message bhejo. "
            "Us message me premium emoji directly use karo. Bot us premium emoji ko internally save kar lega.\n\n"
            "Same template channel me userbot se premium emoji ke saath send hogi.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="templates")]]),
        )

    elif data.startswith("tpl_"):
        name = data.split("_", 1)[1]
        context.user_data["awaiting"] = f"template:{name}"
        await query.edit_message_text(
            f"Send new {name} template.\n\n"
            "Variables:\n"
            "Prediction: {period} {number} {number_emoji} {size} {size_icon} {color} {color_icon} {confidence} {time} {bet_level} {bet_amount}\n"
            "Result: {period} {pred_number} {pred_size} {pred_color} {actual_number} {actual_size} {actual_color} {matched}\n\n"
            f"Current:\n{config['templates'][name]}"
        )

    elif data == "history":
        lines = ["History\n"]
        for item in config.get("history", [])[:15]:
            icon = "✅" if item.get("result") == "WIN" else "❌"
            lines.append(f"{icon} {item.get('period')} P:{item.get('predicted', {}).get('number')} A:{item.get('actual', {}).get('number')}")
        await query.edit_message_text("\n".join(lines) or "No history", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="home")]]))

    elif data == "stats":
        stats = config["stats"]
        await query.edit_message_text(
            f"Stats\n\nTotal: {stats['total']}\nWins: {stats['wins']}\nLosses: {stats['losses']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="home")]]),
        )

    elif data == "set_interval":
        context.user_data["awaiting"] = "interval"
        await query.edit_message_text(f"Send auto interval in seconds.\nCurrent: {config.get('auto_interval', 60)}")

    elif data == "schedule_menu":
        sessions = normalized_sessions()
        current_key = current_session_key()
        kb = InlineKeyboardMarkup(
            [
                [btn("24x7 Non-stop", "preset_full_day", "fire", "primary")],
                [btn("Morning 8 AM", "preset_morning", "candle"), btn("Evening 6 PM", "preset_evening", "moon")],
                [btn("4 Sessions / Day", "preset_four_sessions", "comet")],
                [btn("Custom Times", "set_sessions", "candle"), btn("Target Wins", "set_stop_wins", "hundred")],
                [btn(f"Automation: {'ON' if config.get('auto_mode') else 'OFF'}", "toggle_auto", "zap", "success" if config.get("auto_mode") else "danger")],
                [back_btn()],
            ]
        )
        await query.edit_message_text(
            f"Easy Schedule\n\nMode: {config.get('mode')}\nAuto: {'ON' if config.get('auto_mode') else 'OFF'}\n"
            f"Current session: {current_key or 'None'}\nStart times:\n{chr(10).join(sessions[:4]) if sessions else 'None'}\n\n"
            f"Target wins: {config.get('stop_after_wins') or 'OFF'}\n"
            f"Session wins: {config.get('session_wins', 0)}",
            reply_markup=kb,
        )

    elif data == "schedule_presets":
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Start 8 AM", callback_data="preset_morning"), InlineKeyboardButton("Start 6 PM", callback_data="preset_evening")],
                [InlineKeyboardButton("4 Start Times", callback_data="preset_four_sessions"), InlineKeyboardButton("Full Day", callback_data="preset_full_day")],
                [InlineKeyboardButton("Back", callback_data="schedule_menu")],
            ]
        )
        await query.edit_message_text("Choose a schedule preset.", reply_markup=kb)

    elif data.startswith("preset_"):
        preset = data.split("_", 1)[1]
        sessions = config.get("session_presets", {}).get(preset, [])
        config["sessions"] = sessions[:4]
        config["mode"] = "24x7" if preset == "full_day" else "scheduled"
        config["completed_session_keys"] = []
        save_config()
        await ensure_session_monitor(context, query.message.chat_id)
        await query.edit_message_text(
            f"Preset applied.\n\nSessions:\n{chr(10).join(config['sessions']) if config['sessions'] else '24x7'}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="schedule_menu")]]),
        )

    elif data == "mode_24x7":
        config["mode"] = "24x7"
        config["session_started_by_schedule"] = False
        config["active_session_key"] = ""
        save_config()
        await remove_session_jobs(context)
        await ensure_auto_job(context, query.message.chat_id)
        await query.edit_message_text("Mode set to 24x7.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="schedule_menu")]]))

    elif data == "mode_scheduled":
        config["mode"] = "scheduled"
        config["prediction_active"] = False
        config["session_started_by_schedule"] = False
        config["active_session_key"] = ""
        save_config()
        await remove_auto_jobs(context)
        await ensure_session_monitor(context, query.message.chat_id)
        await query.edit_message_text("Mode set to scheduled.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="schedule_menu")]]))

    elif data == "set_sessions":
        context.user_data["awaiting"] = "sessions"
        await query.edit_message_text(
            "Send session start times, one per line. Max 4.\n"
            "Each session starts at that time and stops after Target Wins.\n\n"
            "Easy examples:\n"
            "08:00\n"
            "14:00\n"
            "20:00\n\n"
            "Range format like 08:00-10:00 still works if you want fixed end time."
        )

    elif data == "set_stop_wins":
        context.user_data["awaiting"] = "stop_wins"
        await query.edit_message_text("Send target wins for each session.\nExample: 5\nSend 0 to disable.")

    elif data == "settings_menu":
        kb = InlineKeyboardMarkup(
            [
                [btn(f"Prediction Messages: {'ON' if config.get('send_prediction_message', True) else 'OFF'}", "toggle_msg_prediction", "mega")],
                [btn(f"Win Messages: {'ON' if config.get('send_win_message', True) else 'OFF'}", "toggle_msg_win", "check", "success")],
                [btn(f"Loss Messages: {'ON' if config.get('send_loss_message', False) else 'OFF'}", "toggle_msg_loss", "cross", "danger")],
                [btn("Martingale Settings", "martingale_menu", "chart", "primary")],
                [back_btn()],
            ]
        )
        await query.edit_message_text("Settings", reply_markup=kb)

    elif data in ["toggle_msg_prediction", "toggle_msg_win", "toggle_msg_loss"]:
        key = {
            "toggle_msg_prediction": "send_prediction_message",
            "toggle_msg_win": "send_win_message",
            "toggle_msg_loss": "send_loss_message",
        }[data]
        config[key] = not config.get(key, key != "send_loss_message")
        save_config()
        await query.edit_message_text("Updated.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="settings_menu")]]))

    elif data == "martingale_menu":
        mg = config.get("martingale", {})
        kb = InlineKeyboardMarkup(
            [
                [btn(f"Enabled: {'ON' if mg.get('enabled', True) else 'OFF'}", "toggle_mg", "zap")],
                [btn("Base Bet", "set_mg_base", "money"), btn("Multiplier", "set_mg_multiplier", "chart")],
                [btn("Max Level", "set_mg_max", "hundred")],
                [back_btn("settings_menu")],
            ]
        )
        await query.edit_message_text(
            f"Martingale\n\nLevel: {mg.get('level', 0)}\nBase: {mg.get('base_bet', 1)}\nMultiplier: {mg.get('multiplier', 2)}\nMax: {mg.get('max_level', 4)}",
            reply_markup=kb,
        )

    elif data == "toggle_mg":
        config["martingale"]["enabled"] = not config.get("martingale", {}).get("enabled", True)
        save_config()
        await query.edit_message_text("Martingale updated.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="martingale_menu")]]))

    elif data in ["set_mg_base", "set_mg_multiplier", "set_mg_max"]:
        context.user_data["awaiting"] = data
        label = {"set_mg_base": "base bet", "set_mg_multiplier": "multiplier", "set_mg_max": "max level"}[data]
        await query.edit_message_text(f"Send martingale {label}.")

    elif data == "home":
        await start(update, context)


@admin_only
async def forwarded_channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    awaiting = context.user_data.get("awaiting")
    if awaiting not in ["channel", "add_channel"]:
        return

    channel_ref, title = extract_forwarded_channel_ref(update.message)
    if not channel_ref:
        await update.message.reply_text(
            "Private channel detect nahi hua. Make sure channel post forward kiya ho. Agar forwarding hidden hai, userbot ko channel me add karke private invite link bhejo.",
            reply_markup=main_keyboard(),
        )
        return

    channels = get_channels()
    if channel_ref not in channels:
        channels.append(channel_ref)
    set_channels(channels)
    context.user_data.pop("awaiting", None)
    save_config()

    label = f"{title} ({channel_ref})" if title else channel_ref
    ok, msg = await send_user_message("Channel connected.", bot=context.bot)
    await update.message.reply_text(
        f"Private channel added: {label}" if ok else f"Private channel added, but test failed: {msg}",
        reply_markup=main_keyboard(),
    )


async def user_reply_menu_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action):
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    settings = effective_user_settings(user_id)

    if action == "connect":
        if not user_has_access(user_id):
            await update.message.reply_text("Your trial/subscription has expired.", reply_markup=user_keyboard())
            return
        context.user_data["awaiting"] = "user_channel"
        await update.message.reply_text(
            f"{pe('link')} <b>CONNECT MY CHANNEL</b>\n\n"
            "1. Add this bot as an admin in your channel.\n"
            "2. Send the public <code>@channel</code> username or numeric channel ID here.\n\n"
            f"{pe('shield')} Your channel remains private and separate.",
            parse_mode=ParseMode.HTML,
            reply_markup=user_keyboard(),
        )
    elif action == "channels":
        channel = profile.get("channels", [])
        keyboard = InlineKeyboardMarkup(
            [
                [btn("Connect / Replace", "user_connect", "link"), btn(f"{'Stop' if profile.get('prediction_active') else 'Start'} Predictions", "user_toggle_predictions", "stop" if profile.get("prediction_active") else "zap")],
                [btn(f"Mode: {settings.get('mode', '24x7')}", "user_toggle_schedule_mode", "candle")],
                [btn("Custom Schedule", "user_custom_schedule", "comet"), btn("Message Template", "user_custom_template", "chat")],
                [btn("Reset My Settings", "user_reset", "no")],
            ]
        )
        await update.message.reply_text(
            f"{pe('globe')} <b>MY CHANNELS</b>\n\n"
            f"<blockquote>Connected: <b>{len(channel)}</b>\n"
            f"Channel: <b>{escape(channel[0]) if channel else 'Not connected'}</b>\n"
            f"Mode: <b>{escape(settings.get('mode', '24x7'))}</b></blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )
    elif action == "plans":
        await update.message.reply_text(
            f"{pe('money')} <b>SUBSCRIPTION PLANS</b>\n\n"
            f"<blockquote>{pe('star')} <b>Starter — Rs.599/month</b>\n1 Channel\n\n"
            f"{pe('zap')} <b>Pro — Rs.999/month</b>\n2 Channels · Custom schedules\n\n"
            f"{pe('crystal')} <b>Premium — Rs.1499/month</b>\n4 Channels · All features</blockquote>\n"
            f"{pe('chat')} Contact: <b>@itsukiarai</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=user_keyboard(),
        )
    elif action == "status":
        await update.message.reply_text(
            f"{pe('chart')} <b>ACCOUNT STATUS</b>\n\n"
            f"<blockquote>Access: <b>{'ACTIVE' if user_has_access(user_id) else 'EXPIRED'}</b>\n"
            f"Plan: <b>{escape(profile.get('plan', 'free_trial').replace('_', ' ').title())}</b>\n"
            f"Premium: <b>{'UNLOCKED' if user_is_premium(user_id) else 'LOCKED'}</b>\n"
            f"Channels: <b>{len(profile.get('channels', []))}</b>\n"
            f"Valid until: <code>{escape(profile.get('subscription_until', 'Unknown'))}</code></blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=user_keyboard(),
        )
    elif action == "help":
        await update.message.reply_text(
            f"{pe('q')} <b>HELP CENTER</b>\n\n"
            "<b>Connect:</b> Add bot as channel admin, then send channel username.\n"
            "<b>My Channels:</b> Manage predictions, schedules, and messages.\n"
            "<b>Support:</b> @itsukiarai",
            parse_mode=ParseMode.HTML,
            reply_markup=user_keyboard(),
        )
    elif action == "about":
        await update.message.reply_text(
            f"{pe('crystal')} <b>ABOUT THIS BOT</b>\n\n"
            "<b>Multi-Platform Prediction Bot</b> · Version 1.1\n\n"
            "Wingo 1 Min Auto Predictions\nMartingale Strategy\nMulti-Session Management\n"
            "Auto Win/Loss Tracking\nDaily & Session Reports\n\n"
            "<b>Platforms:</b> OKWin · Sikkim Game · IN999 · 91Club · Raja Games · Jalwa\n\n"
            f"{pe('chat')} Admin: <b>@itsukiarai</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=user_keyboard(),
        )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    awaiting = context.user_data.get("awaiting")
    text = update.message.text.strip()

    if not is_admin(update.effective_user.id):
        action = USER_MENU_ACTIONS.get(text)
        if action:
            context.user_data.pop("awaiting", None)
            await user_reply_menu_action(update, context, action)
            return
        if awaiting == "user_channel":
            if not user_has_access(update.effective_user.id):
                await update.message.reply_text("Your trial/subscription has expired.")
                return
            value = text.strip()
            if not (value.startswith("@") or re.fullmatch(r"-?\d+", value)):
                await update.message.reply_text("Send a public @channel username or numeric channel ID.")
                return
            profile = get_user_profile(update.effective_user.id)
            profile["channels"] = [value]
            profile.setdefault("overrides", {})["channels"] = [value]
            context.user_data.pop("awaiting", None)
            save_config()
            await update.message.reply_text("Your channel was saved.", reply_markup=user_keyboard())
            return
        if awaiting == "user_schedule":
            sessions = [part.strip() for part in re.split(r"[\n,]+", text) if part.strip()]
            valid = [session.replace(" ", "") for session in sessions[:6] if re.match(r"^\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}$", session)]
            if not valid:
                await update.message.reply_text("No valid sessions found. Use format: 10:00-11:00")
                return
            profile = get_user_profile(update.effective_user.id)
            profile.setdefault("overrides", {})["sessions"] = valid
            profile["overrides"]["mode"] = "scheduled"
            context.user_data.pop("awaiting", None)
            save_config()
            await update.message.reply_text(f"Saved {len(valid)} private session(s).", reply_markup=user_keyboard())
            return
        if awaiting == "user_template":
            profile = get_user_profile(update.effective_user.id)
            profile.setdefault("overrides", {})["prediction_template"] = template_to_html_from_message(update.message)
            context.user_data.pop("awaiting", None)
            save_config()
            await update.message.reply_text("Your private prediction template was saved.", reply_markup=user_keyboard())
            return
        await start(update, context)
        return

    if awaiting == "login_phone":
        phone = re.sub(r"[^\d+]", "", text)
        if len(phone.lstrip("+")) < 8:
            await update.message.reply_text("Phone number invalid lag raha hai. Country code ke saath bhejo.")
            return

        await update.message.reply_text("Sending OTP...")
        ok, msg = await send_login_code(phone)
        if ok and msg == "already_logged_in":
            context.user_data.pop("awaiting", None)
            await update.message.reply_text("Userbot already logged in.", reply_markup=main_keyboard())
        elif ok:
            context.user_data["awaiting"] = "login_code"
            await update.message.reply_text("OTP sent. Ab OTP yahin bhejo.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="login_menu")]]))
        else:
            await update.message.reply_text(f"Login start failed: {msg}", reply_markup=main_keyboard())
        return

    if awaiting == "login_code":
        code = re.sub(r"\D", "", text)
        if len(code) < 3:
            await update.message.reply_text("OTP invalid lag raha hai. Sirf OTP digits bhejo.")
            return

        ok, msg = await sign_in_with_code(code)
        if ok:
            context.user_data.pop("awaiting", None)
            await ensure_session_monitor(context, update.effective_chat.id)
            await update.message.reply_text("Userbot login done. Ab channel me prediction user account se jayegi.", reply_markup=main_keyboard())
        elif msg == "password_needed":
            context.user_data["awaiting"] = "login_password"
            await update.message.reply_text("2FA enabled hai. Telegram password bhejo.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="login_menu")]]))
        elif msg == "invalid_code":
            await update.message.reply_text("OTP wrong hai. Dobara OTP bhejo ya User Login > Resend OTP dabao.")
        else:
            await update.message.reply_text(f"Login failed: {msg}", reply_markup=main_keyboard())
        return

    if awaiting == "login_password":
        ok, msg = await sign_in_with_password(text)
        if ok:
            context.user_data.pop("awaiting", None)
            await ensure_session_monitor(context, update.effective_chat.id)
            await update.message.reply_text("Userbot login done. Ab channel me prediction user account se jayegi.", reply_markup=main_keyboard())
        else:
            await update.message.reply_text(f"Password/login failed: {msg}")
        return

    if awaiting in ["channel", "add_channel"]:
        ok_ref, channel_ref = await normalize_channel_ref(text)
        if not ok_ref:
            await update.message.reply_text(channel_ref, reply_markup=main_keyboard())
            return
        channels = get_channels()
        if channel_ref not in channels:
            channels.append(channel_ref)
        set_channels(channels)
        context.user_data.pop("awaiting", None)
        save_config()
        ok, msg = await send_user_message("✅ Channel connected.", bot=context.bot)
        await update.message.reply_text("Channel added." if ok else f"Channel added, but test failed: {msg}", reply_markup=main_keyboard())
        return

    if awaiting == "replace_channels":
        channels = []
        for part in [part.strip() for part in re.split(r"[\n,]+", text) if part.strip()]:
            ok_ref, channel_ref = await normalize_channel_ref(part)
            if ok_ref and channel_ref not in channels:
                channels.append(channel_ref)
        set_channels(channels)
        context.user_data.pop("awaiting", None)
        save_config()
        await update.message.reply_text(f"Saved {len(get_channels())} channel(s).", reply_markup=main_keyboard())
        return

    if awaiting == "interval":
        try:
            interval = int(text)
            if interval < 45:
                await update.message.reply_text("Minimum interval is 45 seconds.")
                return
            config["auto_interval"] = interval
            context.user_data.pop("awaiting", None)
            save_config()
            await ensure_auto_job(context, update.effective_chat.id)
            await update.message.reply_text(f"Auto interval set to {interval} seconds.", reply_markup=main_keyboard())
        except ValueError:
            await update.message.reply_text("Send interval as a number.")
        return

    if awaiting == "trial_days":
        try:
            days = max(0, min(365, int(text)))
            config["trial_days"] = days
            context.user_data.pop("awaiting", None)
            save_config()
            await update.message.reply_text(f"Default free trial set to {days} day(s).", reply_markup=main_keyboard())
        except ValueError:
            await update.message.reply_text("Send trial duration as a number.")
        return

    if awaiting == "api_url":
        url = text.strip()
        if not re.match(r"^https://[^ ]+$", url):
            await update.message.reply_text("Send a valid HTTPS API URL.")
            return
        config["api_urls"] = [url]
        api_cache["data"] = None
        context.user_data.pop("awaiting", None)
        save_config()
        api = await asyncio.to_thread(fetch_api)
        await update.message.reply_text(
            "API endpoint saved and verified." if api["ok"] else "API endpoint saved, but Railway is still being blocked. Check Live System Health.",
            reply_markup=main_keyboard(),
        )
        return

    if awaiting == "sessions":
        sessions = [part.strip() for part in re.split(r"[\n,]+", text) if part.strip()]
        valid = []
        for session in sessions[:4]:
            if re.match(r"^\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}$", session):
                valid.append(session.replace(" ", ""))
        config["sessions"] = valid
        config["mode"] = "scheduled" if valid else "24x7"
        config["completed_session_keys"] = []
        context.user_data.pop("awaiting", None)
        save_config()
        await ensure_session_monitor(context, update.effective_chat.id)
        await update.message.reply_text(f"Saved {len(valid)} session(s).", reply_markup=main_keyboard())
        return

    if awaiting == "stop_wins":
        try:
            config["stop_after_wins"] = max(0, int(text))
            config["session_wins"] = 0
            config["completed_session_keys"] = []
            context.user_data.pop("awaiting", None)
            save_config()
            await update.message.reply_text(f"Stop-after-wins set to {config['stop_after_wins'] or 'OFF'}.", reply_markup=main_keyboard())
        except ValueError:
            await update.message.reply_text("Send a number.")
        return

    if awaiting in ["set_mg_base", "set_mg_multiplier", "set_mg_max"]:
        try:
            value = float(text) if awaiting in ["set_mg_base", "set_mg_multiplier"] else int(text)
            if awaiting == "set_mg_base":
                config["martingale"]["base_bet"] = max(0, value)
            elif awaiting == "set_mg_multiplier":
                config["martingale"]["multiplier"] = max(1, value)
            else:
                config["martingale"]["max_level"] = max(0, int(value))
            context.user_data.pop("awaiting", None)
            save_config()
            await update.message.reply_text("Martingale updated.", reply_markup=main_keyboard())
        except ValueError:
            await update.message.reply_text("Send a valid number.")
        return

    if awaiting and awaiting.startswith("template:"):
        name = awaiting.split(":", 1)[1]
        config["templates"][name] = template_to_html_from_message(update.message)
        context.user_data.pop("awaiting", None)
        save_config()
        await update.message.reply_text(f"{name} template updated.", reply_markup=main_keyboard())
        return

    if awaiting and awaiting.startswith("sticker:"):
        await update.message.reply_text("Send a sticker, not text.")
        return

    await update.message.reply_text(await dashboard_text(), reply_markup=main_keyboard())


@admin_only
async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    awaiting = context.user_data.get("awaiting", "")
    if not awaiting.startswith("sticker:"):
        await update.message.reply_text(f"Sticker file_id:\n`{update.message.sticker.file_id}`", parse_mode=ParseMode.MARKDOWN)
        return

    kind = awaiting.split(":", 1)[1]
    STICKER_DIR.mkdir(exist_ok=True)
    sticker = update.message.sticker
    ext = "tgs" if sticker.is_animated else "webm" if sticker.is_video else "webp"
    path = STICKER_DIR / f"{kind}.{ext}"
    file = await context.bot.get_file(sticker.file_id)
    await file.download_to_drive(custom_path=path)

    config["stickers"][kind] = sticker.file_id
    config["sticker_files"][kind] = str(path)
    context.user_data.pop("awaiting", None)
    save_config()
    await update.message.reply_text(f"{kind.upper()} sticker saved. It will be sent as a real Telegram sticker by the main bot.", reply_markup=main_keyboard())


@admin_only
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    awaiting = context.user_data.get("awaiting", "")
    if not (awaiting.startswith("prediction_image:") or awaiting.startswith("channel_prediction_image:")):
        await update.message.reply_text("Open Prediction Images and choose Set BIG or Set SMALL first.")
        return

    IMAGE_DIR.mkdir(exist_ok=True)
    photo = update.message.photo[-1]
    if awaiting.startswith("channel_prediction_image:"):
        _, idx, size = awaiting.split(":")
        channels = get_channels()
        if not 0 <= int(idx) < len(channels):
            await update.message.reply_text("Channel no longer exists.")
            return
        channel = channels[int(idx)]
        safe_channel = re.sub(r"[^A-Za-z0-9_-]", "_", channel)
        path = IMAGE_DIR / f"{safe_channel}_{size.lower()}.jpg"
    else:
        size = awaiting.split(":", 1)[1]
        channel = None
        path = IMAGE_DIR / f"{size.lower()}.jpg"
    file = await context.bot.get_file(photo.file_id)
    await file.download_to_drive(custom_path=path)
    item = {
        "enabled": True,
        "path": str(path),
        "file_id": photo.file_id,
    }
    if channel is None:
        config.setdefault("prediction_images", {})[size] = item
    else:
        config.setdefault("channel_prediction_images", {}).setdefault(channel, {})[size] = item
    context.user_data.pop("awaiting", None)
    save_config()
    scope = "global" if channel is None else f"channel {channel}"
    await update.message.reply_text(f"{size} prediction image saved and enabled for {scope}.", reply_markup=main_keyboard())


@admin_only
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting") != "backup_restore":
        await update.message.reply_text("Documents are accepted only through System Controls > Restore Backup.")
        return
    document = update.message.document
    if not document.file_name or not document.file_name.lower().endswith(".zip"):
        await update.message.reply_text("Send a valid ZIP backup file.")
        return
    temp_path = Path(tempfile.gettempdir()) / f"restore_{update.effective_user.id}_{int(time.time())}.zip"
    file = await context.bot.get_file(document.file_id)
    await file.download_to_drive(custom_path=temp_path)
    try:
        restored = await asyncio.to_thread(restore_runtime_backup, temp_path)
        context.user_data.pop("awaiting", None)
        await update.message.reply_text(
            f"Backup restored successfully: {restored} runtime file(s).\nRestart the Railway service once to reload all restored data.",
            reply_markup=main_keyboard(),
        )
    except Exception as exc:
        print(f"Backup restore private error: {exc}")
        await update.message.reply_text("Backup restore failed. The file is invalid or unsafe.")
    finally:
        temp_path.unlink(missing_ok=True)


async def post_init(application: Application):
    api = await asyncio.to_thread(fetch_api)
    if api["ok"] and recover_stale_global_state(api):
        print("Recovered stale global prediction state.")
    if api["ok"]:
        changed = False
        for profile in config.get("users", {}).values():
            current = profile.get("current_prediction")
            if current and not current.get("verified") and (
                prediction_is_stale(api, current.get("period")) or prediction_is_behind_latest(api, current.get("period"))
            ):
                profile["current_prediction"] = None
                changed = True
        if changed:
            save_config()
            print("Recovered stale user prediction state.")
    user_authorized = False
    client = await get_user_client(connect=True)
    if client:
        try:
            user_authorized = await client.is_user_authorized()
            print("Userbot:", "logged in" if user_authorized else "login needed")
        except Exception as exc:
            print(f"Userbot init error: {exc}")
    if user_authorized and config.get("auto_mode") and config.get("admin_ids"):
        if config.get("mode") == "scheduled":
            await ensure_session_monitor(application, config["admin_ids"][0])
        elif config.get("prediction_active"):
            schedule_auto_prediction(application, config["admin_ids"][0])
    for user_id, profile in config.get("users", {}).items():
        if profile.get("prediction_active") and user_has_access(user_id):
            schedule_user_prediction(application, user_id, int(user_id), delay=5)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, BadRequest) and "Message is not modified" in str(context.error):
        return
    print(f"Unhandled bot error: {context.error}")
    try:
        if isinstance(update, Update) and update.effective_chat:
            text = f"Something went wrong: {context.error}" if is_admin(update.effective_user.id if update.effective_user else 0) else "Something went wrong. Please try again shortly."
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
            )
    except Exception as exc:
        print(f"Error handler failed: {exc}")


def main():
    global config
    config = load_config()
    if not config.get("channels") and config.get("channel_id"):
        set_channels([config["channel_id"]])
    config["sessions"] = normalized_sessions()
    save_config()

    if not config.get("bot_token"):
        token = input("Enter admin bot token: ").strip()
        config["bot_token"] = token
        save_config()

    app = Application.builder().token(config["bot_token"]).post_init(post_init).build()
    app.add_handler(CommandHandler(["start", "admin"], start))
    app.add_handler(CommandHandler("setupuser", setup_user))
    app.add_handler(CommandHandler("loginuser", login_user))
    app.add_handler(CommandHandler("code", code_cmd))
    app.add_handler(CommandHandler("password", password_cmd))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("grant", grant_subscription))
    app.add_handler(CommandHandler("premium", grant_premium))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    app.add_handler(MessageHandler(filters.Sticker.ALL, sticker_handler))
    app.add_handler(MessageHandler(filters.FORWARDED, forwarded_channel_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)

    print("Prediction admin bot started")
    print(f"Config: {CONFIG_FILE}")
    print(f"Channel: {config.get('channel_id') or 'not set'}")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
