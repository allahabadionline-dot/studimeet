import logging
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
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

# Define States for Conversation (Added ASKING_GENDER)
CHOOSING_EXAM, ASKING_AGE, ASKING_GENDER, ASKING_LOCATION = range(4)

# Setup Bot Commands Menu (Added settings to the toggle menu)
async def setup_commands(application):
    commands = [
        BotCommand("start", "Start Message"),
        BotCommand("chat", "Find new Partner"),
        BotCommand("exit", "Stop the conversation"),
        BotCommand("settings", "Change Profile Settings"),
        BotCommand("premium", "Search by Gender")
    ]
    await application.bot.set_my_commands(commands)

# 1. Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    # Check if user already has a profile
    if 'users' in context.bot_data and user_id in context.bot_data['users']:
        profile = context.bot_data['users'][user_id]
        
        # Backward compatibility in case old users don't have gender saved yet
        gender_display = profile.get('gender', 'Not Set') 
        
        await update.message.reply_text(
            f"Welcome back! 👋\n\n"
            f"📚 *Exam:* {profile['exam']}\n"
            f"🎂 *Age:* {profile['age']}\n"
            f"👥 *Gender:* {gender_display}\n"
            f"📍 *Location:* {profile['location']}\n\n"
            "Your profile is active. Type /chat to start matching, or /settings to update your profile!",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
        
    # First-time registration flow
    await update.message.reply_text(
        "Hey! Welcome to the ultimate aspirant meetup hub. 🚀\n"
        "Let's set up your profile to find your perfect match.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    keyboard = [
        [InlineKeyboardButton("🏛️ Civil Services (UPSC, UPPSC, BPSC)", callback_data="exam_Civil Services")],
        [InlineKeyboardButton("🩺 Engg & Medical (JEE, NEET, GATE)", callback_data="exam_Engineering & Medical")],
        [InlineKeyboardButton("🪖 Defence Services (NDA, CDS)", callback_data="exam_Defence Services")],
        [InlineKeyboardButton("📋 SSC & Railways (CGL, CHSL, RRB)", callback_data="exam_SSC & Railways")],
        [InlineKeyboardButton("💰 Banking & Finance (SBI, IBPS, RBI)", callback_data="exam_Banking & Finance")],
        [InlineKeyboardButton("⚖️ Mgmt, Law & Commerce (CAT, CLAT, CA)", callback_data="exam_Management, Law & Commerce")],
        [InlineKeyboardButton("🎓 University Admissions (CUET UG)", callback_data="exam_University Admissions")],
        [InlineKeyboardButton("🏫 School Exams (10th / 12th Boards)", callback_data="exam_10th/12th Boards")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("First, select your primary exam category:", reply_markup=reply_markup)
    return CHOOSING_EXAM

# 1.5. Settings Command (Forces Profile Update)
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    # Remove user from waiting pool if they are in it
    if 'waiting_pool' in context.bot_data and user_id in context.bot_data['waiting_pool']:
        context.bot_data['waiting_pool'].remove(user_id)
        
    # Disconnect active chat if they have one
    if 'matches' in context.bot_data and user_id in context.bot_data['matches']:
        partner_id = context.bot_data['matches'][user_id]
        del context.bot_data['matches'][user_id]
        if partner_id in context.bot_data['matches']:
            del context.bot_data['matches'][partner_id]
            try:
                await context.bot.send_message(chat_id=partner_id, text="⚠️ *Your partner left to update their settings.* Type /chat to find someone new.", parse_mode=ParseMode.MARKDOWN)
            except Exception:
                pass

    keyboard = [
        [InlineKeyboardButton("🏛️ Civil Services (UPSC, UPPSC, BPSC)", callback_data="exam_Civil Services")],
        [InlineKeyboardButton("🩺 Engg & Medical (JEE, NEET, GATE)", callback_data="exam_Engineering & Medical")],
        [InlineKeyboardButton("🪖 Defence Services (NDA, CDS)", callback_data="exam_Defence Services")],
        [InlineKeyboardButton("📋 SSC & Railways (CGL, CHSL, RRB)", callback_data="exam_SSC & Railways")],
        [InlineKeyboardButton("💰 Banking & Finance (SBI, IBPS, RBI)", callback_data="exam_Banking & Finance")],
        [InlineKeyboardButton("⚖️ Mgmt, Law & Commerce (CAT, CLAT, CA)", callback_data="exam_Management, Law & Commerce")],
        [InlineKeyboardButton("🎓 University Admissions (CUET UG)", callback_data="exam_University Admissions")],
        [InlineKeyboardButton("🏫 School Exams (10th / 12th Boards)", callback_data="exam_10th/12th Boards")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("⚙️ *Profile Settings*\n\nLet's update your info. First, select your new exam category:", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    return CHOOSING_EXAM

# 2. Handle Exam Choice
async def exam_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    chosen_exam = query.data.replace("exam_", "")
    context.user_data["exam"] = chosen_exam
    
    await query.edit_message_text(
        text=f"✅ Selected: *{chosen_exam}*\n\nNow, please enter your age (e.g., 21):",
        parse_mode=ParseMode.MARKDOWN
    )
    return ASKING_AGE

# 3. Handle Age Input & Ask Gender
async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    age_input = update.message.text
    
    if not age_input.isdigit() or not (15 <= int(age_input) <= 40):
        await update.message.reply_text("Please enter a valid age between 15 and 40.")
        return ASKING_AGE
        
    context.user_data["age"] = age_input
    
    # NEW: Ask for Gender
    keyboard = [
        [InlineKeyboardButton("👨 Male", callback_data="gender_Male")],
        [InlineKeyboardButton("👩 Female", callback_data="gender_Female")],
        [InlineKeyboardButton("🏳️‍🌈 Other", callback_data="gender_Other")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Great! Now, please select your gender:", reply_markup=reply_markup)
    return ASKING_GENDER

# 4. Handle Gender Input & Ask Location
async def ask_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    chosen_gender = query.data.replace("gender_", "")
    context.user_data["gender"] = chosen_gender
    
    city_buttons = [
        [InlineKeyboardButton("📍 Delhi / NCR", callback_data="loc_Delhi"), InlineKeyboardButton("📍 Prayagraj", callback_data="loc_Prayagraj")],
        [InlineKeyboardButton("📍 Kota", callback_data="loc_Kota"), InlineKeyboardButton("📍 Patna", callback_data="loc_Patna")],
        [InlineKeyboardButton("📍 Hyderabad", callback_data="loc_Hyderabad"), InlineKeyboardButton("📍 Bengaluru", callback_data="loc_Bengaluru")],
        [InlineKeyboardButton("📍 Jaipur", callback_data="loc_Jaipur"), InlineKeyboardButton("📍 Lucknow", callback_data="loc_Lucknow")],
        [InlineKeyboardButton("📍 Indore", callback_data="loc_Indore"), InlineKeyboardButton("📍 Pune", callback_data="loc_Pune")],
        [InlineKeyboardButton("📍 Chennai", callback_data="loc_Chennai"), InlineKeyboardButton("📍 Kolkata", callback_data="loc_Kolkata")],
        [InlineKeyboardButton("📍 Mumbai", callback_data="loc_Mumbai"), InlineKeyboardButton("📍 Chandigarh", callback_data="loc_Chandigarh")],
        [InlineKeyboardButton("📍 Guwahati", callback_data="loc_Guwahati"), InlineKeyboardButton("📍 Ranchi", callback_data="loc_Ranchi")],
        [InlineKeyboardButton("📍 Bhopal", callback_data="loc_Bhopal"), InlineKeyboardButton("📍 Dehradun", callback_data="loc_Dehradun")],
        [InlineKeyboardButton("📍 Ahmedabad", callback_data="loc_Ahmedabad"), InlineKeyboardButton("📍 Varanasi", callback_data="loc_Varanasi")],
        [InlineKeyboardButton("✍️ Other / Type My City Manually", callback_data="loc_OTHER")]
    ]
    reply_markup = InlineKeyboardMarkup(city_buttons)
    
    await query.edit_message_text(
        text=f"✅ Selected: {chosen_gender}\n\nAwesome! Last question: Which city or state are you currently preparing from?",
        reply_markup=reply_markup
    )
    return ASKING_LOCATION

# 5. Handle Location & Save Profile
async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        location_data = query.data.replace("loc_", "")
        
        if location_data == "OTHER":
            await query.edit_message_text("Please type your city or state name directly in the chat below:")
            return ASKING_LOCATION
            
        context.user_data["location"] = location_data
        await query.delete_message()
    else:
        context.user_data["location"] = update.message.text

    # Gather data
    exam = context.user_data.get("exam")
    age = context.user_data.get("age")
    gender = context.user_data.get("gender")
    location = context.user_data.get("location")
    
    if 'users' not in context.bot_data:
        context.bot_data['users'] = {}
        
    # Save to permanent memory
    context.bot_data['users'][user_id] = {
        "exam": exam,
        "age": age,
        "gender": gender,
        "location": location
    }
    
    summary_text = (
        "🎉 *Profile Setup Complete!* 🎉\n\n"
        "Your profile is now live. Use the menu or type /chat to start chatting anonymously!"
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=summary_text, 
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

# Cancel Command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Profile setup canceled. Type /start whenever you want to try again!")
    return ConversationHandler.END

# 6. Stop/Exit Chat Logic (/exit)
async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if 'waiting_pool' in context.bot_data and user_id in context.bot_data['waiting_pool']:
        context.bot_data['waiting_pool'].remove(user_id)
        await update.message.reply_text("You have left the matchmaking queue. Type /chat to rejoin.")
        return

    if 'matches' in context.bot_data and user_id in context.bot_data['matches']:
        partner_id = context.bot_data['matches'][user_id]
        
        if user_id in context.bot_data['matches']:
            del context.bot_data['matches'][user_id]
        if partner_id in context.bot_data['matches']:
            del context.bot_data['matches'][partner_id]
            
        try:
            await context.bot.send_message(chat_id=partner_id, text="⚠️ *Your partner has disconnected.* Type /chat to find someone new.", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
            
        await update.message.reply_text("🛑 *You ended the conversation.* Type /chat to find someone new.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("You are not currently in a chat.")

# 7. Anonymous Matchmaking Logic (/chat)
async def match_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if 'users' not in context.bot_data or user_id not in context.bot_data['users']:
        await update.message.reply_text("You need to set up your profile first! Please type /start")
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
            await context.bot.send_message(
                chat_id=partner_id,
                text=get_match_text(my_profile),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        
        await update.message.reply_text(
            get_match_text(partner_profile),
            parse_mode=ParseMode.HTML
        )

# 8. Premium Command
async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("💎 **Premium Features:**\n- View partner's Gender instantly.\n- Filter by exam or location.\n- Priority matching.\n\n_Coming soon!_", parse_mode=ParseMode.MARKDOWN)

# 9. General Message Handler (Relay)
async def handle_general_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user_id = update.effective_user.id

    # Handle Anonymous Chat Relay
    if 'matches' in context.bot_data and user_id in context.bot_data['matches']:
        partner_id = context.bot_data['matches'][user_id]
        try:
            await context.bot.send_message(chat_id=partner_id, text=f"💬 {text}")
        except Exception:
            await stop_chat(update, context)
    else:
        await update.message.reply_text("You are not connected to anyone yet. Type /chat to find a partner!")

# Main Execution block
def main():
    BOT_TOKEN = "8850005240:AAEz-wOHm05-oqraeyO0rp9XETlko715tuU"
    
    # Permanent Storage
    my_persistence = PicklePersistence(filepath="bot_data.pickle")
    
    app = ApplicationBuilder().token(BOT_TOKEN).persistence(my_persistence).post_init(setup_commands).build()

    # Conversation Handler updated with /settings entry point and ASKING_GENDER state
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("settings", settings)
        ],
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
    
    app.add_handler(CommandHandler("chat", match_user))
    app.add_handler(CommandHandler("exit", stop_chat))
    app.add_handler(CommandHandler("premium", premium_info))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_messages))

    print("StudiMeet Bot is running with permanent disk memory...")
    app.run_polling()

if __name__ == "__main__":
    main()
