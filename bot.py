import telebot
import os
import time
import uuid
from telebot import types
from flask import Flask
from threading import Thread
from pymongo import MongoClient

# --- CONFIGURATION ---
BOT_TOKEN = "8761465405:AAEtsT_AnDuClMihQlj3hYjVmzR_ZwGvMaY"
ADMINS = [6450490197, 7520591656]
OWNER_HANDLE = "@Ayush20443"

# --- MONGODB CLOUD SETUP ---
MONGO_URI = "mongodb+srv://aayushkumar20443_db_user:yvej53e2@tgbot.20bdvy0.mongodb.net/?retryWrites=true&w=majority"

CHANNELS = ["@black_bulles", "@DARKSTOREAURA", "@MyDressUpDarlingTamilll", "@+f3wLucRJlnlmYWNl", "@SenjiLooters", "@arshxproofs"]

bot = telebot.TeleBot(BOT_TOKEN)

client = MongoClient(MONGO_URI)
db_mongo = client["LuxuryBotDB"]
collection = db_mongo["MainData"]

# --- FLASK SERVER SETUP (For Render) ---
server = Flask(__name__)

@server.route('/')
def home():
    return "Luxury Bot is running 24/7 on Render with MongoDB!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)

# Temporary memory for handling long file IDs
TEMP_MEDIA = {}

# --- DATABASE LOGIC (Cloud Based) ---
def load_db():
    data = collection.find_one({"_id": "main_db"})
    if not data:
        data = {"_id": "main_db", "users": {}, "free_videos": [], "luxury_videos": []}
        collection.insert_one(data)
    
    if "free_videos" not in data: data["free_videos"] = []
    if "luxury_videos" not in data: data["luxury_videos"] = []
    return data

def save_db(data):
    collection.update_one({"_id": "main_db"}, {"$set": data}, upsert=True)

# --- JOIN CHECKER ---
def is_user_joined(user_id):
    for channel in CHANNELS:
        try:
            if "+" in channel: continue
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked']: return False
        except: continue
    return True

# --- MEDIA SENDER HELPER ---
def send_media(chat_id, item):
    try:
        if item['type'] == 'video': bot.send_video(chat_id, item['id'])
        elif item['type'] == 'photo': bot.send_photo(chat_id, item['id'])
        elif item['type'] == 'document': bot.send_document(chat_id, item['id'])
        elif item['type'] == 'animation': bot.send_animation(chat_id, item['id'])
    except Exception as e:
        print(f"Error sending media: {e}")

# --- ADMIN MEDIA HANDLER ---
@bot.message_handler(content_types=['video', 'photo', 'document', 'animation'])
def handle_admin_media(message):
    if message.from_user.id in ADMINS:
        file_id = None
        m_type = None

        if message.video: file_id, m_type = message.video.file_id, "video"
        elif message.photo: file_id, m_type = message.photo[-1].file_id, "photo"
        elif message.document: file_id, m_type = message.document.file_id, "document"
        elif message.animation: file_id, m_type = message.animation.file_id, "animation"

        if file_id:
            short_id = str(uuid.uuid4())[:8]
            TEMP_MEDIA[short_id] = {"id": file_id, "type": m_type}

            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("Save as FREE 🎞️", callback_data=f"sf_{short_id}"),
                types.InlineKeyboardButton("Save as LUXURY 💎", callback_data=f"sl_{short_id}")
            )
            bot.reply_to(message, "✅ Media Detected! Kahan save karun?", reply_markup=markup)

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = str(message.from_user.id)
    db = load_db()
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_by = args[1]
        if user_id not in db["users"] and ref_by != user_id:
            if ref_by in db["users"]:
                db["users"][ref_by]["ref_count"] += 1
                try: bot.send_message(int(ref_by), "🎊 **New Referral!** Points added.")
                except: pass

    if user_id not in db["users"]:
        db["users"][user_id] = {"ref_count": 0, "name": message.from_user.first_name, "last_used": time.time()}
    else:
        db["users"][user_id]["last_used"] = time.time()
    save_db(db)

    if not is_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup(row_width=2)
        btns = [types.InlineKeyboardButton(f"Channel {i+1} ✨", url=f"https://t.me/{c[1:]}" if "@" in c else f"https://t.me/{c}") for i, c in enumerate(CHANNELS)]
        markup.add(*btns)
        markup.row(types.InlineKeyboardButton("✅ Joined", callback_data="verify_join"))
        bot.send_message(message.chat.id, "┏━━━━━━━━━━━━━━━━━━┓\n   ⚠️ ACCESS RESTRICTED\n┗━━━━━━━━━━━━━━━━━━┛", reply_markup=markup)
    else:
        send_main_menu(message.chat.id, message.from_user.first_name)

def send_main_menu(chat_id, name):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🎞️ GET VIDEO (Free)", callback_data="get_free"))
    markup.row(types.InlineKeyboardButton("💎 LUXURY VIDEO (1 Ref)", callback_data="get_luxury"))
    markup.row(types.InlineKeyboardButton("📊 MY STATS", callback_data="my_stats"))
    bot.send_message(chat_id, f"┏━━━━━━━━━━━━━━━━━━┓\n   ♛ WELCOME, {name.upper()}\n┗━━━━━━━━━━━━━━━━━━┛\n\n👤 Owner: {OWNER_HANDLE}", reply_markup=markup)

# --- CALLBACK HANDLER ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = str(call.from_user.id)
    db = load_db()

    if call.data == "verify_join":
        if is_user_joined(call.from_user.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_main_menu(call.message.chat.id, call.from_user.first_name)
        else: bot.answer_callback_query(call.id, "❌ Join all channels!", show_alert=True)

    elif call.data.startswith(("sf_", "sl_")):
        data = call.data.split("_")
        prefix = data[0]
        short_id = data[1]

        if short_id not in TEMP_MEDIA:
            bot.answer_callback_query(call.id, "⚠️ Error: Session expired. Resend the media.", show_alert=True)
            return

        media_info = TEMP_MEDIA[short_id]
        target = "free_videos" if prefix == "sf" else "luxury_videos"
        db[target].append(media_info)
        save_db(db)
        
        del TEMP_MEDIA[short_id]
        bot.edit_message_text(f"✅ Saved permanently to MongoDB in {target.split('_')[0].upper()} category!", call.message.chat.id, call.message.message_id)

    elif call.data == "get_free":
        if db["free_videos"]:
            bot.answer_callback_query(call.id, "Sending free content...")
            for item in db["free_videos"]: send_media(call.message.chat.id, item)
        else: bot.answer_callback_query(call.id, "No free content!", show_alert=True)

    elif call.data == "get_luxury":
        count = db["users"].get(user_id, {}).get("ref_count", 0)
        if count >= 1:
            if db["luxury_videos"]:
                bot.answer_callback_query(call.id, "Sending luxury content! 💎")
                for item in db["luxury_videos"]: send_media(call.message.chat.id, item)
            else: bot.send_message(call.message.chat.id, "No luxury content yet!")
        else:
            bot_me = bot.get_me().username
            bot.send_message(call.message.chat.id, f"🔐 LOCKED! 1 Referral needed.\n🔗 Invite Link: `https://t.me/{bot_me}?start={user_id}`")

    elif call.data == "my_stats":
        count = db["users"].get(user_id, {}).get("ref_count", 0)
        bot.answer_callback_query(call.id, f"Your Referrals: {count} 💎", show_alert=True)

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.from_user.id in ADMINS:
        db = load_db()
        active = sum(1 for u in db["users"].values() if time.time() - u.get("last_used", 0) <= 86400)
        bot.reply_to(message, f"📊 **Stats:**\nTotal Users: {len(db['users'])}\nActive 24h: {active}")

if __name__ == "__main__":
    print("Starting Flask Server...")
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    print("Bot is LIVE with MongoDB Backup...")
    bot.infinity_polling()
