import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters, \
    ConversationHandler
import os
import dotenv

# Определяем состояния
DAY, CLASS = range(2)
dotenv.load_dotenv()


# Ссылки на Google Sheets для каждого дня
SHEET_LINKS = {
    'Понедельник': '1x18Nc2Lr7Ngz8TKS42Lj90Yt8HY6IPxlOZ7BQYyGJ3Q',
    'Вторник': '13qaJOlSOyPIoRChhFvUVPQQi1_epW6HXouq6tULz9W0',
    'Среда': '1iAIHPysJsk-0-RykEueFw0KLZszxl4xPfXL--Jl0PzU',
    'Четверг': '1ocDeEne_9p7AIbCFDOsJnUtkzr4BXAlf29d6h6O2lFk',
    'Пятница': '15EJNyajCT6pPFouExF77fgvyZmKZZRHAVVqhQHmwI4k',

}


def load_schedule(day):
    try:
        sheet_id = SHEET_LINKS.get(day)
        if not sheet_id:
            print(f"Не найдена ссылка для дня: {day}")
            return pd.DataFrame()

        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx'
        schedule_df = pd.read_excel(url, header=0)
        return schedule_df
    except Exception as e:
        print(f"Ошибка при загрузке расписания для {day}: {e}")
        return pd.DataFrame()


# Команда /start
async def start(update: Update, context: CallbackContext):
    await show_days(update)
    return DAY


# Показать дни недели
async def show_days(update: Update):
    keyboard = [
        ['Понедельник', 'Вторник', 'Среда'],
        ['Четверг', 'Пятница', ],
        ['/start']  # Добавил кнопку для перезапуска
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите день недели:", reply_markup=reply_markup)


# Обработка выбранного дня недели
async def handle_day_selection(update: Update, context: CallbackContext):
    selected_day = update.message.text.strip()

    # Обработка команды /start
    if selected_day == '/start':
        return await start(update, context)

    context.user_data['selected_day'] = selected_day
    await update.message.reply_text("⌛ Загружаю расписание...")

    schedule_df = load_schedule(selected_day)

    if schedule_df.empty:
        await update.message.reply_text("⚠️ Не удалось загрузить расписание. Попробуйте другой день.")
        await show_days(update)
        return DAY

    classes = [col for col in schedule_df.columns[1:] if isinstance(col, str)]
    if not classes:
        await update.message.reply_text("Ошибка: не найдены классы в таблице.")
        await show_days(update)
        return DAY

    keyboard = [[cls.strip()] for cls in classes]
    keyboard.append(['Назад'])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text("Выберите класс:", reply_markup=reply_markup)
    return CLASS


# Обработка выбора класса
async def handle_class_selection(update: Update, context: CallbackContext):
    selected_class = update.message.text.strip()

    if selected_class == 'Назад':
        await show_days(update)
        return DAY

    selected_day = context.user_data.get('selected_day')
    schedule_df = load_schedule(selected_day)

    if selected_class not in schedule_df.columns:
        await update.message.reply_text(f"Класс '{selected_class}' не найден.")
        await show_days(update)
        return DAY

    response = f"📅 Расписание для {selected_class} на {selected_day}:\n\n"
    for index, row in schedule_df.iterrows():
        time_slot = row[0]
        subject = row[selected_class] if pd.notna(row[selected_class]) else "—"
        response += f"⏰ {time_slot}: {subject}\n"

    response += "\nВыберите другой класс или день для продолжения:"
    await update.message.reply_text(response)

    # Возвращаемся к выбору класса
    classes = [col for col in schedule_df.columns[1:] if isinstance(col, str)]
    keyboard = [[cls.strip()] for cls in classes]
    keyboard.append(['Назад'])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите класс или 'Назад' для выбора другого дня:", reply_markup=reply_markup)
    return CLASS


def main():

    app = ApplicationBuilder().token(os.getenv('token', 'No token')).build()

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_day_selection)],
            CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_class_selection)]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conversation_handler)
    app.run_polling()


if __name__ == '__main__':
    main()