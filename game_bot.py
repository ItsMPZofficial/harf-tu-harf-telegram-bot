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

# فعال کردن لاگ برای دیباگ کردن بهتر
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# تعریف مراحل مختلف در مکالمه برای ساخت روم
SELECTING_TIME, SELECTING_SCORE = range(2)

# این دیکشنری اطلاعات تمام روم‌های بازی فعال را نگه می‌دارد
game_rooms = {}

# لیست موضوعات با درجه سختی
CATEGORIES = [
  { "subject": "اسم", "difficulty": 1 }, { "subject": "فامیل", "difficulty": 1 },
  { "subject": "گل و گیاه", "difficulty": 2 }, { "subject": "شهر", "difficulty": 1 },
  { "subject": "میوه", "difficulty": 1 }, { "subject": "مارک", "difficulty": 2 },
  { "subject": "اعضای بدن", "difficulty": 2 }, { "subject": "شخصیت تاریخی", "difficulty": 3 },
  { "subject": "شخصیت داستانی", "difficulty": 2 }, { "subject": "غذا", "difficulty": 1 },
  { "subject": "اشیاء", "difficulty": 1 }, { "subject": "ابزار", "difficulty": 1 },
  { "subject": "مکان عمومی", "difficulty": 2 }, { "subject": "خواننده", "difficulty": 2 },
  { "subject": "فعل", "difficulty": 1 }, { "subject": "بیماری", "difficulty": 2 },
  { "subject": "بازیگر", "difficulty": 3 }, { "subject": "پوشیدنی", "difficulty": 2 },
  { "subject": "ورزش", "difficulty": 2 }, { "subject": "شغل", "difficulty": 1 },
  { "subject": "ضرب‌المثل", "difficulty": 3 }, { "subject": "ورزشکار", "difficulty": 2 },
  { "subject": "رنگ", "difficulty": 1 }, { "subject": "حیوان", "difficulty": 2 },
  { "subject": "کشور", "difficulty": 2 }, { "subject": "فیلم", "difficulty": 3 },
  { "subject": "کتاب", "difficulty": 3 }, { "subject": "ماشین", "difficulty": 1 },
  { "subject": "شاعر", "difficulty": 3 }, { "subject": "ساز موسیقی", "difficulty": 3 },
  { "subject": "شعر و ترانه", "difficulty": 3 }, { "subject": "عنصر شیمیایی", "difficulty": 3 },
  { "subject": "اسم نویسنده", "difficulty": 3 }
]

# لیست حروف الفبا با درجه سختی
PERSIAN_LETTERS = [
  { "letter": "الف", "difficulty": 1 }, { "letter": "ب", "difficulty": 1 },
  { "letter": "پ", "difficulty": 2 }, { "letter": "ت", "difficulty": 1 },
  { "letter": "ث", "difficulty": 3 }, { "letter": "ج", "difficulty": 2 },
  { "letter": "چ", "difficulty": 2 }, { "letter": "ح", "difficulty": 3 },
  { "letter": "خ", "difficulty": 2 }, { "letter": "د", "difficulty": 1 },
  { "letter": "ذ", "difficulty": 3 }, { "letter": "ر", "difficulty": 1 },
  { "letter": "ز", "difficulty": 1 }, { "letter": "ژ", "difficulty": 3 },
  { "letter": "س", "difficulty": 1 }, { "letter": "ش", "difficulty": 2 },
  { "letter": "ص", "difficulty": 3 }, { "letter": "ض", "difficulty": 3 },
  { "letter": "ط", "difficulty": 3 }, { "letter": "ظ", "difficulty": 3 },
  { "letter": "ع", "difficulty": 2 }, { "letter": "غ", "difficulty": 2 },
  { "letter": "ف", "difficulty": 2 }, { "letter": "ق", "difficulty": 2 },
  { "letter": "ک", "difficulty": 1 }, { "letter": "گ", "difficulty": 1 },
  { "letter": "ل", "difficulty": 1 }, { "letter": "م", "difficulty": 1 },
  { "letter": "ن", "difficulty": 1 }, { "letter": "و", "difficulty": 1 },
  { "letter": "ه", "difficulty": 1 }, { "letter": "ی", "difficulty": 1 }
]

# --- توابع اصلی شروع و ساخت روم ---

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
        "status": "waiting", "current_round": None, "timer_task": None,
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

async def join_room(update: Update, context: ContextTypes.DEFAULT_TYPE, room_id: str):
    user = update.effective_user
    if room_id not in game_rooms:
        await update.message.reply_text("این روم بازی دیگر وجود ندارد.")
        return
        
    room = game_rooms[room_id]
    if user.id in room["players"]:
        await update.message.reply_text("شما از قبل در این روم هستید!")
        return
    if len(room["players"]) >= 2:
        await update.message.reply_text("متاسفانه ظرفیت این روم تکمیل شده است.")
        return
        
    room["players"][user.id] = {"name": user.first_name, "score": 0}
    room["status"] = "playing"
    logger.info(f"Player {user.first_name} ({user.id}) joined room {room_id}.")
    for player_id in room["players"]:
        await context.bot.send_message(
            chat_id=player_id, text=f"🎉 {user.first_name} به بازی پیوست! بازی شروع می‌شود..."
        )
    await asyncio.sleep(2)
    await start_new_round(context, room_id)


async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("ساخت روم لغو شد.")
    return ConversationHandler.END


async def no_answer_in_time(context: ContextTypes.DEFAULT_TYPE, room_id: str):
    """Handles the case where no one answers in time."""
    if room_id not in game_rooms or game_rooms[room_id]["status"] != "playing":
        return

    room = game_rooms[room_id]
    if room.get("current_round") and room["current_round"].get("answered_by") is None:
        room["current_round"]["answered_by"] = "TIMEOUT" 
        for player_id in room["players"]:
            try:
                await context.bot.send_message(chat_id=player_id, text="⌛️ زمان تمام شد! هیچکس پاسخی نداد.\nآماده برای راند بعدی...")
            except Exception as e:
                logger.error(f"Error sending timeout message to {player_id}: {e}")

        await asyncio.sleep(3) 
        await start_new_round(context, room_id)


async def start_new_round(context: ContextTypes.DEFAULT_TYPE, room_id: str):
    if room_id not in game_rooms or game_rooms[room_id]["status"] != "playing":
        return
        
    room = game_rooms[room_id]
    
    # Clean up protest info from the previous round
    if "last_round_info" in room:
        del room["last_round_info"]
        
    if room.get("timer_task") and not room["timer_task"].done():
        room["timer_task"].cancel()

    countdown_messages = {}
    for player_id in room["players"]:
        msg = await context.bot.send_message(chat_id=player_id, text="🚀")
        countdown_messages[player_id] = msg
        
    for i in range(3, 0, -1):
        for player_id, msg in countdown_messages.items():
            try:
                await msg.edit_text(f"راند بعدی تا {i} ثانیه دیگر...")
            except Exception as e:
                logger.error(f"Could not edit message for countdown: {e}")
        await asyncio.sleep(1)

    selected_category_info = random.choice(CATEGORIES)
    selected_letter_info = random.choice(PERSIAN_LETTERS)
    
    room["current_round"] = {
        "category_info": selected_category_info,
        "letter_info": selected_letter_info,
        "answered_by": None,
        "round_id": str(uuid.uuid4())
    }
    
    scores_text = "\n".join([f"👤 {p['name']}: {p['score']}" for p in room["players"].values()])
    message_text = (
        f"ዙ راند جدید! ዙ\n\n"
        f"موضوع: **{selected_category_info['subject']}** (سختی: {selected_category_info['difficulty']})\n"
        f"با حرف: **{selected_letter_info['letter']}** (سختی: {selected_letter_info['difficulty']})\n\n"
        f"--- امتیازات ---\n{scores_text}"
    )

    for player_id, msg in countdown_messages.items():
         await msg.edit_text(text=message_text, parse_mode='Markdown')

    time_limit = room["settings"]["time"]
    job_name = f'timeout_{room_id}'
    
    # Remove any existing job with the same name
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()
        
    context.job_queue.run_once(
        lambda ctx: asyncio.create_task(no_answer_in_time(ctx, room_id)),
        time_limit,
        name=job_name,
        data={'room_id': room_id}
    )


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    answer = update.message.text
    active_room_id = None
    for room_id, room_data in game_rooms.items():
        if user.id in room_data["players"] and room_data["status"] == "playing":
            active_room_id = room_id
            break
            
    if not active_room_id:
        return
        
    room = game_rooms[active_room_id]
    current_round = room.get("current_round")
    
    if not current_round or current_round.get("answered_by") is not None:
        return

    job_name = f'timeout_{active_room_id}'
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()

    letter_info = current_round["letter_info"]
    if answer.strip().startswith(letter_info["letter"]):
        current_round["answered_by"] = user.id
        
        category_info = current_round["category_info"]
        score_this_round = category_info["difficulty"] + letter_info["difficulty"]
        room["players"][user.id]["score"] += score_this_round
        
        # **FIX**: Store round info for potential protest
        room["last_round_info"] = {
            "round_id": current_round["round_id"],
            "winner_id": user.id,
            "score": score_this_round,
            "answer": answer
        }

        winner_name = room["players"][user.id]["name"]
        announcement = f"✅ آفرین {winner_name}!\nجواب: *{answer}*\n\nشما *{score_this_round}* امتیاز گرفتی."
        
        protest_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("⚖️ اعتراض دارم!", callback_data=f"protest_{active_room_id}_{current_round['round_id']}")
        ]])
        
        for player_id in room["players"]:
            if player_id == user.id:
                await context.bot.send_message(chat_id=player_id, text=announcement, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=player_id, text=announcement, reply_markup=protest_button, parse_mode='Markdown')

        if room["players"][user.id]["score"] >= room["settings"]["score"]:
            await end_game(context, active_room_id, f"برنده نهایی {winner_name} است")
        else:
            await asyncio.sleep(5)
            if game_rooms.get(active_room_id) and game_rooms[active_room_id]["status"] == "playing":
                await start_new_round(context, active_room_id)


async def protest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    try:
        _, room_id, round_id_from_callback = query.data.split("_")
    except ValueError:
        await query.answer("خطا در پردازش اعتراض.", show_alert=True)
        return

    if room_id not in game_rooms:
        await query.answer("این بازی دیگر وجود ندارد.", show_alert=True)
        return

    room = game_rooms[room_id]
    last_round = room.get("last_round_info")

    if last_round and last_round["round_id"] == round_id_from_callback:
        await query.answer("اعتراض شما ثبت شد!")
        
        winner_id = last_round["winner_id"]
        score_to_revert = last_round["score"]
        winner_name = room["players"][winner_id]["name"]
        protester_name = query.from_user.first_name
        
        room["players"][winner_id]["score"] -= score_to_revert
        
        protest_message = (
            f"❗️ **اعتراض ثبت شد!**\n\n"
            f"{protester_name} به پاسخ '{last_round['answer']}' اعتراض کرد.\n"
            f"{score_to_revert} امتیاز از {winner_name} کسر شد."
        )
        
        # Remove the protest button and update the message
        await query.edit_message_text(text=query.message.text_markdown + f"\n\n*(⚖️ اعتراض توسط {protester_name} ثبت شد)*", parse_mode='Markdown')

        for player_id in room["players"]:
            await context.bot.send_message(chat_id=player_id, text=protest_message, parse_mode='Markdown')
            
        # Remove info to prevent double protest
        del room["last_round_info"]
    else:
        await query.answer("فرصت اعتراض برای این راند تمام شده است.", show_alert=True)
        # Optionally remove the button if the protest is too late
        await query.edit_message_text(text=query.message.text_markdown + "\n\n*(فرصت اعتراض تمام شد)*", parse_mode='Markdown')

async def end_game(context: ContextTypes.DEFAULT_TYPE, room_id: str, reason: str):
    if room_id not in game_rooms or game_rooms[room_id]["status"] == "finished":
        return
        
    room = game_rooms[room_id]
    room["status"] = "finished"

    # Cancel any running timer job
    job_name = f'timeout_{room_id}'
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()

    scores_text = "\n".join([f"👤 {p['name']}: {p['score']}" for p in room["players"].values()])
    final_message = (
        f"🏆 **بازی تمام شد!** 🏆\n\n"
        f"علت: *{reason}*\n\n"
        f"--- امتیازات نهایی ---\n{scores_text}"
    )
    for player_id in room["players"]:
        await context.bot.send_message(chat_id=player_id, text=final_message, parse_mode='Markdown')
        
    creator_id = room["creator_id"]
    keyboard = [[InlineKeyboardButton("🔄 شروع مجدد بازی", callback_data=f"restart_{room_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if 'creator_id' in room and room['creator_id']:
            await context.bot.send_message(chat_id=creator_id, text="می‌خواهید دوباره بازی کنید؟", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Could not send restart message to creator {creator_id}: {e}")
    
    # Clean up the room immediately
    if room_id in game_rooms:
        del game_rooms[room_id]
        logger.info(f"Room {room_id} finished and cleaned up.")


async def restart_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("این قابلیت در حال حاضر غیرفعال است.")


# NEW: Stop game command (creator only)
async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    active_room_id = None
    for room_id, room_data in game_rooms.items():
        if user.id == room_data.get("creator_id") and room_data.get("status") == "playing":
            active_room_id = room_id
            break

    if not active_room_id:
        await update.message.reply_text("شما سازنده یک بازی فعال نیستید یا بازی در حال اجرا نیست.")
        return

    logger.info(f"Creator {user.first_name} ({user.id}) stopped room {active_room_id}.")
    await end_game(context, active_room_id, "بازی توسط سازنده متوقف شد")


# NEW: Leave game command (any player)
async def leave_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    active_room_id = None
    
    for room_id, room_data in game_rooms.items():
        if user.id in room_data.get("players", {}) and room_data.get("status") == "playing":
            active_room_id = room_id
            break

    if not active_room_id:
        await update.message.reply_text("شما در حال حاضر در هیچ بازی فعالی نیستید.")
        return
    
    room = game_rooms[active_room_id]
    leaver_name = room["players"][user.id]["name"]
    logger.info(f"Player {leaver_name} ({user.id}) left room {active_room_id}.")
    await end_game(context, active_room_id, f"بازیکن {leaver_name} از بازی خارج شد")


def main() -> None:
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN not found in environment variables!")
        return
        
    application = Application.builder().token(token).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🎮 ساخت روم بازی 🎮$"), create_room_start)],
        states={
            SELECTING_TIME: [CallbackQueryHandler(select_time, pattern="^time_")],
            SELECTING_SCORE: [CallbackQueryHandler(select_score, pattern="^score_")],
        },
        fallbacks=[CallbackQueryHandler(cancel_creation, pattern="^cancel_creation$")],
        per_message=False
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop_game))
    application.add_handler(CommandHandler("leave", leave_game)) # NEW
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    application.add_handler(CallbackQueryHandler(restart_game_callback, pattern="^restart_"))
    application.add_handler(CallbackQueryHandler(protest_callback, pattern="^protest_"))
    
    application.run_polling()

if __name__ == "__main__":
    main()