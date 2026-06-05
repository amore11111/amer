import telebot
import sqlite3
from telebot import types

TOKEN = '816336444:AAFECNgfVTunBrgaqoZy0KRRXvjr-BhGKeE'
ADMIN_ID = 454731317
CHANNEL_URL = 'https://t.me/YourChannelUsername'
ADMIN_USERNAME = '@YourAdminUsername' # استبدله بمعرفك

bot = telebot.TeleBot(TOKEN)
user_data = {}

def get_db():
    conn = sqlite3.connect('bot_data.db')
    return conn, conn.cursor()

def init_db():
    conn, cur = get_db()
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    cur.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, service_id TEXT, link TEXT, qty INTEGER, status TEXT, order_id TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS services (id TEXT PRIMARY KEY, cat TEXT, name TEXT, rate TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

init_db()

def is_banned(u_id):
    conn, cur = get_db()
    cur.execute('SELECT 1 FROM banned_users WHERE user_id = ?', (u_id,))
    res = cur.fetchone()
    conn.close()
    return res is not None

# --- القائمة الرئيسية ---
def get_main_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛍️ عرض الخدمات", callback_data="show_services"),
               types.InlineKeyboardButton("💰 رصيدي", callback_data="check_balance"))
    markup.add(types.InlineKeyboardButton("💳 شحن رصيد", callback_data="add_balance"))
    markup.add(types.InlineKeyboardButton("📜 طلباتي", callback_data="my_orders_btn"))
    markup.add(types.InlineKeyboardButton("📢 قناة البوت", url=CHANNEL_URL))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    if is_banned(message.chat.id): return
    conn, cur = get_db()
    cur.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.chat.id,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "أهلاً بك في بوت الخدمات، اختر ما تحتاجه:", reply_markup=get_main_markup())

# --- معالج الأزرار ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if is_banned(call.message.chat.id): return
    u_id = call.message.chat.id
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_main"))

    if call.data == "check_balance":
        conn, cur = get_db()
        cur.execute('SELECT balance FROM users WHERE user_id = ?', (u_id,))
        res = cur.fetchone()
        balance = res[0] if res else 0
        conn.close()
        bot.edit_message_text(f"💰 رصيدك الحالي هو: {balance}$", u_id, call.message.message_id, reply_markup=markup)

    elif call.data == "add_balance":
        bot.edit_message_text(f"💳 **لشحن رصيدك:**\n\nيرجى التواصل مع الإدارة: {ADMIN_USERNAME}\nأرسل لهم صورة التحويل مع رقم هويتك داخل البوت.", 
                              u_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "show_services":
        bot.edit_message_text("🛍️ قائمة الخدمات:\nهنا يتم عرض الخدمات من قاعدة البيانات.", u_id, call.message.message_id, reply_markup=markup)

    elif call.data == "my_orders_btn":
        bot.edit_message_text("📜 طلباتك السابقة:\nلا يوجد طلبات حالياً.", u_id, call.message.message_id, reply_markup=markup)

    elif call.data == "back_to_main":
        bot.edit_message_text("أهلاً بك مجدداً، اختر الخدمة:", u_id, call.message.message_id, reply_markup=get_main_markup())

# --- معالج أوامر الأدمن والرسائل ---
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    if is_banned(message.chat.id): return
    
    if message.chat.id == ADMIN_ID:
        if message.text == '/admin':
            bot.send_message(ADMIN_ID, "👑 **لوحة تحكم الأدمن:**\n\n💰 `/add ID المبلغ` - شحن\n🚫 `/ban ID` - حظر\n✅ `/unban ID` - فك حظر\n📢 `/broadcast الرسالة` - إذاعة\n🛠 `/addservice` - إضافة خدمة\n🗑 `/delservice` - حذف خدمة", parse_mode="Markdown")
            return
        
        cmd = message.text.split()
        if message.text.startswith('/add '):
            conn, cur = get_db()
            cur.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (float(cmd[2]), int(cmd[1])))
            conn.commit()
            conn.close()
            bot.send_message(ADMIN_ID, "✅ تم الشحن.")
        elif message.text.startswith('/ban '):
            conn, cur = get_db()
            cur.execute('INSERT OR IGNORE INTO banned_users VALUES (?)', (int(cmd[1]),))
            conn.commit()
            conn.close()
            bot.send_message(ADMIN_ID, "🚫 تم الحظر.")
        elif message.text.startswith('/unban '):
            conn, cur = get_db()
            cur.execute('DELETE FROM banned_users WHERE user_id = ?', (int(cmd[1]),))
            conn.commit()
            conn.close()
            bot.send_message(ADMIN_ID, "✅ تم فك الحظر.")
        elif message.text.startswith('/broadcast '):
            text = message.text.replace('/broadcast ', '', 1)
            conn, cur = get_db()
            cur.execute('SELECT user_id FROM users')
            for u in cur.fetchall():
                try: bot.send_message(u[0], text)
                except: pass
            conn.close()
            bot.send_message(ADMIN_ID, "📢 تم الإرسال.")
        elif message.text == '/addservice':
            user_data[ADMIN_ID] = {'state': 'add_id'}
            bot.send_message(ADMIN_ID, "📝 أرسل ID الخدمة:")
        elif message.text == '/delservice':
            user_data[ADMIN_ID] = {'state': 'del_id'}
            bot.send_message(ADMIN_ID, "🗑️ أرسل ID الخدمة للحذف:")
        elif ADMIN_ID in user_data and user_data[ADMIN_ID]['state'] == 'del_id':
            conn, cur = get_db()
            cur.execute('DELETE FROM services WHERE id = ?', (message.text,))
            conn.commit()
            conn.close()
            bot.send_message(ADMIN_ID, "✅ تم الحذف.")
            del user_data[ADMIN_ID]

bot.polling(none_stop=True)
