import logging
import uuid
import random
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

SELECTING_TIME, SELECTING_SCORE = 0, 1  # اصلاح: مراحل به صورت اعداد ثابت

game_rooms = {}

CATEGORIES = [
    {"subject": "اسم", "difficulty": 1}, {"subject": "فامیل", "difficulty": 1},
    {"subject": "گل و گیاه", "difficulty": 2}, {"subject": "شهر", "difficulty": 1},
    {"subject": "میوه", "difficulty": 1}, {"subject": "مارک", "difficulty": 2},
    {"subject": "اعضای بدن", "difficulty": 2}, {"subject": "شخصیت تاریخی", "difficulty": 3},
    {"subject": "شخصیت داستانی", "difficulty": 2}, {"subject": "غذا", "difficulty": 1},
    {"subject": "اشیاء", "difficulty": 1}, {"subject": "ابزار", "difficulty": 1},
    {"subject": "مکان عمومی", "difficulty": 2}, {"subject": "خواننده", "difficulty": 2},
    {"subject": "فعل", "difficulty": 1}, {"subject": "بیماری", "difficulty": 2},
    {"subject": "بازیگر", "difficulty": 3}, {"subject": "پوشیدنی", "difficulty": 2},
    {"subject": "ورزش", "difficulty": 2}, {"subject": "شغل", "difficulty": 1},
    {"subject": "ضرب‌المثل", "difficulty": 3}, {"subject": "ورزشکار", "difficulty": 2},
    {"subject": "رنگ", "difficulty": 1}, {"subject": "حیوان", "difficulty": 2},
    {"subject": "کشور", "difficulty": 2}, {"subject": "فیلم", "difficulty": 3},
    {"subject": "کتاب", "difficulty": 3}, {"subject": "ماشین", "difficulty": 1},
    {"subject": "شاعر", "difficulty": 3}, {"subject": "ساز موسیقی", "difficulty": 3},
    {"subject": "شعر و ترانه", "difficulty": 3}, {"subject": "عنصر شیمیایی", "difficulty": 3},
    {"subject": "اسم نویسنده", "difficulty": 3}
]

PERSIAN_LETTERS = [
    {"letter": "الف", "difficulty": 1}, {"letter": "ب", "difficulty": 1},
    {"letter": "پ", "difficulty": 2}, {"letter": "ت", "difficulty": 1},
    {"letter": "ث", "difficulty": 3}, {"letter": "ج", "difficulty": 2},
    {"letter": "چ", "difficulty": 2}, {"letter": "ح", "difficulty": 3},
    {"letter": "خ", "difficulty": 2}, {"letter": "د", "difficulty": 1},
    {"letter": "ذ", "difficulty": 3}, {"letter": "ر", "difficulty": 1},
    {"letter": "ز", "difficulty": 1}, {"letter": "ژ", "difficulty": 3},
    {"letter": "س", "difficulty": 1}, {"letter": "ش", "difficulty": 2},
    {"letter": "ص", "difficulty": 3}, {"letter": "ض", "difficulty": 3},
    {"letter": "ط", "difficulty": 3}, {"letter": "ظ", "difficulty": 3},
    {"letter": "ع", "difficulty": 2}, {"letter": "غ", "difficulty": 2},
    {"letter": "ف", "difficulty": 2}, {"letter": "ق", "difficulty": 2},
    {"letter": "ک", "difficulty": 1}, {"letter": "گ", "difficulty": 1},
    {"letter": "ل", "difficulty": 1}, {"letter": "م", "difficulty": 1},
    {"letter": "ن", "difficulty": 1}, {"letter": "و", "difficulty": 1},
    {"letter": "ه", "difficulty": 1}, {"letter": "ی", "difficulty": 1}
]

# --- توابع ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    args = context.args
    if args:
        room_id = args[0]
        if room_id in game_rooms and game_rooms[room_id]["status"] == "waiting":
            await join_room(update, context, room_id)
            return
    keyboard = [["🎮 ساخت روم بازی 🎮"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        f"سلام {user.first_name}!\n"
        "به ربات بازی اسم و فامیل سرعتی خوش آمدی.\n"
        "برای شروع یک روم بساز یا با استفاده از لینک دعوت به یک روم ملحق شو.\n\n"
        "برای خروج از بازی در هر زمان از دستور /leave استفاده کن.",
        reply_markup=reply_markup,
    )

async def create_room_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [
            InlineKeyboardButton("5 ثانیه", callback_data="time_5"),
            InlineKeyboardButton("10 ثانیه", callback_data="time_10"),
            InlineKeyboardButton("15 ثانیه", callback_data="time_15"),
        ],
        [InlineKeyboardButton("انصراف", callback_data="cancel_creation")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⏰ زمان هر راند را انتخاب کن:", reply_markup=reply_markup)
    return SELECTING_TIME

async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["time_limit"] = int(query.data.split("_")[1])
    keyboard = [
        [
            InlineKeyboardButton("30 امتیاز", callback_data="score_30"),
            InlineKeyboardButton("45 امتیاز", callback_data="score_45"),
            InlineKeyboardButton("60 امتیاز", callback_data="score_60"),
        ],
        [InlineKeyboardButton("انصراف", callback_data="cancel_creation")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="🏆 امتیاز نهایی برای برنده شدن را انتخاب کن:", reply_markup=reply_markup
    )
    return SELECTING_SCORE

async def select_score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    selected_score = int(query.data.split("_")[1])
    time_limit = context.user_data["time_limit"]
    room_id = str(uuid.uuid4())[:8]
    bot_username = (await context.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?start={room_id}"
    game_rooms[room_id] = {
        "creator_id": user.id,
        "creator_name": user.first_name,
        "players": {user.id: {"name": user.first_name, "score": 0}},
        "settings": {"time": time_limit, "score": selected_score},
        "status": "waiting",
        "current_round": None,
    }
    await query.edit_message_text(
        f"✅ روم شما ساخته شد!\n\n"
        f"تنظیمات:\n"
        f"⏱️ زمان هر راند: {time_limit} ثانیه\n"
        f"🏅 امتیاز نهایی: {selected_score}\n\n"
        f"این لینک را برای دوستت بفرست تا به بازی ملحق شود:\n{invite_link}\n\n"
        f"برای متوقف کردن بازی (فقط توسط سازنده) از /stop و برای خروج همه بازیکنان از /leave استفاده کنید."
    )
    logger.info(f"Room {room_id} created by {user.first_name} ({user.id}).")
    return ConversationHandler.END

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ ساخت روم لغو شد.")
    return ConversationHandler.END

async def join_room(update: Update, context: ContextTypes.DEFAULT_TYPE, room_id=None) -> None:
    user = update.effective_user
    if room_id is None:
        args = context.args
        if args:
            room_id = args[0]
        else:
            await update.message.reply_text("لینک یا آی‌دی روم نامعتبر است.")
            return

    if room_id not in game_rooms:
        await update.message.reply_text("روم مورد نظر یافت نشد یا قبلاً بسته شده است.")
        return
    room = game_rooms[room_id]
    if room["status"] != "waiting":
        await update.message.reply_text("بازی در این روم در حال انجام است و نمی‌توان به آن ملحق شد.")
        return

    if user.id in room["players"]:
        await update.message.reply_text("شما قبلاً به این روم ملحق شده‌اید.")
        return

    # حذف کاربر از روم‌های دیگر (اگر بود)
    for r_id, r_data in game_rooms.items():
        if r_id != room_id and user.id in r_data["players"]:
            del r_data["players"][user.id]

    room["players"][user.id] = {"name": user.first_name, "score": 0}
    await update.message.reply_text(
        f"✅ شما به روم {room_id} ملحق شدید.\n"
        f"تعداد بازیکنان فعلی: {len(room['players'])}\n"
        f"برای شروع بازی منتظر باشید یا اگر سازنده هستید /startgame را بزنید."
    )

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    # پیدا کردن روم کاربر (که سازنده است)
    user_rooms = [
        (room_id, r)
        for room_id, r in game_rooms.items()
        if r["creator_id"] == user.id and r["status"] == "waiting"
    ]
    if not user_rooms:
        await update.message.reply_text("شما روم بازی در حال انتظار ندارید.")
        return
    room_id, room = user_rooms[0]
    if len(room["players"]) < 2:
        await update.message.reply_text("برای شروع بازی حداقل ۲ بازیکن لازم است.")
        return

    room["status"] = "playing"
    room["current_round"] = {"round_number": 0, "players_answered": set()}
    await update.message.reply_text("🎲 بازی شروع شد!")
    asyncio.create_task(game_loop(context, room_id))

async def game_loop(context: ContextTypes.DEFAULT_TYPE, room_id: str):
    room = game_rooms.get(room_id)
    if not room:
        return
    time_limit = room["settings"]["time"]
    target_score = room["settings"]["score"]
    while True:
        if room["status"] != "playing":
            break
        room["current_round"]["round_number"] += 1
        round_num = room["current_round"]["round_number"]

        # انتخاب تصادفی حرف و موضوع با دشواری تصادفی
        letter = random.choice(PERSIAN_LETTERS)["letter"]
        subject = random.choice(CATEGORIES)["subject"]

        # ریست وضعیت بازیکنان در این راند
        room["current_round"]["players_answered"] = set()
        room["current_round"]["letter"] = letter
        room["current_round"]["subject"] = subject

        # ارسال پیام شروع راند
        for player_id in room["players"]:
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text=(
                        f"راند {round_num} شروع شد!\n"
                        f"موضوع: *{subject}*\n"
                        f"حرف: *{letter}*\n"
                        f"شما {time_limit} ثانیه وقت دارید تا پاسخ دهید."
                    ),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning(f"Error sending round start to {player_id}: {e}")

        # تایمر راند
        await asyncio.sleep(time_limit)

        # پایان راند: محاسبه امتیازات
        scores_text = "امتیازات پس از راند {}:\n".format(round_num)
        for pid, pdata in room["players"].items():
            scores_text += f"{pdata['name']}: {pdata['score']}\n"
            if pdata["score"] >= target_score:
                # پایان بازی
                room["status"] = "finished"
                winner_name = pdata["name"]
                for p in room["players"]:
                    try:
                        await context.bot.send_message(
                            chat_id=p,
                            text=f"🏆 بازی تمام شد! برنده: {winner_name}\nامتیاز: {pdata['score']}"
                        )
                    except Exception as e:
                        logger.warning(f"Error sending game end to {p}: {e}")
                del game_rooms[room_id]
                return

        # ارسال امتیازات پس از راند
        for pid in room["players"]:
            try:
                await context.bot.send_message(
                    chat_id=pid,
                    text=scores_text,
                )
            except Exception as e:
                logger.warning(f"Error sending score to {pid}: {e}")

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = update.message.text.strip()
    # پیدا کردن روم کاربر
    user_room = None
    user_room_id = None
    for room_id, room in game_rooms.items():
        if user.id in room["players"] and room["status"] == "playing":
            user_room = room
            user_room_id = room_id
            break
    if not user_room:
        await update.message.reply_text("شما در بازی فعالی شرکت ندارید.")
        return

    # اگر بازیکن قبلاً جواب داده بود
    if user.id in user_room["current_round"]["players_answered"]:
        await update.message.reply_text("شما در این راند قبلاً جواب داده‌اید.")
        return

    letter = user_room["current_round"]["letter"]
    # چک کردن اینکه جواب با حرف شروع می‌شود (می‌توانید قوانین سخت‌تر اضافه کنید)
    if not text.startswith(letter):
        await update.message.reply_text(f"جواب باید با حرف {letter} شروع شود.")
        return

    # ثبت جواب و دادن امتیاز
    user_room["players"][user.id]["score"] += 1
    user_room["current_round"]["players_answered"].add(user.id)
    await update.message.reply_text("✅ جواب ثبت شد و امتیاز دریافت کردید.")

async def protest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # اعتراض در این نسخه هنوز کامل پیاده نشده ولی می‌توانید اینجا کد اضافه کنید.
    await update.message.reply_text("عملیات اعتراض فعلاً پشتیبانی نمی‌شود.")

async def leave_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    removed = False
    to_remove = []
    for room_id, room in game_rooms.items():
        if user.id in room["players"]:
            del room["players"][user.id]
            removed = True
            # اگر سازنده است یا کسی نماند، روم را حذف کن
            if user.id == room["creator_id"] or len(room["players"]) == 0:
                to_remove.append(room_id)
    for rid in to_remove:
        del game_rooms[rid]
    if removed:
        await update.message.reply_text("شما از همه بازی‌ها خارج شدید.")
    else:
        await update.message.reply_text("شما در هیچ بازی فعالی نیستید.")

async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    stopped = False
    to_remove = []
    for room_id, room in game_rooms.items():
        if room["creator_id"] == user.id and room["status"] == "playing":
            room["status"] = "finished"
            to_remove.append(room_id)
            stopped = True
    for rid in to_remove:
        del game_rooms[rid]
    if stopped:
        await update.message.reply_text("بازی متوقف شد.")
    else:
        await update.message.reply_text("شما در هیچ بازی در حال اجرا سازنده نیستید.")

def main() -> None:
    application = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🎮 ساخت روم بازی 🎮$"), create_room_start)],
        states={
            SELECTING_TIME: [CallbackQueryHandler(select_time, pattern=r"^time_\d+$"),
                            CallbackQueryHandler(cancel_creation, pattern="^cancel_creation$")],
            SELECTING_SCORE: [CallbackQueryHandler(select_score, pattern=r"^score_\d+$"),
                             CallbackQueryHandler(cancel_creation, pattern="^cancel_creation$")],
        },
        fallbacks=[CommandHandler("cancel", cancel_creation)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("startgame", start_game))
    application.add_handler(CommandHandler("leave", leave_game))
    application.add_handler(CommandHandler("stop", stop_game))
    application.add_handler(CallbackQueryHandler(cancel_creation, pattern="^cancel_creation$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    application.add_handler(CommandHandler("protest", protest))

    application.run_polling()

if __name__ == "__main__":
    main()
