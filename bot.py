import sqlite3, logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, CommandHandler, ContextTypes

TOKEN = "8733876154:AAFOPwTsf1RwnCnM6CQ6eDjSEtGHmsvhHLA"
ADMIN_ID = 5006344380

ASK_SERVICE, ASK_NAME, ASK_CAR = range(3)
logging.basicConfig(level=logging.INFO)

def init_db():
    conn = sqlite3.connect('detailing.db')
    conn.execute('CREATE TABLE IF NOT EXISTS slots (id INTEGER PRIMARY KEY, slot_text TEXT, is_taken INTEGER DEFAULT 0)')
    conn.execute('CREATE TABLE IF NOT EXISTS appointments (id INTEGER PRIMARY KEY, name TEXT, car TEXT, slot TEXT, service TEXT)')
    conn.commit()
    conn.close()

async def start(update, context):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("👋 Админ, используй /add [время] для слотов.")
    else:
        kb = [[InlineKeyboardButton("📅 Записаться", callback_data="show_slots")]]
        await update.message.reply_text("✨ Добро пожаловать!", reply_markup=InlineKeyboardMarkup(kb))

async def add_slot(update, context):
    if update.effective_user.id != ADMIN_ID: return
    slot_time = " ".join(context.args)
    conn = sqlite3.connect('detailing.db')
    conn.execute('INSERT INTO slots (slot_text) VALUES (?)', (slot_time,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Слот {slot_time} добавлен.")

async def show_slots(update, context):
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect('detailing.db')
    slots = conn.execute('SELECT id, slot_text FROM slots WHERE is_taken = 0').fetchall()
    conn.close()
    if not slots:
        await query.edit_message_text("❌ Нет свободных мест.")
        return ConversationHandler.END
    kb = [[InlineKeyboardButton(f"🕒 {s[1]}", callback_data=f"slot_{s[0]}")] for s in slots]
    await query.edit_message_text("🕒 Выберите время:", reply_markup=InlineKeyboardMarkup(kb))
    return ASK_SERVICE

async def select_service(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data['slot_id'] = query.data.split('_')[1]
    conn = sqlite3.connect('detailing.db')
    context.user_data['slot_text'] = conn.execute('SELECT slot_text FROM slots WHERE id = ?', (context.user_data['slot_id'],)).fetchone()[0]
    conn.close()
    kb = [[InlineKeyboardButton(name, callback_data=name)] for name in ["Полировка фар", "Полировка кузова", "Подсветка"]]
    await query.edit_message_text("🛠 Выберите услугу:", reply_markup=InlineKeyboardMarkup(kb))
    return ASK_NAME

async def ask_name(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data['service'] = query.data
    await query.message.reply_text("👤 Введите ваше имя:")
    return ASK_CAR

async def finish(update, context):
    name = update.message.text
    slot = context.user_data['slot_text']
    service = context.user_data['service']
    conn = sqlite3.connect('detailing.db')
    conn.execute('INSERT INTO appointments (name, slot, service) VALUES (?, ?, ?)', (name, slot, service))
    conn.execute('UPDATE slots SET is_taken = 1 WHERE id = ?', (context.user_data['slot_id'],))
    conn.commit()
    conn.close()
    await update.message.reply_text("🎉 Записано!")
    await context.bot.send_message(ADMIN_ID, f"🔔 Новая запись: {name}, {service}, {slot}")
    return ConversationHandler.END

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(entry_points=[CallbackQueryHandler(show_slots, pattern='show_slots')],
        states={ASK_SERVICE: [CallbackQueryHandler(select_service, pattern='^slot_')],
                ASK_NAME: [CallbackQueryHandler(ask_name)],
                ASK_CAR: [MessageHandler(filters.TEXT, finish)]}, fallbacks=[])
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('add', add_slot))
    app.add_handler(conv)
    app.run_polling()
