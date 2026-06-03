import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8967510298:AAH9SUKzNNkxA0SMKdXfHlxeD7AHZnhktfY"

BOT_USERNAME = "StakingILBot"

ADMIN_IDS = [959140085]

CHANNEL_ID = -1003703530350

DB_NAME = "have_users.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            post_id INTEGER PRIMARY KEY,
            file_id TEXT,
            caption TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            post_id INTEGER,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            PRIMARY KEY (post_id, user_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent_photos (
            user_id INTEGER,
            bot_message_id INTEGER,
            post_id INTEGER,
            PRIMARY KEY (user_id, bot_message_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_photos (
            admin_id INTEGER,
            bot_message_id INTEGER,
            post_id INTEGER,
            PRIMARY KEY (admin_id, bot_message_id)
        )
    """)

    conn.commit()
    conn.close()


def save_post(post_id, file_id, caption):
    conn = sqlite3.connect(DB_NAME)
    conn.execute(
        "INSERT OR REPLACE INTO posts VALUES (?, ?, ?)",
        (post_id, file_id, caption)
    )
    conn.commit()
    conn.close()


def get_post(post_id):
    conn = sqlite3.connect(DB_NAME)
    post = conn.execute(
        "SELECT file_id, caption FROM posts WHERE post_id = ?",
        (post_id,)
    ).fetchone()
    conn.close()
    return post


def add_subscription(post_id, user_id, username, first_name):
    conn = sqlite3.connect(DB_NAME)
    conn.execute(
        """
        INSERT OR REPLACE INTO subscriptions
        (post_id, user_id, username, first_name)
        VALUES (?, ?, ?, ?)
        """,
        (post_id, user_id, username, first_name)
    )
    conn.commit()
    conn.close()


def get_subscribers(post_id):
    conn = sqlite3.connect(DB_NAME)
    users = conn.execute(
        "SELECT user_id FROM subscriptions WHERE post_id = ?",
        (post_id,)
    ).fetchall()
    conn.close()
    return [u[0] for u in users]


def save_sent_photo(user_id, bot_message_id, post_id):
    conn = sqlite3.connect(DB_NAME)
    conn.execute(
        "INSERT OR REPLACE INTO sent_photos VALUES (?, ?, ?)",
        (user_id, bot_message_id, post_id)
    )
    conn.commit()
    conn.close()


def get_post_id_from_user_reply(user_id, bot_message_id):
    conn = sqlite3.connect(DB_NAME)
    row = conn.execute(
        """
        SELECT post_id FROM sent_photos
        WHERE user_id = ? AND bot_message_id = ?
        """,
        (user_id, bot_message_id)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def save_admin_photo(admin_id, bot_message_id, post_id):
    conn = sqlite3.connect(DB_NAME)
    conn.execute(
        "INSERT OR REPLACE INTO admin_photos VALUES (?, ?, ?)",
        (admin_id, bot_message_id, post_id)
    )
    conn.commit()
    conn.close()


def get_post_id_from_admin_reply(admin_id, bot_message_id):
    conn = sqlite3.connect(DB_NAME)
    row = conn.execute(
        """
        SELECT post_id FROM admin_photos
        WHERE admin_id = ? AND bot_message_id = ?
        """,
        (admin_id, bot_message_id)
    ).fetchone()
    conn.close()
    return row[0] if row else None


async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post

    if not post or not post.photo:
        return

    post_id = post.message_id
    file_id = post.photo[-1].file_id
    caption = post.caption or ""

    save_post(post_id, file_id, caption)

    deep_link = f"https://t.me/{BOT_USERNAME}?start=have_{post_id}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Have 👍", url=deep_link)]
    ])

    await context.bot.edit_message_reply_markup(
        chat_id=post.chat_id,
        message_id=post.message_id,
        reply_markup=keyboard
    )

    for admin_id in ADMIN_IDS:
        sent_admin_photo = await context.bot.send_photo(
            chat_id=admin_id,
            photo=file_id,
            caption=(
                f"{caption}\n\n"
                "Admin control for this Have 👍\n\n"
                "Reply to this photo with any message, photo, video or file.\n"
                "It will be sent only to users who clicked Have 👍 on this specific post.\n\n"
                "──────────────\n\n"
                "ניהול עבור ה־Have 👍 הזה\n\n"
                "הגב לתמונה הזו עם הודעה, תמונה, וידאו או קובץ.\n"
                "זה יישלח רק למשתמשים שלחצו Have 👍 על הפוסט הספציפי הזה."
            )
        )

        save_admin_photo(
            admin_id,
            sent_admin_photo.message_id,
            post_id
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if context.args and context.args[0].startswith("have_"):
        post_id = int(context.args[0].replace("have_", ""))

        post = get_post(post_id)

        if not post:
            await update.message.reply_text("Match not found.")
            return

        file_id, caption = post

        add_subscription(
            post_id,
            user.id,
            user.username,
            user.first_name
        )

        sent_photo = await context.bot.send_photo(
            chat_id=user.id,
            photo=file_id,
            caption=(
                f"{caption}\n\n"
                "📌 Match Notification Bot 📌\n\n"
                "1️⃣ Reply to this photo with your bet amount.\n"
                "Example: €10\n\n"
                "2️⃣ To remove your bet, reply:\n"
                "delete bet\n\n"
                "──────────────\n\n"
                "📌 בוט עדכוני משחקים 📌\n\n"
                "1️⃣ הגב לתמונה הזו עם סכום ההימור שלך.\n"
                "לדוגמה: €10\n\n"
                "2️⃣ כדי לבטל את ההימור שלך, הגב:\n"
                "delete bet"
            )
        )

        save_sent_photo(
            user.id,
            sent_photo.message_id,
            post_id
        )

        username = f"@{user.username}" if user.username else "No username"

        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    "🔥 New Have Click\n\n"
                    f"Name: {user.first_name}\n"
                    f"Username: {username}\n"
                    f"User ID: {user.id}\n"
                    f"Post ID: {post_id}"
                )
            )

    else:
        await update.message.reply_text(
            "Welcome 🙂\n"
            "Click Have 👍 in the channel to receive the match.\n\n"
            "──────────────\n\n"
            "ברוך הבא 🙂\n"
            "לחץ Have 👍 בערוץ כדי לקבל את המשחק."
        )


async def admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Reply to the admin control photo of a specific Have 👍 post.\n\n"
            "──────────────\n\n"
            "הגב לתמונת הניהול של Have 👍 ספציפי."
        )
        return

    replied_message_id = update.message.reply_to_message.message_id

    post_id = get_post_id_from_admin_reply(
        update.effective_user.id,
        replied_message_id
    )

    if not post_id:
        await update.message.reply_text(
            "This reply is not linked to a specific Have 👍 post.\n\n"
            "──────────────\n\n"
            "התגובה הזו לא משויכת ל־Have 👍 ספציפי."
        )
        return

    subscribers = get_subscribers(post_id)

    sent = 0
    failed = 0

    for user_id in subscribers:
        try:
            await update.message.copy(chat_id=user_id)
            sent += 1
        except Exception as e:
            print(e)
            failed += 1

    await update.message.reply_text(
        f"Sent only to this Have 👍 group\n"
        f"Post ID: {post_id}\n"
        f"Sent: {sent}\n"
        f"Failed: {failed}\n\n"
        f"──────────────\n\n"
        f"נשלח רק לקבוצת ה־Have 👍 הזו\n"
        f"Post ID: {post_id}\n"
        f"נשלח: {sent}\n"
        f"נכשל: {failed}"
    )


async def user_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id in ADMIN_IDS:
        return

    if not update.message.reply_to_message:
        return

    replied_message_id = update.message.reply_to_message.message_id

    post_id = get_post_id_from_user_reply(
        user.id,
        replied_message_id
    )

    if not post_id:
        return

    username = f"@{user.username}" if user.username else "No username"
    message_text = update.message.text if update.message.text else "Non-text message"

    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            chat_id=admin_id,
            text=(
                "📩 New Bet Reply\n\n"
                f"Post ID: {post_id}\n"
                f"Name: {user.first_name}\n"
                f"Username: {username}\n"
                f"User ID: {user.id}\n\n"
                f"Reply:\n{message_text}"
            )
        )

        await context.bot.forward_message(
            chat_id=admin_id,
            from_chat_id=user.id,
            message_id=update.message.message_id
        )


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.Chat(CHANNEL_ID) & filters.PHOTO,
            channel_post_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.User(user_id=ADMIN_IDS)
            & ~filters.COMMAND,
            admin_message
        )
    )

    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & ~filters.User(user_id=ADMIN_IDS)
            & ~filters.COMMAND,
            user_reply
        )
    )

    print("Bot is running...")

    app.run_polling(
        allowed_updates=["message", "channel_post"]
    )


if __name__ == "__main__":
    main()
