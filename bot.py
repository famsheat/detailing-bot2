import sqlite3, logging
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler

# Твои данные (вшиты для стабильности)
TOKEN = "8733876154:AAFOPwTsf1RwnCnM6CQ6eDjSEtGHmsvhHLA"
ADMIN_ID = 5006344380

# Прайс и сроки
SERVICES = {
    "✨ Полировка кузова": "Срок: 1-2 дня",
    "💎 Химчистка салона": "Срок: 1 день",
    "💡 Установка подсветки": "Срок: 4-6 часов",
    "🛡 Оклейка плёнкой": "Срок: 2-3 дня"
}
PRICE = 8000

# Этапы записи
DATE, SERVICE, NAME, PHONE, CAR = range(5)

logging.basicConfig(level=logging.INFO)

def init_db():
    conn = sqlite3.connect('detailing.db')
    conn.execute('CREATE TABLE IF NOT EXISTS schedule (work_hours TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS appointments (name TEXT, phone TEXT, car TEXT, datetime TEXT, service TEXT, price INTEGER)')
    conn.commit()
    conn.close()

async def start(update, context):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("👋 Привет, Админ! Используй /work [время] для графика.")
    else:
        await update.message.reply_text("✨ *Добро пожаловать в VIP-Детейлинг!*\n\nНапишите /book для записи.", parse_mode="Markdown")

async def work(update, context):
    if update.effective_user.id != ADMIN_ID: return
    hours = " ".join(context.args)
    conn = sqlite3.connect('detailing.db')
    conn.execute('DELETE FROM schedule')
    conn.execute('INSERT INTO schedule (work_hours) VALUES (?)', (hours,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ График обновлен: {hours}")

async def book(update, context):
    conn = sqlite3.connect('detailing.db')
    work = conn.execute('SELECT work_hours FROM schedule').fetchone()
    conn.close()
    if not work:
        await update.message.reply_text("🚗 Мастер пока не задал график.")
        return ConversationHandler.END
    await update.message.reply_text(f"🕒 *График работы:* {work[0]}\n\n📅 Введите дату и время (например: 25.10 в 15:00):", parse_mode="Markdown")
    return DATE

async def get_date(update, context):
    context.user_data['datetime'] = update.message.text
    kb = [[name] for name in SERVICES.keys()]
    await update.message.reply_text("🛠 *Выберите услугу:*", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True), parse_mode="Markdown")
    return SERVICE

async def get_service(update, context):
    context.user_data['service'] = update.message.text
    info = SERVICES.get(update.message.text, "Срок уточняется при осмотре")
    await update.message.reply_text(f"📋 *Ваш выбор:* {update.message.text}\n⏳ *Примерный срок:* {info}\n\n👤 Как вас зовут?", parse_mode="Markdown")
    return NAME

async def get_name(update, context):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("📱 Введите номер телефона:")
    return PHONE

async def get_phone(update, context):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("🚗 Марка и модель авто:")
    return CAR

async def finish(update, context):
    u = context.user_data
    u['car'] = update.message.text
    
    conn = sqlite3.connect('detailing.db')
    conn.execute('INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?)', (u['name'], u['phone'], u['car'], u['datetime'], u['service'], PRICE))
    conn.commit()
    conn.close()
    
    msg = (f"🎉 *Запись создана!*\n\n👤 Клиент: {u['name']}\n📱 Телефон: {u['phone']}\n🚗 Авто: {u['car']}\n🛠 Услуга: {u['service']}\n💰 Стоимость: {PRICE}₽\n📅 Время: {u['datetime']}")
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    await context.bot.send_message(ADMIN_ID, f"🔔 *Новая запись*\n\n{msg}", parse_mode="Markdown")
    return ConversationHandler.END

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(entry_points=[CommandHandler('book', book)],
        states={DATE: [MessageHandler(filters.TEXT, get_date)],
                SERVICE: [MessageHandler(filters.TEXT, get_service)],
                NAME: [MessageHandler(filters.TEXT, get_name)],
                PHONE: [MessageHandler(filters.TEXT, get_phone)],
                CAR: [MessageHandler(filters.TEXT, finish)]}, fallbacks=[CommandHandler('start', start)])
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('work', work))
    app.run_polling()
