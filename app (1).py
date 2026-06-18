import logging
import random
import string
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    BotCommand
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    PicklePersistence,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define States for Initial Registration Conversation
CHOOSING_EXAM, ASKING_AGE, ASKING_GENDER, ASKING_LOCATION = range(4)

# ==========================================
# HELPER FUNCTIONS (Tags & Keyboards)
# ==========================================
def get_main_keyboard(is_premium=False):
    limit_text = "💡 Daily chat limit: Unlimited" if is_premium else "💡 Daily chat limit: 100"
    keyboard = [
        [KeyboardButton("💬 Chat"), KeyboardButton("🔄 Re-Chat")],
        [KeyboardButton("⚙️ Settings"), KeyboardButton("💎 Premium")],
        [KeyboardButton("🎁 Send Gift"), KeyboardButton("ℹ️ About")],
        [KeyboardButton("❓ Help"), KeyboardButton(limit_text)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def get_or_create_tag(user_id, bot_data):
    if 'tags' not in bot_data:
        bot_data['tags'] = {}
        
    profile = bot_data['users'].get(user_id, {})
    tag = profile.get('tag')
    
    if not tag:
        while True:
            tag = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if tag not in bot_data['tags']:
                break
        bot_data['users'][user_id]['tag'] = tag
        bot_data['tags'][tag] = user_id
        
    return tag

# Setup Bot Commands Menu
async def setup_commands(application):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("chat", "Find a partner"),
        BotCommand("exit", "Leave current chat"),
        BotCommand("rechat", "Reconnect with last or specific partner 💎"),
        BotCommand("settings", "Manage profile"),
        BotCommand("premium", "Premium features"),
        BotCommand("delete", "Delete sent message 💎"),
        BotCommand("report", "Report user"),
        BotCommand("rules", "Community rules"),
        BotCommand("paysupport", "Payment support"),
        BotCommand("privacy", "Privacy policy"),
        BotCommand("help", "Show help menu")
    ]
    await application.bot.set_my_commands(commands)

# ==========================================
# 1. INITIAL REGISTRATION FLOW (/start)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    # Check if user already exists
    if 'users' in context.bot_data and user_id in context.bot_data['users']:
        profile = context.bot_data['users'][user_id]
        gender_display = profile.get('gender', 'Not Set') 
        my_tag = get_or_create_tag(user_id, context.bot_data)
        
        await update.message.reply_text(
            f"🌟 *Welcome back!*\n\n"
            f"💳 *ID TAG:* `{my_tag}`\n"
            f"📚 *Exam:* {profile['exam']}\n"
            f"🎂 *Age:* {profile['age']}\n"
            f"👥 *Gender:* {gender_display}\n"
            f"📍 *Location:* {profile['location']}\n\n"
            "Your profile is active. Use the menu below to navigate!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
        
    await update.message.reply_text(
        "Hey! Welcome to the ultimate aspirant meetup hub. 🚀\n"
        "Let's set up your profile to find your perfect match.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    keyboard = [
        [InlineKeyboardButton("🏛️ Civil Services (UPSC, UPPSC)", callback_data="exam_Civil Services")],
        [InlineKeyboardButton("🩺 Engg & Medical (JEE, NEET)", callback_data="exam_Engineering & Medical")],
        [InlineKeyboardButton("🪖 Defence Services (NDA, CDS)", callback_data="exam_Defence Services")],
        [InlineKeyboardButton("📋 SSC & Railways", callback_data="exam_SSC & Railways")],
        [InlineKeyboardButton("💰 Banking & Finance", callback_data="exam_Banking & Finance")],
        [InlineKeyboardButton("⚖️ Mgmt, Law (CAT, CLAT)", callback_data="exam_Management, Law & Commerce")],
        [InlineKeyboardButton("🎓 University Admissions (CUET)", callback_data="exam_University Admissions")],
        [InlineKeyboardButton("🏫 School Exams (10th/12th)", callback_data="exam_10th/12th Boards")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("First, select your primary exam category:", reply_markup=reply_markup)
    return CHOOSING_EXAM

async def exam_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["exam"] = query.data.replace("exam_", "")
    await query.edit_message_text(text=f"✅ Selected: *{context.user_data['exam']}*\n\nNow, please enter your age (e.g., 21):", parse_mode=ParseMode.MARKDOWN)
    return ASKING_AGE

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    age_input = update.message.text
    if not age_input.isdigit() or not (15 <= int(age_input) <= 40):
        await update.message.reply_text("Please enter a valid age between 15 and 40.")
        return ASKING_AGE
    context.user_data["age"] = age_input
    
    keyboard = [
        [InlineKeyboardButton("👨 Male", callback_data="gender_Male"), InlineKeyboardButton("👩 Female", callback_data="gender_Female")],
        [InlineKeyboardButton("🏳️‍🌈 Other", callback_data="gender_Other")]
    ]
    await update.message.reply_text("Great! Now, please select your gender:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ASKING_GENDER

async def ask_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["gender"] = query.data.replace("gender_", "")
    
    city_buttons = [
        [InlineKeyboardButton("📍 Delhi", callback_data="loc_Delhi"), InlineKeyboardButton("📍 Prayagraj", callback_data="loc_Prayagraj")],
        [InlineKeyboardButton("📍 Kota", callback_data="loc_Kota"), InlineKeyboardButton("📍 Patna", callback_data="loc_Patna")],
        [InlineKeyboardButton("📍 Hyderabad", callback_data="loc_Hyderabad"), InlineKeyboardButton("📍 Bengaluru", callback_data="loc_Bengaluru")],
        [InlineKeyboardButton("✍️ Other / Type My City", callback_data="loc_OTHER")]
    ]
    await query.edit_message_text(f"✅ Selected: {context.user_data['gender']}\n\nLast question: Which city are you preparing from?", reply_markup=InlineKeyboardMarkup(city_buttons))
    return ASKING_LOCATION

async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        loc_data = query.data.replace("loc_", "")
        if loc_data == "OTHER":
            await query.edit_message_text("Please type your city or state name directly below:")
            return ASKING_LOCATION
        context.user_data["location"] = loc_data
        await query.delete_message()
    else:
        context.user_data["location"] = update.message.text

    if 'users' not in context.bot_data:
        context.bot_data['users'] = {}
        
    context.bot_data['users'][user_id] = {
        "exam": context.user_data.get("exam"),
        "age": context.user_data.get("age"),
        "gender": context.user_data.get("gender"),
        "location": context.user_data.get("location")
    }
    
    # Generate permanent TAG for new user
    my_tag = get_or_create_tag(user_id, context.bot_data)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🎉 *Profile Setup Complete!* 🎉\nYour permanent ID is `{my_tag}`.\n\nUse the menu below to start chatting anonymously!", 
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Setup canceled. Type /start to try again!", reply_markup=get_main_keyboard())
    return ConversationHandler.END


# ==========================================
# 2. IN-CHAT SETTINGS GRID (/settings)
# ==========================================
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if 'users' not in context.bot_data or user_id not in context.bot_data['users']:
        await update.message.reply_text("You need to set up your profile first! Type /start")
        return
        
    keyboard = [
        [InlineKeyboardButton("📚 Change Exam", callback_data="set_edit_exam"), InlineKeyboardButton("🎂 Change Age", callback_data="set_edit_age")],
        [InlineKeyboardButton("👥 Change Gender", callback_data="set_edit_gender"), InlineKeyboardButton("📍 Change Location", callback_data="set_edit_loc")],
        [InlineKeyboardButton("❌ Close Settings", callback_data="set_close")]
    ]
    await update.message.reply_text(
        "⚙️ *Profile Settings*\nSelect what you want to change. *(This is hidden from your chat partner)*:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def settings_grid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "set_close":
        context.user_data['awaiting_setting'] = None
        await query.delete_message()
        return
        
    elif data == "set_edit_exam":
        keyboard = [
            [InlineKeyboardButton("Civil Services", callback_data="set_save_exam_Civil Services"), InlineKeyboardButton("Engg/Med", callback_data="set_save_exam_Engineering & Medical")],
            [InlineKeyboardButton("SSC/Railways", callback_data="set_save_exam_SSC & Railways"), InlineKeyboardButton("Banking", callback_data="set_save_exam_Banking & Finance")],
            [InlineKeyboardButton("School Boards", callback_data="set_save_exam_10th/12th Boards"), InlineKeyboardButton("Other", callback_data="set_save_exam_Other")]
        ]
        await query.edit_message_text("Select your new Exam Category:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif data == "set_edit_age":
        context.user_data['awaiting_setting'] = 'age'
        await query.edit_message_text("Please type your new age (e.g., 22):")
        
    elif data == "set_edit_gender":
        keyboard = [[InlineKeyboardButton("Male", callback_data="set_save_gen_Male"), InlineKeyboardButton("Female", callback_data="set_save_gen_Female"), InlineKeyboardButton("Other", callback_data="set_save_gen_Other")]]
        await query.edit_message_text("Select your new Gender:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif data == "set_edit_loc":
        context.user_data['awaiting_setting'] = 'location'
        await query.edit_message_text("Please type your new City or State name:")

async def settings_save_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("set_save_exam_"):
        new_val = data.replace("set_save_exam_", "")
        context.bot_data['users'][user_id]['exam'] = new_val
        await query.edit_message_text(f"✅ Exam successfully updated to: {new_val}")
        
    elif data.startswith("set_save_gen_"):
        new_val = data.replace("set_save_gen_", "")
        context.bot_data['users'][user_id]['gender'] = new_val
        await query.edit_message_text(f"✅ Gender successfully updated to: {new_val}")


# ==========================================
# 3. CHAT CONTROLS (/chat, /exit, /rechat)
# ==========================================
async def match_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if 'users' not in context.bot_data or user_id not in context.bot_data['users']:
        await update.message.reply_text("You need to set up your profile first! Type /start")
        return
    if 'matches' in context.bot_data and user_id in context.bot_data['matches']:
        await update.message.reply_text("You are already in a chat! Type /exit to leave your current chat first.")
        return

    if 'waiting_pool' not in context.bot_data:
        context.bot_data['waiting_pool'] = set()
        
    waiting_pool = context.bot_data['waiting_pool']
    if user_id in waiting_pool:
        await update.message.reply_text("⏳ You are already in the queue! We'll message you as soon as someone joins.")
        return
        
    available_users = [uid for uid in waiting_pool if uid != user_id]
    if not available_users:
        waiting_pool.add(user_id)
        await update.message.reply_text("🔍 Looking for an anonymous partner... \nAdded you to the queue! You'll be notified automatically.")
    else:
        partner_id = available_users[0]
        waiting_pool.remove(partner_id)
        
        if 'matches' not in context.bot_data:
            context.bot_data['matches'] = {}
            
        context.bot_data['matches'][user_id] = partner_id
        context.bot_data['matches'][partner_id] = user_id
        
        my_profile = context.bot_data['users'][user_id]
        partner_profile = context.bot_data['users'][partner_id]
        
        def get_match_text(profile):
            return (
                "🎊 <b>Match Found!</b> 🎊\n\n"
                f"📚 <b>Exam:</b> {profile['exam']}\n"
                f"🎂 <b>Age:</b> {profile['age']}\n"
                f"👥 <b>Gender:</b> <tg-spoiler>Available With Premium</tg-spoiler>\n"
                f"📍 <b>Location:</b> {profile['location']}\n\n"
                "<i>You can now say hi! Messages sent here will be delivered to your partner. Type /exit to leave.</i>"
            )
        
        try:
            await context.bot.send_message(chat_id=partner_id, text=get_match_text(my_profile), parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())
        except Exception:
            pass
        await update.message.reply_text(get_match_text(partner_profile), parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())

async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if 'waiting_pool' in context.bot_data and user_id in context.bot_data['waiting_pool']:
        context.bot_data['waiting_pool'].remove(user_id)
        await update.message.reply_text("You have left the matchmaking queue. Type /chat to rejoin.")
        return

    if 'matches' in context.bot_data and user_id in context.bot_data['matches']:
        partner_id = context.bot_data['matches'][user_id]
        partner_tag = get_or_create_tag(partner_id, context.bot_data)
        
        # Disconnect backend
        del context.bot_data['matches'][user_id]
        if partner_id in context.bot_data['matches']:
            del context.bot_data['matches'][partner_id]
            
            # Notify Partner
            my_tag = get_or_create_tag(user_id, context.bot_data)
            partner_exit_text = (
                "🚫 *Your partner left the chat*\n\n"
                "/chat - Find new partner\n"
                "━━━━━━━━━━━━━━━\n"
                f"⚠️ *Session TAG:* `{my_tag}`\n\n"
                f"To reconnect: `/rechat {my_tag}`\n"
                f"To report: `/report {my_tag}`"
            )
            partner_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⚠️ Report User", callback_data=f"rep_{my_tag}")]])
            try:
                await context.bot.send_message(chat_id=partner_id, text=partner_exit_text, parse_mode=ParseMode.MARKDOWN, reply_markup=partner_markup)
            except Exception:
                pass
                
        # Notify Self
        self_exit_text = (
            "🚫 *You left the chat*\n\n"
            "/chat - Find new partner\n"
            "━━━━━━━━━━━━━━━\n"
            f"⚠️ *Session TAG:* `{partner_tag}`\n\n"
            f"To reconnect: `/rechat {partner_tag}`\n"
            f"To report: `/report {partner_tag}`"
        )
        self_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⚠️ Report User", callback_data=f"rep_{partner_tag}")]])
        await update.message.reply_text(self_exit_text, parse_mode=ParseMode.MARKDOWN, reply_markup=self_markup)
    else:
        await update.message.reply_text("You are not currently in a chat.")

async def rechat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # If they passed a specific TAG (Premium Feature)
    if context.args:
        target_tag = context.args[0].upper()
        await update.message.reply_text(f"💎 *Premium Feature*\nDirectly reconnecting with TAG `{target_tag}` is available for Premium users only.", parse_mode=ParseMode.MARKDOWN)
        return
        
    # Standard Re-Chat (Disconnects and searches randomly)
    if 'matches' in context.bot_data and user_id in context.bot_data['matches']:
        await stop_chat(update, context)
    await match_user(update, context)


# ==========================================
# 4. UTILITY & NEW COMMANDS
# ==========================================
async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "💎 **StudiMeet Premium**\n\n"
        "• View partner's Gender instantly\n"
        "• Direct reconnect using `/rechat TAG`\n"
        "• Delete sent messages using `/delete`\n"
        "• Unlimited daily chats\n\n"
        "_Integration coming soon!_"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def send_gift(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if 'matches' in context.bot_data and user_id in context.bot_data['matches']:
        await update.message.reply_text("🎁 *Send a Gift!*\nSupport your chat partner by sending Telegram Stars. _(Payment gateway syncing...)_", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("You need to be in a chat to send a gift!")

async def delete_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("💎 *Premium Feature*\nUpgrade to Premium to un-send messages from your partner's screen!", parse_mode=ParseMode.MARKDOWN)

async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        target = context.args[0]
        await update.message.reply_text(f"✅ Report submitted for TAG `{target}`. Our team will review the chat logs.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("To report someone, use: `/report TAG`", parse_mode=ParseMode.MARKDOWN)

async def generic_text_responses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cmd = update.message.text.lower()
    if "/rules" in cmd:
        await update.message.reply_text("📜 *Rules*\n1. Be respectful.\n2. No spam/promotions.\n3. Keep prep discussions healthy.", parse_mode=ParseMode.MARKDOWN)
    elif "/privacy" in cmd:
        await update.message.reply_text("🔒 *Privacy*\nChats are anonymous. We do not share your real profile or Telegram link.")
    elif "/paysupport" in cmd:
        await update.message.reply_text("💳 *Support*\nFor payment issues, contact our admin team at @StudiMeetSupport.")
    elif "/about" in cmd or "ℹ️ about" in cmd:
        await update.message.reply_text("🎓 *StudiMeet*\nThe best anonymous peer-to-peer prep platform. Connect, chat, and crack it!")
    elif "/help" in cmd or "❓ help" in cmd:
        await update.message.reply_text("🛠 *Help Menu*\nUse `/chat` to find someone, and `/settings` to change your exam or location. To exit a chat safely, type `/exit`.")

async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Report Logged", show_alert=True)
    await query.edit_message_reply_markup(reply_markup=None) # Removes the button after clicking


# ==========================================
# 5. UNIVERSAL MESSAGE RELAY & INTERCEPTOR
# ==========================================
async def handle_general_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user_id = update.effective_user.id
    
    # Check if they tapped a Bottom Menu Button
    if text == "💬 Chat":
        await match_user(update, context)
        return
    elif text == "🔄 Re-Chat":
        await rechat_command(update, context)
        return
    elif text == "⚙️ Settings":
        await settings_command(update, context)
        return
    elif text == "💎 Premium":
        await premium_info(update, context)
        return
    elif text == "🎁 Send Gift":
        await send_gift(update, context)
        return
    elif text in ["ℹ️ About", "❓ Help"]:
        await generic_text_responses(update, context)
        return
    elif "Daily chat limit" in text:
        await update.message.reply_text("You have plenty of chats remaining today!")
        return

    # INTERCEPTOR: Settings Update
    awaiting = context.user_data.get('awaiting_setting')
    if awaiting:
        if awaiting == 'age':
            if not text.isdigit() or not (15 <= int(text) <= 40):
                await update.message.reply_text("Please enter a valid age between 15 and 40.")
                return
            context.bot_data['users'][user_id]['age'] = text
            context.user_data['awaiting_setting'] = None
            await update.message.reply_text(f"✅ Age successfully updated to: {text}")
            return 
            
        elif awaiting == 'location':
            context.bot_data['users'][user_id]['location'] = text
            context.user_data['awaiting_setting'] = None
            await update.message.reply_text(f"✅ Location successfully updated to: {text}")
            return 

    # NORMAL RELAY: Chat Partner
    if 'matches' in context.bot_data and user_id in context.bot_data['matches']:
        partner_id = context.bot_data['matches'][user_id]
        try:
            await context.bot.send_message(chat_id=partner_id, text=f"💬 {text}")
        except Exception:
            await stop_chat(update, context)
    else:
        await update.message.reply_text("You are not connected to anyone yet. Tap '💬 Chat' below to find a partner!", reply_markup=get_main_keyboard())


# ==========================================
# MAIN APP EXECUTION
# ==========================================
def main():
    BOT_TOKEN = "8850005240:AAEz-wOHm05-oqraeyO0rp9XETlko715tuU"
    my_persistence = PicklePersistence(filepath="bot_data.pickle")
    app = ApplicationBuilder().token(BOT_TOKEN).persistence(my_persistence).post_init(setup_commands).build()

    # Initial Setup Handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_EXAM: [CallbackQueryHandler(exam_choice)],
            ASKING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            ASKING_GENDER: [CallbackQueryHandler(ask_gender)],
            ASKING_LOCATION: [
                CallbackQueryHandler(ask_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_location)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="my_registration_conv",
        persistent=True 
    )

    app.add_handler(conv_handler)
    
    # Settings
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CallbackQueryHandler(settings_grid_callback, pattern="^set_edit_|^set_close"))
    app.add_handler(CallbackQueryHandler(settings_save_callback, pattern="^set_save_"))
    
    # Interaction Commands
    app.add_handler(CommandHandler("chat", match_user))
    app.add_handler(CommandHandler("exit", stop_chat))
    app.add_handler(CommandHandler("rechat", rechat_command))
    app.add_handler(CommandHandler("premium", premium_info))
    app.add_handler(CommandHandler("delete", delete_msg))
    
    # Utility Commands
    app.add_handler(CommandHandler("report", report_user))
    app.add_handler(CallbackQueryHandler(report_callback, pattern="^rep_"))
    app.add_handler(CommandHandler(["rules", "paysupport", "privacy", "help", "about"], generic_text_responses))
    
    # Universal Message Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_messages))

    print("StudiMeet Bot is running with the new V2 Interface...")
    app.run_polling()

if __name__ == "__main__":
    main()