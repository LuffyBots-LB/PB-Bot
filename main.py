"""
Moon Leaks Video Sharing Bot
"""

import json
import os
import random
from typing import Dict, List, Any

from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

# Bot token
BOT_TOKEN = "8349861272:AAF0lU1JJRok2yfDcs9wnm-pXhNNjVNZL8k"

# Owner / Super Admin user id
OWNER_ID = 6847499628

# Channels list (force join)
REQUIRED_CHANNELS = [
    {
        "id": -1002699957030,
        "name": "𝙈.𝙊.𝙊.𝙉 𝙒𝙊𝙍𝙇𝘿 🔥",
        "link": "https://t.me/EscrowMoon",
    },
    {
        "id": -1002148399900,
        "name": "MiddleAppect",
        "link": "https://t.me/MiddleAppect",
    },
    {
        "id": -1002277863913,
        "name": "About LuffyBots 💀",
        "link": "https://t.me/AboutLuffyBots",
    },
    {
        "id": -1002588749986,
        "name": "Channel 4",
        "link": "https://t.me/+yZVVK3L_IGdjYzQ9",
    },
]

# /start / verification ke liye photo file_id
START_PHOTO_ID = (
    "AgACAgUAAxkBAANGaSF-MCIW2hCVrsrf2Aba8-x07PoAAkoNaxuFIwlVfZt7lOWQcKEBAAMCAAN5AAM2BA"
)

# Data file
DATA_FILE = "data.json"


# ---------------------------------------------------------------------------
# DATA HELPERS
# ---------------------------------------------------------------------------

def _empty_data() -> Dict[str, Any]:
    """Fresh data structure."""
    data: Dict[str, Any] = {f"room{i}": [] for i in range(1, 5)}
    data["users"] = {}      # { user_id(str): {"verified": bool} }
    data["last_sent"] = {}  # { "room1": last_file_id, ... }
    data["admins"] = []     # extra admins (string user_ids)
    return data


def load_data() -> Dict[str, Any]:
    """Load data from file or create default."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = _empty_data()
    else:
        data = _empty_data()

    # Ensure keys
    for i in range(1, 5):
        data.setdefault(f"room{i}", [])
    data.setdefault("users", {})
    data.setdefault("last_sent", {})
    data.setdefault("admins", [])
    return data


def save_data(data: Dict[str, Any]) -> None:
    """Save data to file."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def update_user_status(user_id: int, verified: bool) -> None:
    """Store/Update user verified flag."""
    data = load_data()
    users = data.setdefault("users", {})
    uid = str(user_id)
    record = users.get(uid, {"verified": False})

    if verified:
        record["verified"] = True
    else:
        # sirf new user ke liye false set karo
        if uid not in users:
            record["verified"] = False

    users[uid] = record
    save_data(data)


# ---------------------------------------------------------------------------
# OWNER / ADMIN UTILS
# ---------------------------------------------------------------------------

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def is_admin(user_id: int) -> bool:
    """Owner + stored admins."""
    if is_owner(user_id):
        return True
    data = load_data()
    admins = data.get("admins", [])
    return str(user_id) in admins


# ---------------------------------------------------------------------------
# MEMBERSHIP & JOIN INSTRUCTIONS
# ---------------------------------------------------------------------------

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Return True if user in all required channels."""
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(
                chat_id=channel["id"],
                user_id=user_id,
            )
            if getattr(member, "status", None) in {"left", "kicked"}:
                return False
        except Exception:
            return False
    return True


async def send_join_instructions_inline(update: Update) -> None:
    """
    User ne saare channels join nahi kiye:
    - Photo + caption
    - Neeche inline channel buttons + ✅ Verify
    """
    buttons = [
        [InlineKeyboardButton(text=channel["name"], url=channel["link"])]
        for channel in REQUIRED_CHANNELS
    ]
    buttons.append(
        [InlineKeyboardButton(text="✅ Verify", callback_data="verify")]
    )
    keyboard = InlineKeyboardMarkup(buttons)

    caption = (
        "<b>Must join all channels to get videos.</b>\n"
        "Neeche wale buttons se saare channels join karo, phir ✅ Verify dabao."
    )

    await update.effective_message.reply_photo(
        photo=START_PHOTO_ID,
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


# ---------------------------------------------------------------------------
# COMMANDS
# ---------------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start."""
    user_id = update.effective_user.id

    # membership check
    if not await check_membership(user_id, context):
        update_user_status(user_id, verified=False)
        await send_join_instructions_inline(update)
        return

    # verified user
    update_user_status(user_id, verified=True)

    # welcome photo
    await update.message.reply_photo(photo=START_PHOTO_ID)

    description = (
        "<b>Welcome to the Moon Leaks Bot 🌝</b>\n"
        "Neeche kisi bhi room ko select karo, random video milega."
    )
    keyboard = ReplyKeyboardMarkup(
        [["Room 1", "Room 2"], ["Room 3", "Room 4"]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

    await update.message.reply_text(
        description,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /upload <file_id> <room_number> (admin only)."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Only admins can use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /upload <file_id> <room_number>")
        return

    file_id = context.args[0]
    try:
        room_number = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Room number must be an integer between 1 and 4.")
        return

    if room_number not in {1, 2, 3, 4}:
        await update.message.reply_text("Room number must be between 1 and 4.")
        return

    data = load_data()
    key = f"room{room_number}"
    data.setdefault(key, [])
    data[key].append(file_id)
    save_data(data)

    await update.message.reply_text(
        f"Added file to Room {room_number}. Total videos in this room: {len(data[key])}"
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reset (admin only)."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Only admins can reset the bot.")
        return

    data = _empty_data()
    save_data(data)
    await update.message.reply_text("Bot has been reset. All rooms are now empty.")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats (admin only)."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Only admins can view stats.")
        return

    data = load_data()
    users = data.get("users", {})
    total = len(users)
    verified = sum(1 for rec in users.values() if rec.get("verified"))
    not_verified = total - verified

    text = (
        "<b>📊 Bot Stats</b>\n"
        f"👥 Total Users: <b>{total}</b>\n"
        f"✅ Verified Users: <b>{verified}</b>\n"
        f"⚠️ Not Verified Users: <b>{not_verified}</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def totalvids_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /totalvids – room-wise video count (admin only)."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Only admins can use this command.")
        return

    data = load_data()

    text = (
        "<b>📁 Total Videos in Rooms</b>\n\n"
        f"Room 1: <b>{len(data.get('room1', []))}</b>\n"
        f"Room 2: <b>{len(data.get('room2', []))}</b>\n"
        f"Room 3: <b>{len(data.get('room3', []))}</b>\n"
        f"Room 4: <b>{len(data.get('room4', []))}</b>"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a broadcast message to all users (admin only)."""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("Only admins can use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(context.args)

    data = load_data()
    users = data.get("users", {})

    sent = 0
    failed = 0

    for uid in users.keys():
        try:
            await context.bot.send_message(chat_id=int(uid), text=message)
            sent += 1
        except Exception:
            failed += 1
            continue

    await update.message.reply_text(
        f"📢 Broadcast Completed!\n\n"
        f"✔ Sent: {sent}\n"
        f"❌ Failed: {failed}"
    )


async def cmds_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all admin commands (admin only)."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Only admins can use this command.")
        return

    text = (
        "<b>🛠 Admin Commands</b>\n\n"
        "/upload &lt;file_id&gt; &lt;room&gt; - Add video to room 1-4\n"
        "/reset - Clear all rooms data\n"
        "/stats - Show users stats\n"
        "/totalvids - Show total videos per room\n"
        "/broadcast &lt;text&gt; - Send message to all users\n"
        "/addadmin - Add new admin (owner only)\n"
        "/removeadmin - Remove admin (owner only)\n"
        "/cmds - Show this admin commands list\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def addadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add admin (OWNER only). /addadmin <user_id> or reply to user."""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("Only the owner can manage admins.")
        return

    target_id = None

    # Option 1: /addadmin 123456789
    if context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("User id must be a number.")
            return
    # Option 2: reply to a user's message
    elif update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id

    if target_id is None:
        await update.message.reply_text(
            "Usage: /addadmin <user_id>\n"
            "Ya phir kisi user ke message pe reply karke /addadmin bhejo."
        )
        return

    if is_owner(target_id):
        await update.message.reply_text("Owner already has all permissions.")
        return

    data = load_data()
    admins = data.setdefault("admins", [])
    uid = str(target_id)

    if uid in admins:
        await update.message.reply_text("Ye user already admin hai.")
        return

    admins.append(uid)
    save_data(data)

    await update.message.reply_text(f"Added admin: <code>{uid}</code>", parse_mode=ParseMode.HTML)


async def removeadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove admin (OWNER only). /removeadmin <user_id> or reply."""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("Only the owner can manage admins.")
        return

    target_id = None

    if context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("User id must be a number.")
            return
    elif update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id

    if target_id is None:
        await update.message.reply_text(
            "Usage: /removeadmin <user_id>\n"
            "Ya phir kisi admin ke message pe reply karke /removeadmin bhejo."
        )
        return

    if is_owner(target_id):
        await update.message.reply_text("Owner ko remove nahi kar sakte.")
        return

    data = load_data()
    admins = data.setdefault("admins", [])
    uid = str(target_id)

    if uid not in admins:
        await update.message.reply_text("Ye user admin list me nahi hai.")
        return

    admins.remove(uid)
    save_data(data)

    await update.message.reply_text(f"Removed admin: <code>{uid}</code>", parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# ROOM SELECTION & MEDIA HANDLER
# ---------------------------------------------------------------------------

async def handle_room_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text buttons: Room 1/2/3/4."""
    message_text = (update.message.text or "").strip()
    valid_rooms = {
        "Room 1": "room1",
        "Room 2": "room2",
        "Room 3": "room3",
        "Room 4": "room4",
    }

    if message_text not in valid_rooms:
        return

    user_id = update.effective_user.id

    # Check membership again
    if not await check_membership(user_id, context):
        update_user_status(user_id, verified=False)
        await send_join_instructions_inline(update)
        return

    update_user_status(user_id, verified=True)

    data = load_data()
    room_key = valid_rooms[message_text]
    videos: List[str] = data.get(room_key, [])

    if not videos:
        await update.message.reply_text("No videos in this room yet. Please check back later.")
        return

    # avoid same video twice in a row
    last_sent = data.setdefault("last_sent", {})
    last_file = last_sent.get(room_key)

    if len(videos) == 1:
        file_id = videos[0]
    else:
        candidates = [v for v in videos if v != last_file] or videos
        file_id = random.choice(candidates)

    last_sent[room_key] = file_id
    save_data(data)

    try:
        await update.message.reply_video(file_id)
    except Exception:
        try:
            await update.message.reply_document(file_id)
        except Exception:
            await update.message.reply_text("Failed to send the video. File ID may be invalid.")


async def handle_media_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin sends media -> bot replies with file_id in mono font."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    message = update.message
    file_id = None

    if message.video:
        file_id = message.video.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id  # highest resolution

    if file_id:
        text = (
            "<b>File ID:</b>\n"
            f"<pre>{file_id}</pre>"
        )
        await message.reply_text(text, parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# VERIFY CALLBACK
# ---------------------------------------------------------------------------

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline ✅ Verify button callback."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if await check_membership(user_id, context):
        update_user_status(user_id, verified=True)

        description = (
            "<b>Verification successful ✅</b>\n"
            "Ab neeche se koi bhi room choose karo, random video milega."
        )
        keyboard = ReplyKeyboardMarkup(
            [["Room 1", "Room 2"], ["Room 3", "Room 4"]],
            resize_keyboard=True,
            one_time_keyboard=False,
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=description,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )
    else:
        update_user_status(user_id, verified=False)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="You must join all channels before accessing videos.",
        )
        await send_join_instructions_inline(update)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("totalvids", totalvids_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("cmds", cmds_command))
    application.add_handler(CommandHandler("addadmin", addadmin_command))
    application.add_handler(CommandHandler("removeadmin", removeadmin_command))

    # Media -> file_id for admins
    application.add_handler(
        MessageHandler(filters.PHOTO | filters.VIDEO, handle_media_id)
    )

    # Room selection (any text that is not a command)
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_room_selection)
    )

    # Verify callback
    application.add_handler(
        CallbackQueryHandler(verify_callback, pattern="^verify$")
    )

    application.run_polling()


if __name__ == "__main__":
    main()
