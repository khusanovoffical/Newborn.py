import telebot
from telebot import types
from flask import Flask, request

# 🔹 Token va sozlamalar
TOKEN = "8496235164:AAFk0H8IVfM8ao7tTyo1ZTgWY3i_sfanmmc"
ADMIN_ID = 6901872341
CHANNEL_ID = -1003096445262
CHANNEL_LINK = "https://t.me/instagram_akkuntlar"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- Majburiy kanal tekshiruvi
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False


# --- Start komandasi
@bot.message_handler(commands=['start'])
def start(message):
    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 Kanalga obuna bo‘lish", url=CHANNEL_LINK))
        bot.send_message(message.chat.id, "❗ Botdan foydalanish uchun kanalga obuna bo‘ling!", reply_markup=markup)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📱 Insta Bozor", "🛒 Akkaunt sotib olish 💬", "📤 Akkaunt sotish")
    bot.send_message(message.chat.id, "Assalomu alaykum! Nima xizmat? 👇", reply_markup=markup)


# --- Tugmalarni ishlovchi qism
@bot.message_handler(func=lambda m: True)
def menu_handler(message):
    if message.text == "📱 Insta Bozor":
        bot.send_message(message.chat.id, f"📢 Akkountlar {CHANNEL_LINK} kanalida joylanadi.")

    elif message.text == "🛒 Akkaunt sotib olish 💬":
        bot.send_message(
            message.chat.id,
            f"💬 Akkountlar narxlari va rasmlarini {CHANNEL_LINK} kanalidan ko‘rishingiz mumkin.\n"
            f"Sotib olish uchun adminga murojaat qiling."
        )
        bot.send_message(ADMIN_ID, f"👤 {message.from_user.first_name} akkaunt sotib olmoqchi.")

    elif message.text == "📤 Akkaunt sotish":
        bot.send_message(message.chat.id, "🧾 Akkount havolasini yuboring:")
        bot.register_next_step_handler(message, get_link)


def get_link(message):
    user_data = {'link': message.text}
    bot.send_message(message.chat.id, "👥 Obunachilar sonini kiriting:")
    bot.register_next_step_handler(message, get_followers, user_data)


def get_followers(message, user_data):
    user_data['followers'] = message.text
    bot.send_message(message.chat.id, "🖼 1-5 ta rasm yuboring:")
    bot.register_next_step_handler(message, get_photos, user_data, [])


def get_photos(message, user_data, photos):
    if message.content_type == 'photo':
        photos.append(message.photo[-1].file_id)
        if len(photos) < 5:
            bot.send_message(message.chat.id, "Yana rasm yuboring yoki 'tugatdim' deb yozing:")
            bot.register_next_step_handler(message, get_photos, user_data, photos)
            return

    if message.text and message.text.lower() == 'tugatdim' or len(photos) >= 1:
        user_data['photos'] = photos
        bot.send_message(message.chat.id, "💰 Narxni so‘mda yozing:")
        bot.register_next_step_handler(message, get_price, user_data)


def get_price(message, user_data):
    user_data['price'] = message.text
    bot.send_message(message.chat.id, "📌 Akkaunt afzal tomonlarini yozing:")
    bot.register_next_step_handler(message, get_advantages, user_data)


def get_advantages(message, user_data):
    user_data['advantages'] = message.text
    bot.send_message(message.chat.id, "✅ Raxmat! Ma’lumotlar adminga yuborildi, 24 soat ichida kanalga joylanadi.")
    
    text = (
        f"🆕 Yangi akkaunt sotuvga qo‘shildi:\n\n"
        f"🔗 Havola: {user_data['link']}\n"
        f"👥 Obunachilar: {user_data['followers']}\n"
        f"💰 Narx: {user_data['price']} so‘m\n"
        f"📋 Afzalliklar: {user_data['advantages']}\n\n"
        f"👤 Foydalanuvchi: @{message.from_user.username or message.from_user.first_name}"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ To‘g‘ri", callback_data=f"ok|{message.chat.id}"),
        types.InlineKeyboardButton("❌ Noto‘g‘ri", callback_data=f"no|{message.chat.id}")
    )

    bot.send_message(ADMIN_ID, text)
    for p in user_data['photos']:
        bot.send_photo(ADMIN_ID, p)
    bot.send_message(ADMIN_ID, "Quyidagi tanlovni bajaring 👇", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    action, user_id = call.data.split("|")
    if action == "ok":
        bot.send_message(int(user_id), "✅ Akkauntingiz tekshirildi va kanalga joylandi.")
        bot.send_message(
            CHANNEL_ID,
            f"🔗 Akkaunt: {call.message.text}\n🛒 Akkaunt sotib olish 💬",
        )
    else:
        bot.send_message(int(user_id), "❌ Ma’lumotlar xato. Iltimos, qayta urinib ko‘ring.")


# --- Flask server (Render uchun)
@app.route('/', methods=['GET'])
def home():
    return "OK", 200


@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
