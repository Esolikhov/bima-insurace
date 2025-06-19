import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from db_utils import (
    db_init, add_user, get_user, update_user_lesson,
    get_material_by_day, get_lessons_count
)

from attestation import (
    start_attestation, process_attestation, process_interview, get_state,
    STATE_ATT_QUESTION, STATE_INTERVIEW
)

from admin import is_admin, get_all_interviews, get_interviews_file, get_active_users, reset_db

TOKEN = '7785563549:AAG9MXHaIaGLGwAtLaScrOO-_1q7DUAG-Gk'
DB_PATH = "insurancebot.db"
PROMO_CODE = 'INSUR2024'

# Меню
menu_keyboard = [
    ["📚 Получить урок", "🎟 Промокод"],
    ["📊 Мой прогресс", "📝 Собеседование"],
    ["🏢 Вакансии", "🌐 Сайт компании"],
    ["🔄 Сбросить прогресс"]
]
menu_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

# Логирование
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user:
        await update.message.reply_text(
            "Вы уже зарегистрированы.\nЧтобы получить урок, нажмите на кнопку ниже.",
            reply_markup=menu_markup
        )
    else:
        await update.message.reply_text(
            "Здравствуйте! Введите ваше имя для регистрации:"
        )
        return

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user = get_user(user_id)
    state = get_state(context, user_id)

    if state == STATE_ATT_QUESTION:
        next_q = process_attestation(context, user_id, text)
        await update.message.reply_text(next_q)
        return

    if state == STATE_INTERVIEW:
        result = process_interview(context, user_id, text)
        await update.message.reply_text(result, reply_markup=menu_markup)
        return

    if not user:
        add_user(user_id, text.strip())
        await update.message.reply_text(
            "Спасибо! Вы зарегистрированы.\nЧтобы получить урок, нажмите на кнопку ниже.",
            reply_markup=menu_markup
        )
        return

    if text == "📚 Получить урок":
        await send_lesson(update, context)
        user = get_user(user_id)
        lessons_count = get_lessons_count()
        if user["current_lesson"] > lessons_count and not get_state(context, user_id):
            first_q = start_attestation(context, user_id)
            await update.message.reply_text(
                "Вы завершили все уроки. Для получения промокода и записи на собеседование пройдите итоговую аттестацию!\n" + first_q
            )
        return
    elif text == "🎟 Промокод":
        await send_promo(update, context)
    elif text == "📊 Мой прогресс":
        await send_progress(update, context)
    elif text == "📝 Собеседование":
        await send_interview(update, context)
    elif text == "🏢 Вакансии":
        await update.message.reply_text("Актуальные вакансии: https://bima.tj/vacancies", reply_markup=menu_markup)
    elif text == "🌐 Сайт компании":
        await update.message.reply_text("Официальный сайт: https://bima.tj/", reply_markup=menu_markup)
    elif text == "🔄 Сбросить прогресс":
        await reset_progress(update, context)
    else:
        await update.message.reply_text("Пожалуйста, используйте кнопки меню.", reply_markup=menu_markup)

async def send_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала зарегистрируйтесь командой /start")
        return

    lesson_number = user["current_lesson"]
    lesson = get_material_by_day(lesson_number)
    if lesson:
        if lesson['type'] == 'text':
            text = lesson['text']
            if lesson['link']:
                text += f"\n\nСсылка: {lesson['link']}"
            await update.message.reply_text(text, reply_markup=menu_markup)
        elif lesson['type'] == 'file':
            file_path = lesson['file_paths']
            await update.message.reply_document(document=open(file_path, 'rb'), caption=lesson['text'], reply_markup=menu_markup)
        update_user_lesson(update.effective_user.id, lesson_number + 1)
    else:
        await update.message.reply_text("На сегодня уроков больше нет. Вы молодец!", reply_markup=menu_markup)

async def send_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    lessons_count = get_lessons_count()
    if user and user['current_lesson'] > lessons_count:
        await update.message.reply_text(
            f'Поздравляем, вы прошли весь курс!\nВаш промокод: {PROMO_CODE}',
            reply_markup=menu_markup
        )
    else:
        await update.message.reply_text(
            'Пожалуйста, завершите все уроки, чтобы получить промокод.',
            reply_markup=menu_markup
        )

async def send_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    lessons_count = get_lessons_count()
    if user:
        await update.message.reply_text(
            f"Ваш прогресс: {min(user['current_lesson']-1, lessons_count)}/{lessons_count} уроков.",
            reply_markup=menu_markup
        )

async def send_interview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    lessons_count = get_lessons_count()
    if user and user['current_lesson'] > lessons_count:
        await update.message.reply_text(
            "Ваша заявка на собеседование принята!\nС вами свяжется специалист в ближайшее время.",
            reply_markup=menu_markup
        )
    else:
        await update.message.reply_text(
            "Пожалуйста, завершите все уроки, чтобы записаться на собеседование.",
            reply_markup=menu_markup
        )

async def reset_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("UPDATE users SET current_lesson=1 WHERE telegram_id=?", (telegram_id,))
    con.commit()
    con.close()
    if telegram_id in context.user_data:
        del context.user_data[telegram_id]
    await update.message.reply_text(
        "Ваш прогресс сброшен. Вы можете начать обучение заново! Используйте кнопку 'Получить урок'.",
        reply_markup=menu_markup
    )

# --- АДМИН КОМАНДЫ ---

async def admin_interviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Доступ запрещён.")
        return
    await update.message.reply_text(get_all_interviews())

async def admin_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Доступ запрещён.")
        return
    file = get_interviews_file()
    if file:
        await update.message.reply_document(file, filename="interviews.csv")
        file.close()
    else:
        await update.message.reply_text("Файл с заявками не найден.")

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Доступ запрещён.")
        return
    await update.message.reply_text(get_active_users())

# --- СБРОС БАЗЫ ДАННЫХ ---

async def admin_reset_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Доступ запрещён.")
        return
    msg = reset_db()
    await update.message.reply_text(msg)

# --- КОНЕЦ АДМИН БЛОКА ---

def main():
    db_init()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset_progress))
    application.add_handler(CommandHandler("admin_interviews", admin_interviews))
    application.add_handler(CommandHandler("admin_file", admin_file))
    application.add_handler(CommandHandler("admin_users", admin_users))
    application.add_handler(CommandHandler("admin_reset_db", admin_reset_db))  # <-- новый обработчик
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.run_polling()

if __name__ == '__main__':
    main()
