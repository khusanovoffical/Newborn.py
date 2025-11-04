import telebot
from telebot import types
from flask import Flask, request

# ---------------- CONFIG ----------------
TOKEN = "8496235164:AAFiGPabX2CN2BvjJ3XTdHHTMj88SBDVh04"
CHANNEL_ID = -1003096445262
CHANNEL_USERNAME = "@instagram_akkuntlar"
ADMIN_ID = 7205796796  # admin telegram id

WEBHOOK_BASE = "https://insta-bozor-bot-full.onrender.com"  # <- o'zingizning Render URL ni shu yerga qo'ying

# ---------------- INIT ----------------
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# In-memory storage (soddalashtirilgan). Deploydan keyin qayta yuklansa oʻchadi.
user_data = {}        # temp seller data during submission: {user_id: {...}}
listings = {}         # approved listings: {listing_id: {...}}
next_listing_id = 1
stats = {"users": set(), "posts": 0}

# ---------------- HELPERS ----------------
def check_sub(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ["member", "creator", "administrator"]
    except Exception:
        return False

def make_admin_caption(info, seller_id):
    return (
        f"📩 *Yangi akkaunt so‘rovi*\n\n"
        f"👤 Sotuvchi: @{info.get('username')}\n"
        f"🔗 Havola: {info.get('link')}\n"
        f"👥 Obunachilar: {info.get('followers')}\n"
        f"💰 Narxi: {info.get('price')} so‘m\n"
        f"⭐ Afzalliklar: {info.get('features')}\n"
        f"🆔 Sotuvchi ID: `{seller_id}`"
    )

def make_channel_caption(info):
    return (
        f"📸 *Sotuvdagi akkaunt!* \n\n"
        f"🔗 {info.get('link')}\n"
        f"👥 Obunachilar: {info.get('followers')}\n"
        f"💰 Narxi: {info.get('price')} so‘m\n"
        f"⭐ Afzalliklar: {info.get('features')}"
    )

# ---------------- HANDLERS: START & SUBSCRIPTION ----------------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    stats["users"].add(user_id)

    if not check_sub(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        markup.add(types.InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub"))
        bot.send_message(user_id, "⚠️ Botdan foydalanish uchun kanalga obuna bo‘ling:", reply_markup=markup)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🛍 InstaBozor"))
    markup.add(types.KeyboardButton("💸 Akkaunt sotish"), types.KeyboardButton("📥 Akkaunt sotib olish"))
    bot.send_message(user_id, "👋 Assalomu alaykum! Nima xizmat?", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def check_subscription(call):
    uid = call.message.chat.id
    if check_sub(uid):
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Hali obuna bo‘lmagansiz!")

# ---------------- MENU HANDLERS ----------------
@bot.message_handler(func=lambda m: m.text == "🛍 InstaBozor")
def bozor(m):
    bot.send_message(m.chat.id, f"📢 Akkauntlar kanalimizda: https://t.me/{CHANNEL_USERNAME[1:]}")

@bot.message_handler(func=lambda m: m.text == "📥 Akkaunt sotib olish")
def sotib_olish(m):
    bot.send_message(m.chat.id, f"📸 Akkaunt narxlari va rasmlar: https://t.me/{CHANNEL_USERNAME[1:]} \nMarhamat!")

# ---------------- SELL FLOW ----------------
@bot.message_handler(func=lambda m: m.text == "💸 Akkaunt sotish")
def sell_start(m):
    if not check_sub(m.chat.id):
        return start(m)
    bot.send_message(m.chat.id, "1️⃣ Akkaunt havolasini yuboring:")
    bot.register_next_step_handler(m, get_link)

def get_link(m):
    user_data[m.chat.id] = {
        'link': m.text,
        'username': m.from_user.username or m.from_user.first_name
    }
    bot.send_message(m.chat.id, "2️⃣ Obunachilar sonini yozing:")
    bot.register_next_step_handler(m, get_followers)

def get_followers(m):
    user_data[m.chat.id]['followers'] = m.text
    bot.send_message(m.chat.id, "3️⃣ Akkaunt rasmlarini (1–5 tagacha) yuboring:")
    user_data[m.chat.id]['photos'] = []
    bot.register_next_step_handler(m, get_photos)

def get_photos(m):
    # Accept multiple photos (user sends one by one). Send "Tayyor ✅" when done.
    if m.photo:
        user_data[m.chat.id]['photos'].append(m.photo[-1].file_id)
        if len(user_data[m.chat.id]['photos']) < 5:
            bot.send_message(m.chat.id, "Yana rasm yuborishingiz mumkin yoki 'Tayyor ✅' deb yozing:")
            bot.register_next_step_handler(m, get_photos)
            return
    if not m.photo and m.text not in ["✅ Tayyor", "Tayyor ✅"]:
        bot.send_message(m.chat.id, "Rasm yuboring yoki 'Tayyor ✅' deb yozing.")
        bot.register_next_step_handler(m, get_photos)
        return
    bot.send_message(m.chat.id, "4️⃣ Akkaunt narxini yozing (so'mda):")
    bot.register_next_step_handler(m, get_price)

def get_price(m):
    user_data[m.chat.id]['price'] = m.text
    bot.send_message(m.chat.id, "5️⃣ Akkauntning afzalliklarini yozing:")
    bot.register_next_step_handler(m, get_features)

def get_features(m):
    info = user_data[m.chat.id]
    info['features'] = m.text

    admin_text = make_admin_caption(info, m.chat.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ To‘g‘ri", callback_data=f"ok_{m.chat.id}"),
        types.InlineKeyboardButton("❌ Noto‘g‘ri", callback_data=f"no_{m.chat.id}")
    )

    # send photos + caption to admin
    photos = info['photos']
    if photos:
        # first photo with caption+buttons
        bot.send_photo(ADMIN_ID, photos[0], caption=admin_text, parse_mode="Markdown", reply_markup=markup)
        # rest photos plain
        for p in photos[1:]:
            bot.send_photo(ADMIN_ID, p)
    else:
        bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=markup)

    bot.send_message(m.chat.id, "Rahmat! Maʼlumotlar adminga yuborildi ✅")

# ---------------- ADMIN APPROVE/REJECT ----------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("ok_") or c.data.startswith("no_"))
def admin_check(call):
    global next_listing_id
    data = call.data
    user_id = int(data.split("_")[1])
    info = user_data.get(user_id)
    if not info:
        bot.answer_callback_query(call.id, "❌ Foydalanuvchi topilmadi.")
        return

    if data.startswith("ok_"):
        # Create listing id and save approved listing
        lid = next_listing_id
        next_listing_id += 1
        listings[lid] = {
            "info": info,
            "seller_id": user_id
        }

        # Send to channel: photos + caption, with inline buy button (label: "Akkaunt sotib olish 💬")
        caption = make_channel_caption(info)
        photos = info['photos']
        buy_markup = types.InlineKeyboardMarkup()
        buy_markup.add(types.InlineKeyboardButton("Akkaunt sotib olish 💬", callback_data=f"buy_{lid}"))

        if photos:
            # send first photo with caption
            msg = bot.send_photo(CHANNEL_ID, photos[0], caption=caption, parse_mode="Markdown", reply_markup=buy_markup)
            # send the rest as separate photos (Telegram channels don't support media_group + inline for all)
            for p in photos[1:]:
                bot.send_photo(CHANNEL_ID, p)
        else:
            bot.send_message(CHANNEL_ID, caption, parse_mode="Markdown", reply_markup=buy_markup)

        stats["posts"] += 1
        bot.send_message(user_id, "Akkauntingiz kanalga joylandi ✅")
        bot.answer_callback_query(call.id, "✅ Kanalga joylandi")
    else:
        bot.send_message(user_id, "Maʼlumotlar xato. Iltimos, qayta urinib ko‘ring ❌")
        bot.answer_callback_query(call.id, "❌ Rad etildi")

# ---------------- BUY BUTTON: USER CLICK -> ADMIN NOTIFY ----------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def handle_buy(call):
    buyer_id = call.from_user.id
    buyer_username = call.from_user.username or call.from_user.first_name
    lid = int(call.data.split("_")[1])
    listing = listings.get(lid)

    if not listing:
        bot.answer_callback_query(call.id, "Xatolik: e'lon topilmadi.")
        return

    info = listing["info"]
    seller_id = listing["seller_id"]

    # Notify admin: include buyer info + listing info + listing photos
    admin_buy_text = (
        f"🛒 *Sotib olish so‘rovi*\n\n"
        f"🔔 Xaridor: @{buyer_username} (ID: `{buyer_id}`)\n"
        f"🔗 Akkaunt: {info.get('link')}\n"
        f"👥 Obunachilar: {info.get('followers')}\n"
        f"💰 Narxi: {info.get('price')} so‘m\n"
        f"⭐ Afzalliklar: {info.get('features')}\n"
        f"🆔 Sotuvchi ID: `{seller_id}`\n"
        f"📌 Listing ID: {lid}"
    )

    photos = info.get('photos', [])
    if photos:
        # send listing photos to admin (first with caption)
        bot.send_photo(ADMIN_ID, photos[0], caption=admin_buy_text, parse_mode="Markdown")
        for p in photos[1:]:
            bot.send_photo(ADMIN_ID, p)
    else:
        bot.send_message(ADMIN_ID, admin_buy_text, parse_mode="Markdown")

    # Confirm to buyer
    bot.answer_callback_query(call.id, "🕓 So‘rovingiz adminga yuborildi, javobni kuting ✅", show_alert=False)
    try:
        bot.send_message(buyer_id, "🕓 So‘rovingiz adminga yuborildi, javobni kuting ✅")
    except Exception:
        # if cannot send private message (rare), just ignore
        pass

# ---------------- ADMIN PANEL ----------------
@bot.message_handler(commands=['admin'])
def admin_panel(m):
    if m.chat.id != ADMIN_ID:
        return
    users = len(stats["users"])
    posts = stats["posts"]
    text = (
        f"📊 *Admin panel:*\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"📦 Joylangan akkauntlar: {posts}\n"
        f"🪄 Kanal: {CHANNEL_USERNAME}"
    )
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

# ---------------- WEBHOOK ROUTES ----------------
@app.route('/' + TOKEN, methods=['POST'])
def receive_update():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

@app.route('/')
def index():
    # set webhook to your hosted domain (ensure WEBHOOK_BASE is your render URL)
    bot.remove_webhook()
    bot.set_webhook(url=f'{WEBHOOK_BASE}/{TOKEN}')
    return "Bot Webhook ishga tushdi ✅", 200

# ---------------- RUN ----------------
if __name__ == '__main__':
    # port chosen by Render is usually 10000 or 5000; Render uses PORT env var.
    import os
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
