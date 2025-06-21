# --- Migrated to python-telegram-bot v21.0.1 ---

import os
import logging
import requests
import datetime
import json
import time
import asyncio
import io

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# --- Setup for Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration: Your Secret Keys ---
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
HF_API_KEY = os.environ.get("HF_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable not set. Please set it in Replit Secrets.")
    exit(1)
if not HF_API_KEY:
    logger.error("HF_API_KEY environment variable not set. Please set it in Replit Secrets.")
    exit(1)

# --- Smart Tagging Service Settings (Hugging Face Inference API) ---
HUGGING_FACE_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

POTENTIAL_TAGS = [
    "philosophy", "motivation", "productivity", "history", "science", "psychology",
    "self-improvement", "business", "fiction", "art", "nature", "spirituality",
    "learning", "wisdom", "courage", "mindfulness", "health", "relationships",
    "technology", "creativity", "writing", "reading", "future", "past", "present",
    "emotions", "happiness", "sadness", "joy", "anger", "fear", "love", "friendship",
    "family", "society", "politics", "economy", "environment", "travel", "culture",
    "food", "exercise", "sleep", "meditation", "habit", "discipline", "focus"
]

# --- Replit DB Persistence ---
from replit import db

# Functions to load and save data from Replit DB (These are unchanged)
def load_data_from_db():
    global user_highlights, user_preferences, reminder_state
    if "user_highlights" in db:
        try:
            user_highlights = json.loads(db["user_highlights"])
            logger.info("Loaded user_highlights from DB.")
        except json.JSONDecodeError:
            logger.error("Failed to decode user_highlights from DB. Initializing empty.")
            user_highlights = {}
    else:
        user_highlights = {}
        logger.info("No user_highlights found in DB. Initializing empty.")

    if "user_preferences" in db:
        try:
            user_preferences = json.loads(db["user_preferences"])
            logger.info("Loaded user_preferences from DB.")
        except json.JSONDecodeError:
            logger.error("Failed to decode user_preferences from DB. Initializing empty.")
            user_preferences = {}
    else:
        user_preferences = {}
        logger.info("No user_preferences found in DB. Initializing empty.")

    if "reminder_state" in db:
        try:
            reminder_state = json.loads(db["reminder_state"])
            logger.info("Loaded reminder_state from DB.")
        except json.JSONDecodeError:
            logger.error("Failed to decode reminder_state from DB. Initializing empty.")
            reminder_state = {"last_sent_time": {}, "phrase_index": {}}
    else:
        reminder_state = {"last_sent_time": {}, "phrase_index": {}}
        logger.info("No reminder_state found in DB. Initializing empty.")

def save_data_to_db():
    try:
        db["user_highlights"] = json.dumps(user_highlights)
        db["user_preferences"] = json.dumps(user_preferences)
        db["reminder_state"] = json.dumps(reminder_state)
        logger.info("Data saved to Replit DB.")
    except Exception as e:
        logger.error(f"Error saving to DB: {e}")

# Initialize variables and load from DB
user_highlights = {}
user_preferences = {}
reminder_state = {"last_sent_time": {}, "phrase_index": {}}
load_data_from_db()

# --- Conversation Flow Steps ---
UPLOAD_HIGHLIGHTS, SELECT_TOPICS = range(2)

# --- Weekly Reminder Phrases (Unchanged) ---
WEEKLY_REMINDERS = [
    "Hey there, wisdom seeker! Your weekly dose of brain candy is ready. Dive in with /wisdom!",
    "Knock knock, who's there? It's your weekly reminder to check out your latest nuggets! Type /wisdom.",
    "Don't let your insights gather dust! Your fresh wisdom awaits. Hit /wisdom for a refresh.",
    "Feeling a little... un-nuggeted? Your weekly wisdom top-up is here. Just /wisdom away!",
    "Your brain called, it wants its weekly wisdom. Answer with /wisdom!",
    "Time to unwrap some mental treats! Your wisdom nuggets are fresh and ready. Type /wisdom.",
    "Shake off the Monday blues with a dose of brilliance! Your weekly wisdom is hot off the press. Try /wisdom.",
    "Curiosity is calling! Your weekly dive into your highlights is here. Don't forget to /wisdom.",
    "What's smarter than a smart cookie? You, after checking your weekly wisdom! Get it with /wisdom.",
    "Ding dong! Your weekly wisdom delivery has arrived. Go on, open it with /wisdom.",
    "Ready for an 'aha!' moment? Your personalized wisdom nuggets are just a /wisdom away.",
    "Your secret weapon for a smarter week? Your highlight wisdom! Access it with /wisdom.",
    "Before the week gets wild, grab your wisdom shield! Your nuggets await with /wisdom.",
    "Level up your mind! Your weekly wisdom boost is here. Tap /wisdom to begin.",
    "Your brain's personal trainer says: 'Time for your weekly wisdom workout!' Send /wisdom.",
    "Don't just scroll, grow! Your weekly wisdom reminder is here. Discover with /wisdom.",
    "A week without wisdom is like... well, you know. Get your fix with /wisdom!",
    "Your weekly reminder: You're brilliant, and your highlights prove it! Check them with /wisdom.",
    "The oracle of your Kindle has spoken! Your weekly wisdom is ready. Say /wisdom.",
    "Unlock new perspectives! Your weekly wisdom gems are polished and waiting. Use /wisdom.",
    "Hey! Just a little nudge. Your wisdom insights are eager to be revisited. Send /wisdom.",
    "This message is a sign: It's wisdom o'clock! Get your weekly knowledge drop with /wisdom.",
    "Got 30 seconds? That's all it takes for a wisdom spark! Your weekly nuggets await. Try /wisdom.",
    "The week's big question: Have you claimed your wisdom yet? It's here with /wisdom.",
    "Your personalized wisdom playlist is refreshed! Hit play with /wisdom.",
    "Feeling philosophical? Or just need a good thought? Your weekly highlights are ready. Use /wisdom.",
    "Don't forget the brilliance you've collected! Your weekly reminder to revisit. Type /wisdom.",
    "Your brain's weekly pick-me-up: fresh wisdom nuggets! Claim yours with /wisdom.",
    "Let's get smart! Your weekly reminder to dive into your personal insights. Send /wisdom.",
    "The secret to a thoughtful week? Your highlights! Grab your weekly dose with /wisdom.",
    "Your weekly wisdom alert! Prepare for some delightful mental food. Just /wisdom.",
    "It's like a treasure hunt, but the treasure is knowledge! Your weekly nuggets are hidden behind /wisdom.",
    "Your future self will thank you for this weekly wisdom check. Go on, /wisdom.",
    "Mind matters! And so do your highlights. Get your weekly intellectual boost with /wisdom.",
    "Don't leave your insights hanging! They want to be seen. Your weekly reminder to /wisdom.",
    "Your personal library is calling! Weekly wisdom updates available. Type /wisdom.",
    "Make this week smarter than the last! Your weekly wisdom nudge is here. Send /wisdom.",
    "A little spark of insight to brighten your week! Your nuggets are ready. Go /wisdom.",
    "Did you know you have a wisdom superpower? Unleash it weekly with /wisdom!",
    "It's a beautiful day for some beautiful thoughts! Your weekly highlights await. Use /wisdom.",
    "Your knowledge garden needs watering! Nurture it with your weekly wisdom from /wisdom.",
    "The best kind of re-run: your brilliant highlights! Your weekly reminder to /wisdom.",
    "Stop, think, grow! Your weekly wisdom reminder. Find your nuggets with /wisdom.",
    "Your brain's favorite day? When it gets new wisdom! Your weekly update is here. Tap /wisdom.",
    "Curate your brilliance! Your weekly reminder to explore your highlights. Send /wisdom.",
    "Get ready for some mental fireworks! Your weekly wisdom nuggets are charged. Try /wisdom.",
    "Unlock the genius within your reads! Your weekly wisdom is calling. Pick it up with /wisdom.",
    "Your personal insight engine is revving up! Get your weekly thoughts with /wisdom."
]

# --- Helper Function: API calling (Unchanged) ---
def call_api_with_retry(text_to_analyze, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            payload = {
                "inputs": text_to_analyze,
                "parameters": {"candidate_labels": POTENTIAL_TAGS, "multi_label": True}
            }
            response = requests.post(HUGGING_FACE_API_URL, headers=HEADERS, json=payload, timeout=30)

            if response.status_code == 429:
                wait_time = base_delay * (2 ** attempt) + 1
                logger.warning(f"Rate limited, waiting {wait_time} seconds before retry {attempt + 1}")
                time.sleep(wait_time)
                continue
            elif response.status_code == 503:
                wait_time = base_delay * (2 ** attempt) + 2
                logger.warning(f"Service unavailable, waiting {wait_time} seconds before retry {attempt + 1}")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            result = response.json()

            if 'labels' in result and 'scores' in result:
                tags = [
                    label.lower() for label, score in zip(result['labels'], result['scores'])
                    if score > 0.5
                ]
                return tags if tags else ["untagged"]
            else:
                logger.warning(f"Unexpected API response format: {result}")
                return ["untagged", "api-format-error"]

        except requests.exceptions.Timeout:
            logger.warning(f"API timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
                continue
        except requests.exceptions.RequestException as e:
            logger.warning(f"API error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
                continue
        except Exception as e:
            logger.error(f"Unexpected error calling API: {e}")
            break

    logger.error(f"Failed to get tags after {max_retries} attempts")
    return ["untagged", "api-error"]

# --- Helper Function: Semantic tagging (Unchanged) ---
def get_fast_meaning_tags(text_to_analyze):
    text_lower = text_to_analyze.lower()
    found_tags = []
    concept_patterns = {
        "philosophy": ["philosophy", "philosophical", "wisdom", "truth", "meaning", "existence", "reality", "purpose of life", "human condition", "moral", "ethics", "virtue", "contemplat", "profound", "deeper understanding", "fundamental question", "nature of", "essence of", "universal principle", "timeless", "ancient wisdom", "enlighten", "conscious living"],
        "motivation": ["motivation", "inspire", "dream", "goal", "ambition", "success", "achieve", "push yourself", "never give up", "persist", "determination", "drive", "passion", "overcome obstacles", "reach potential", "strive", "excellence", "breakthrough", "transform", "rise above", "inner strength", "willpower", "dedication"],
        "happiness": ["happy", "joy", "smile", "positive", "optimism", "content", "cheerful", "fulfillment", "satisfaction", "bliss", "delight", "pleasure", "gratitude", "inner peace", "serenity", "radiant", "glow", "light up", "uplift", "celebrate", "appreciate", "thankful", "blessed", "flourish", "thrive", "well-being", "harmony", "balance", "laugh", "brightens"],
        "wisdom": ["wisdom", "wise", "insight", "understanding", "knowledge", "learn", "life lesson", "experience taught", "realize", "discover", "revelation", "profound truth", "deep understanding", "perspective", "clarity", "awareness", "growth", "maturity", "reflection", "contemplate", "ponder", "epiphany"],
        "relationships": ["relationship", "friend", "family", "love", "trust", "communication", "marriage", "connection", "bond", "intimacy", "companionship", "partnership", "loyalty", "understanding", "support", "care", "affection", "devotion", "commitment", "empathy", "compassion", "togetherness", "unity", "belonging", "acceptance"],
        "courage": ["courage", "brave", "bold", "confident", "strength", "fearless", "face your fears", "take risks", "step outside comfort zone", "dare to", "overcome fear", "stand up", "resilience", "perseverance", "determination", "inner strength", "backbone", "grit", "tenacity", "fortitude", "valor"],
        "mindfulness": ["mindful", "present", "awareness", "meditation", "conscious", "attention", "in the moment", "here and now", "pay attention", "observe", "notice", "breathe", "stillness", "quiet mind", "centered", "grounded", "focus", "presence", "being present", "mindful living", "inner calm"],
        "self-improvement": ["improve", "better", "growth", "develop", "change", "habit", "skill", "personal development", "self-discovery", "transform", "evolve", "progress", "better version", "upgrade", "enhance", "refine", "polish", "cultivate", "discipline", "practice", "mastery", "potential", "becoming", "journey"],
        "creativity": ["creative", "art", "design", "innovation", "imagination", "original", "inspire", "think outside the box", "new perspective", "innovative", "inventive", "artistic", "expressive", "unique", "novel", "fresh", "breakthrough", "vision", "create", "craft", "compose", "generate", "conceive"],
        "productivity": ["productivity", "efficient", "time", "work", "focus", "organize", "system", "get things done", "optimize", "streamline", "effective", "results", "accomplish", "output", "performance", "workflow", "method", "strategy", "priority", "task", "goal-oriented", "systematic", "structured"],
        "learning": ["learn", "education", "knowledge", "study", "understand", "skill", "teach", "acquire knowledge", "gain insight", "comprehend", "grasp", "absorb", "intellectual", "curiosity", "explore ideas", "mental growth", "scholarship", "enlightenment", "discovery", "research", "investigation", "inquiry"],
        "emotions": ["emotion", "feel", "feeling", "mood", "sentiment", "emotional", "heart", "soul", "passion", "intensity", "deep feeling", "stirring", "moving", "touching", "powerful", "overwhelming", "surge", "waves of", "flood of", "rush of", "emotional response"],
        "spirituality": ["spiritual", "soul", "faith", "belief", "meditation", "prayer", "divine", "higher power", "transcendent", "sacred", "holy", "blessed", "grace", "inner peace", "enlightenment", "awakening", "consciousness", "universe", "purpose", "calling", "devotion", "reverence", "worship", "sanctuary"]
    }
    for tag, patterns in concept_patterns.items():
        for pattern in patterns:
            if pattern in text_lower:
                found_tags.append(tag)
                break
    found_tags = list(dict.fromkeys(found_tags))
    if found_tags:
        return found_tags
    else:
        return call_api_with_retry(text_to_analyze)

# --- Helper Functions (Unchanged) ---
def parse_highlights(text):
    highlights = []
    current_highlight_lines = []
    metadata_markers = ["==========", "- Your Highlight on page", "- Highlight Loc.", "- Note Loc."]
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or any(marker in line for marker in metadata_markers):
            if current_highlight_lines:
                highlight_text = " ".join(current_highlight_lines).strip()
                if highlight_text and not all(any(marker in h_line for marker in metadata_markers) for h_line in current_highlight_lines):
                    if len(highlight_text) > 10:
                        highlights.append(highlight_text)
                current_highlight_lines = []
            continue
        current_highlight_lines.append(line)
    if current_highlight_lines:
        highlight_text = " ".join(current_highlight_lines).strip()
        if highlight_text and not all(any(marker in h_line for marker in metadata_markers) for h_line in current_highlight_lines):
            if len(highlight_text) > 10:
                highlights.append(highlight_text)
    return highlights

def get_unique_tags(highlights_dict):
    all_tags = set()
    for tags_list in highlights_dict.values():
        for tag in tags_list:
            all_tags.add(tag)
    return sorted(list(all_tags))

def get_wisdom_nugget(chat_id):
    chat_id_str = str(chat_id)
    user_prefs = user_preferences.get(chat_id_str, [])
    available_highlights = user_highlights.get(chat_id_str, {})
    if not available_highlights:
        return "You haven't uploaded any highlights yet! Use /upload to get started."
    filtered_highlights = []
    if user_prefs:
        for highlight, tags in available_highlights.items():
            if any(pref_tag in tags for pref_tag in user_prefs):
                filtered_highlights.append(highlight)
    else:
        filtered_highlights = list(available_highlights.keys())
    if filtered_highlights:
        import random
        selected_nugget = random.choice(filtered_highlights)
        tags_for_nugget = available_highlights[selected_nugget]
        tag_string = " ".join([f"#{t}" for t in tags_for_nugget])
        return f"{selected_nugget}\n\nTags: {tag_string}"
    else:
        return "No highlights found for your selected topics. Try selecting more topics or uploading more highlights!"

# --- Bot Command Handlers (Now async) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"Hello {user.mention_html()}! Welcome to your Kindle Wisdom Bot.\n\n"
        "I can help you extract wisdom from your Kindle highlights, **automatically categorize them by meaning**, "
        "and send you personalized wisdom nuggets anytime you want. Your highlights are now saved permanently! "
        "I can also send you fun weekly reminders!\n\n"
        "To get started, use /upload to send me your Kindle highlights file (.txt)."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Here are the commands you can use:\n\n"
        "/start - Start interacting with the bot.\n"
        "/upload - Send me your Kindle highlights file (.txt) for smart tagging.\n"
        "/topics - Change your preferred topics (hashtags).\n"
        "/wisdom - Get a random wisdom nugget right now (as many times as you like!).\n"
        "/reminders - Control weekly wisdom reminders.\n"
        "/help - Show this help message."
    )

async def send_wisdom_nugget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    wisdom_text = get_wisdom_nugget(chat_id)
    await update.message.reply_text(wisdom_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

async def upload_highlights_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Please upload your Kindle highlights as a **.txt document** (e.g., your 'My Clippings.txt' file). "
        "I will automatically analyze the text and suggest topics for you."
    )
    return UPLOAD_HIGHLIGHTS

async def process_uploaded_highlights(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id_str = str(update.effective_chat.id)
    raw_text_document = ""

    if update.message.document:
        if not update.message.document.file_name.lower().endswith('.txt'):
            await update.message.reply_text("Please upload a **.txt** file. Other file types are not supported for highlights.")
            return UPLOAD_HIGHLIGHTS

        file_obj = await context.bot.get_file(update.message.document.file_id)

        try:
            file_buffer = io.BytesIO()
            await file_obj.download_to_memory(out=file_buffer)
            file_buffer.seek(0)
            raw_text_document = file_buffer.read().decode('utf-8')
            file_buffer.close()
            logger.info(f"Successfully downloaded file. Content length: {len(raw_text_document)} characters")
        except Exception as e:
            logger.error(f"Error downloading or decoding file: {e}")
            await update.message.reply_text("Sorry, I had trouble reading that file. Please make sure it's a plain text (.txt) file and try again.")
            return UPLOAD_HIGHLIGHTS

    elif update.message.text:
        raw_text_document = update.message.text
        await update.message.reply_text("Thanks for the text! For larger collections, uploading a .txt file is recommended.")
    else:
        await update.message.reply_text("It seems you didn't send a .txt file or any text. Please try again.")
        return UPLOAD_HIGHLIGHTS

    parsed_highlights = parse_highlights(raw_text_document)
    if not parsed_highlights:
        await update.message.reply_text("Could not find any clear highlights in your input. Please ensure your .txt file or text is clearly formatted.")
        return ConversationHandler.END

    if chat_id_str not in user_highlights:
        user_highlights[chat_id_str] = {}

    existing_highlight_texts = set(user_highlights[chat_id_str].keys())
    new_highlights = [h for h in parsed_highlights if h not in existing_highlight_texts]
    duplicate_count = len(parsed_highlights) - len(new_highlights)

    if duplicate_count > 0:
        await update.message.reply_text(f"Found {len(parsed_highlights)} highlights. {duplicate_count} already exist and will be skipped. Processing {len(new_highlights)} new highlights...")
    else:
        await update.message.reply_text(f"Found {len(new_highlights)} new highlights. Analyzing and categorizing them now...")

    if not new_highlights:
        await update.message.reply_text("All highlights already exist in your collection. No new processing needed!")
        return ConversationHandler.END

    batch_size = 10
    failed_highlights = []
    processed_count = 0
    existing_count = len(user_highlights[chat_id_str])

    for i, highlight_text in enumerate(new_highlights):
        try:
            if i > 0 and i % batch_size == 0:
                progress_msg = f"Processing highlight {i}/{len(new_highlights)}... (Total in collection: {existing_count + processed_count})"
                await update.message.reply_text(progress_msg, disable_notification=True)

            tags = get_fast_meaning_tags(highlight_text)
            if not tags or not isinstance(tags, list):
                logger.warning(f"Invalid tags result for highlight {i+1}: {tags}")
                tags = ["untagged"]

            user_highlights[chat_id_str][highlight_text] = tags
            processed_count += 1

            if processed_count % 25 == 0:
                save_data_to_db()
                logger.info(f"Saved progress: {processed_count}/{len(new_highlights)} new highlights processed")

            if i > 0 and i % 5 == 0:
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error processing highlight {i+1}: {e}")
            failed_highlights.append((i+1, highlight_text[:50] + "..."))
            user_highlights[chat_id_str][highlight_text] = ["untagged", "processing-error"]
            processed_count += 1

    save_data_to_db()

    success_count = processed_count - len(failed_highlights)
    total_in_collection = len(user_highlights[chat_id_str])

    result_message = f"✅ Processing complete!\n\n"
    result_message += f"📊 Successfully processed: {success_count} new highlights\n"
    if failed_highlights:
        result_message += f"⚠️ Failed to process: {len(failed_highlights)} highlights\n(These were marked as 'untagged' and saved anyway)\n\n"
    if duplicate_count > 0:
        result_message += f"🔄 Skipped {duplicate_count} duplicate highlights\n\n"
    result_message += f"📚 Total highlights in your collection: {total_in_collection}"
    await update.message.reply_text(result_message)

    all_unique_tags = get_unique_tags(user_highlights[chat_id_str])

    if not all_unique_tags:
        await update.message.reply_text(
            "The smart service didn't find specific topics, but your highlights are saved. "
            "You can now use /wisdom to get a random nugget or /upload to add more."
        )
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(f"#{tag}", callback_data=f"tag_{tag}")] for tag in all_unique_tags]
    keyboard.append([InlineKeyboardButton("Done Selecting Topics", callback_data="done_topics")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Here are the topics found in your highlights. Select the ones you're interested in:",
        reply_markup=reply_markup,
    )
    return SELECT_TOPICS

async def select_topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chat_id_str = str(query.message.chat_id)
    tag_selected = query.data.replace("tag_", "")

    if chat_id_str not in user_preferences:
        user_preferences[chat_id_str] = []

    if tag_selected in user_preferences[chat_id_str]:
        user_preferences[chat_id_str].remove(tag_selected)
    else:
        user_preferences[chat_id_str].append(tag_selected)

    save_data_to_db()

    current_selected_tags_str = ', '.join([f'#{t}' for t in user_preferences[chat_id_str]]) if user_preferences.get(chat_id_str) else 'None selected'
    message_text = f"Your current topics: {current_selected_tags_str}"

    all_tags = get_unique_tags(user_highlights.get(chat_id_str, {}))
    keyboard = []
    for tag in all_tags:
        button_text = f"✅ #{tag}" if tag in user_preferences.get(chat_id_str, []) else f"#{tag}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"tag_{tag}")])

    keyboard.append([InlineKeyboardButton("Done Selecting Topics", callback_data="done_topics")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(text=message_text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        await query.message.reply_text(message_text, reply_markup=reply_markup)

    return SELECT_TOPICS

async def topics_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chat_id_str = str(query.message.chat_id)
    selected_tags_str = ', '.join([f'#{t}' for t in user_preferences.get(chat_id_str, [])])

    if selected_tags_str:
        message_text = f"Great! Your selected topics are: {selected_tags_str}.\n" \
                       "Use /wisdom to get a nugget from these topics, or /topics to change them."
    else:
        message_text = "No topics selected. You will receive random wisdom nuggets from all uploaded highlights. " \
                       "Use /topics to select some, or /wisdom for a random one."

    try:
        await query.edit_message_text(message_text)
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        await query.message.reply_text(message_text)

    return ConversationHandler.END

async def topics_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id_str = str(update.effective_chat.id)
    all_tags = get_unique_tags(user_highlights.get(chat_id_str, {}))

    if not all_tags:
        await update.message.reply_text("You haven't uploaded any highlights yet, so there are no topics to choose from. Use /upload to add your highlights.")
        return ConversationHandler.END

    keyboard = []
    for tag in all_tags:
        button_text = f"✅ #{tag}" if tag in user_preferences.get(chat_id_str, []) else f"#{tag}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"tag_{tag}")])

    keyboard.append([InlineKeyboardButton("Done Selecting Topics", callback_data="done_topics")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Select or deselect topics:", reply_markup=reply_markup)
    return SELECT_TOPICS

# --- Weekly Reminder Logic (Now async) ---
async def check_and_send_weekly_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        load_data_from_db()
        all_known_chat_ids = set(user_highlights.keys()).union(user_preferences.keys()).union(reminder_state["last_sent_time"].keys())
        current_time_utc = datetime.datetime.utcnow()

        for chat_id_str in all_known_chat_ids:
            if chat_id_str not in reminder_state["last_sent_time"]:
                continue

            try:
                chat_id_int = int(chat_id_str)
            except ValueError:
                logger.error(f"Invalid chat_id in reminder_state: {chat_id_str}")
                continue

            last_sent_timestamp = reminder_state["last_sent_time"].get(chat_id_str)
            should_send = False

            if last_sent_timestamp:
                last_sent_time = datetime.datetime.fromtimestamp(last_sent_timestamp, tz=datetime.timezone.utc)
                if current_time_utc.weekday() == 0 and current_time_utc.hour >= 9 and \
                   (current_time_utc - last_sent_time).days >= 7:
                    should_send = True
            else:
                if current_time_utc.weekday() == 0 and current_time_utc.hour >= 9:
                    should_send = True

            if should_send:
                phrase_idx = reminder_state["phrase_index"].get(chat_id_str, 0)
                reminder_message = WEEKLY_REMINDERS[phrase_idx % len(WEEKLY_REMINDERS)]

                try:
                    await context.bot.send_message(chat_id=chat_id_int, text=reminder_message)
                    logger.info(f"Sent weekly reminder to chat_id {chat_id_int}. Phrase index: {phrase_idx}")

                    reminder_state["last_sent_time"][chat_id_str] = current_time_utc.timestamp()
                    reminder_state["phrase_index"][chat_id_str] = (phrase_idx + 1) % len(WEEKLY_REMINDERS)
                    save_data_to_db()
                except Exception as e:
                    logger.error(f"Failed to send reminder to {chat_id_int}: {e}")

    except Exception as e:
        logger.error(f"Error in check_and_send_weekly_reminders: {e}")

async def set_reminders_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id_str = str(update.effective_chat.id)
    keyboard = [
        [InlineKeyboardButton("Enable Reminders", callback_data="reminders_on")],
        [InlineKeyboardButton("Disable Reminders", callback_data="reminders_off")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    status_message = "Your weekly reminders are currently "
    status_message += "ENABLED." if chat_id_str in reminder_state["last_sent_time"] else "DISABLED."
    await update.message.reply_text(status_message + "\n\nChoose an option:", reply_markup=reply_markup)

async def handle_reminders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id_str = str(query.message.chat_id)

    try:
        if query.data == "reminders_on":
            if chat_id_str not in reminder_state["last_sent_time"]:
                reminder_state["last_sent_time"][chat_id_str] = 0
                reminder_state["phrase_index"][chat_id_str] = 0
                save_data_to_db()
                await query.edit_message_text("Weekly reminders ENABLED! You'll get a fun nudge every Monday at 9 AM (UTC).")
            else:
                await query.edit_message_text("Weekly reminders are already ENABLED.")
        elif query.data == "reminders_off":
            if chat_id_str in reminder_state["last_sent_time"]:
                del reminder_state["last_sent_time"][chat_id_str]
                if chat_id_str in reminder_state["phrase_index"]:
                    del reminder_state["phrase_index"][chat_id_str]
                save_data_to_db()
                await query.edit_message_text("Weekly reminders DISABLED. You won't receive nudges anymore.")
            else:
                await query.edit_message_text("Weekly reminders are already DISABLED.")
    except Exception as e:
        logger.error(f"Error handling reminders callback: {e}")
        await query.message.reply_text("Sorry, there was an error updating your reminder settings. Please try again.")

async def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation handler for uploading highlights
    upload_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('upload', upload_highlights_start)],
        states={
            UPLOAD_HIGHLIGHTS: [MessageHandler(filters.Document.TXT | (filters.TEXT & ~filters.COMMAND), process_uploaded_highlights)],
            SELECT_TOPICS: [
                MessageHandler(filters.Document.TXT | (filters.TEXT & ~filters.COMMAND), process_uploaded_highlights),
                CallbackQueryHandler(select_topics, pattern='^tag_.*$'),
                CallbackQueryHandler(topics_done, pattern='^done_topics$')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Conversation handler for /topics command
    topics_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('topics', topics_command_handler)],
        states={
            SELECT_TOPICS: [
                CallbackQueryHandler(select_topics, pattern='^tag_.*$'),
                CallbackQueryHandler(topics_done, pattern='^done_topics$')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("wisdom", send_wisdom_nugget))
    application.add_handler(CommandHandler("reminders", set_reminders_status))
    application.add_handler(CallbackQueryHandler(handle_reminders_callback, pattern='^reminders_(on|off)$'))

    # Add conversation handlers
    application.add_handler(upload_conv_handler)
    application.add_handler(topics_conv_handler)

    # Schedule weekly reminder check
    job_queue = application.job_queue
    job_queue.run_repeating(check_and_send_weekly_reminders, interval=3600, first=0)

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    await application.run_polling()
    logger.info("Bot stopped.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot shutdown initiated by user.")
    except Exception as e:
        logger.critical(f"Bot failed to start or crashed: {e}", exc_info=True)