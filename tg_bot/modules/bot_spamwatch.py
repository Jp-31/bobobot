import spamwatch
import html

from telegram import Message, Update, Bot, User, Chat, ParseMode, InlineKeyboardMarkup
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters, CallbackContext

from tg_bot import dispatcher, SPAMWATCH_TOKEN, LOGGER
import tg_bot.modules.sql.global_bans_sql as sql
from telegram.utils.helpers import mention_html
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat, is_bot_admin
from tg_bot.modules.helper_funcs.extraction import extract_user

client = spamwatch.Client(SPAMWATCH_TOKEN) # initialize spamwatch client with the token from the config file
SPAM_ENFORCE_GROUP = 7

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

        spam_ban(update, context, user.id, spamwatch_text)

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

        spam_ban(update, context, user.id, is_banned.reason)
        

@run_async
@bot_admin
@can_restrict
@user_admin
def spam_ban(update: Update, context: CallbackContext, user_id, reason) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    reply = "{} has been banned by " \
            "<a href=\"http://telegram.me/SpamWatchFederationLog\">SpamWatch</a>!".format(mention_html(user.id, 
                                                                                          user.first_name))
    
    if reason:
        reply += "\n<b>Reason:</b> <i>{}</i>".format(reason)

    try:
        chat.kick_member(user_id)
        message.reply_text(reply, parse_mode=ParseMode.HTML)
        return

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text('Banned!', quote=False)
            return
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Well damn, I can't ban that user.")

    return ""

# @run_async
# @user_admin
# def spamwatch_stat(update: Update, context: CallbackContext):
#     chat = update.effective_chat
#     if len(args) > 0:
#         if args[0].lower() in ["on", "yes"]:
#             sql.enable_gbans(update.effective_chat.id)
#             spamstat = "I've enabled SpamWatch ban for {}. Therefore, "
#                        "You're protected from active spammers, trolls, unsavoury characters."
#             update.effective_message.reply_text(spamstat.format(chat.title))
#
#         elif args[0].lower() in ["off", "no"]:
#             sql.disable_gbans(update.effective_chat.id)
#             spamstat = "I've disabled SpamWatch bans for {}. SpamWatch ban wont affect your users "
#                        "anymore. You'll be less protected from any trolls and spammers "
#                        "though!"
#             update.effective_message.reply_text(spamstat.format(chat.title))
#     else:
#         update.effective_message.reply_text("Give me some arguments to choose a setting! on/off, yes/no!\n\n"
#                                             "Your current setting is: {}\n"
#                                             "When True, any SpamWatch bans that happen will also happen in your group. "
#                                             "When False, they won't, leaving you at the possible mercy of "
#                                             "spammers.".format(sql.does_chat_gban(update.effective_chat.id)))

def __user_info__(user_id):
    is_banned = client.get_ban(user_id)

    user = client.get_ban(user_id)
    text =""
    if is_banned:
        text = "This user is currently banned by Spamwatch."
        if user.reason:
            text += "\nReason: {}".format(html.escape(user.reason))
    return text
    
__help__ = """
SpamWatch maintains a large constantly updated ban-list of spambots, trolls, unsavoury characters. {} will constantly \
help banning any possible spammers off your chatroom automatically, you're less likely to worry about spammers \
storming the chatroom.

You can disable the SpamWatch bans by `/spamwatch off` or enable `/spamwatch on`, {} will either actively engage or \
disengage from protecting the chatroom.

*Admin only:*
 - /spamwatch <on/off/yes/no>: Will disable the effect of SpamWatch bans on your group, or return your current settings.
""".format(dispatcher.bot.first_name, dispatcher.bot.first_name)

__mod_name__ = "SpamWatch"
    
SPAM_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_spamwatch_ban)
dispatcher.add_handler(SPAM_ENFORCER, SPAM_ENFORCE_GROUP)