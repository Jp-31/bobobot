import spamwatch
import html

from telegram import Message, Update, Bot, User, Chat, ParseMode, InlineKeyboardMarkup
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters

from tg_bot import dispatcher, SPAMWATCH_TOKEN, BAN_STICKER, LOGGER
from telegram.utils.helpers import mention_html
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat, is_bot_admin
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.log_channel import loggable

client = spamwatch.Client(SPAMWATCH_TOKEN) # initialize spamwatch client with the token from the config file

def welcome_spamwatch_ban(update: Update, context: CallbackContext, user_id):
    chat = update.effective_chat  # type: Optional[Chat]
    user = context.bot.get_chat(user_id)
    msg = update.effective_message
    banned_user = client.get_ban(user_id)
    
    spamwatch_text = "No reason given."
    
    if banned_user:
        update.effective_chat.kick_member(user_id)

        if banned_user.reason:
            spamwatch_text = banned_user.reason

        ban(update, context, user.id, spamwatch_text)

@run_async
def enforce_spamwatch_ban(update: Update, context: CallbackContext):
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    
    spamwatch_text = "No reason given."
    
    if msg.new_chat_members:
        new_members = update.effective_message.new_chat_members
        for mem in new_members:
            welcome_spamwatch_ban(update, context, mem.id)
    
    is_banned = client.get_ban(user.id)
    
    if is_banned:
        if is_banned.reason:
            spamwatch_text = is_banned.reason

        ban(update, context, user.id, is_banned.reason)
        
@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def ban(update: Update, context: CallbackContext, user_id, reason) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("I can't seem to find this user")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Why would I ban an admin? That sounds like a pretty dumb idea.")
        return ""

    if user_id == context.bot.id:
        message.reply_text("I'm not gonna BAN myself, are you crazy?")
        return ""

    log = "<b>{}:</b>" \
          "\n#BANNED" \
          "\n<b>• Admin:</b> {}" \
          "\n<b>• User:</b> {}" \
          "\n<b>• ID:</b> <code>{}</code>".format(html.escape(chat.title), mention_html(user.id, user.first_name), 
                                                  mention_html(member.user.id, member.user.first_name), user_id)

    reply = "{} has been banned through Spamwatch!".format(mention_html(member.user.id, member.user.first_name))
    if reason:
        log += "\n<b>• Reason:</b> {}".format(reason)
        reply += "\n<b>Reason:</b> <i>{}</i>".format(reason)

    try:
        chat.kick_member(user_id)
        message.reply_text(reply, parse_mode=ParseMode.HTML)
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text('Banned!', quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Well damn, I can't ban that user.")

    return ""

SPAM_ENFORCE_GROUP = 6
SPAM_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_spamwatch_ban)
dispatcher.add_handler(SPAM_ENFORCER, SPAM_ENFORCE_GROUP)