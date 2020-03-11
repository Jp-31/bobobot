import spamwatch
import html

from io import BytesIO
from telegram import Message, Update, Bot, User, Chat, ParseMode, InlineKeyboardMarkup
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters, CallbackContext

from tg_bot import dispatcher, SPAMWATCH_TOKEN, LOGGER, CMD_PREFIX, SUDO_USERS, SUPPORT_USERS, GBAN_LOG
import tg_bot.modules.sql.global_bans_sql as sql
from tg_bot.modules.helper_funcs.handlers import CustomCommandHandler
from telegram.utils.helpers import mention_html
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat, is_bot_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters

client = spamwatch.Client(SPAMWATCH_TOKEN) # initialize spamwatch client with the token from the config file
SPAM_ENFORCE_GROUP = 7

@run_async
def unspamban(update: Update, context: CallbackContext):
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    args = message.text.split(" ")
    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return

    try:
        user_chat = context.bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("That's not a user!")
        return

    starting = "Whitelisting {} from SpamWatch ban...".format(mention_html(user_chat.id, 
                                                              user_chat.first_name or "Deleted Account"))
    message.reply_text(starting, parse_mode=ParseMode.HTML)
    
    super_user = update.effective_user  # type: Optional[User]
    spam_log = "<b>SpamWatch</b>" \
                "\n#WHITELIST" \
                "\n<b>Status:</b> <code>WHITELISTED</code>" \
                "\n<b>Name:</b> {}".format(mention_html(user_chat.id, user_chat.first_name or "Deleted Account"))
    
    if user_chat.last_name:
        spam_log += "\n<b>Surname:</b> {}".format(mention_html(user_chat.id, user_chat.last_name))
    
    if user_chat.username:
        spam_log += "\n<b>Username:</b> @{}".format(html.escape(user_chat.username))
    
    if  user_chat:
        spam_log += "\n<b>ID:</b> <code>{}</code>".format(user_chat.id)
    
    if super_user.id in SUDO_USERS:
        spam_log += "\n<b>Sudo:</b> {}".format(mention_html(super_user.id, super_user.first_name))
    
    if super_user.id in SUPPORT_USERS:
        spam_log += "\n<b>Support:</b> {}".format(mention_html(super_user.id, super_user.first_name))
    
    context.bot.send_message(chat_id=GBAN_LOG, text=spam_log, parse_mode=ParseMode.HTML)
    sql.spam_whitelist(user_id, user_chat.username or user_chat.first_name)
    
    spamtxt = "User {} whitelisted in SpamWatch".format(mention_html(user_chat.id, user_chat.first_name or 
                                                               "Deleted Account"))
    
    
    context.bot.send_message(chat_id=GBAN_LOG, text=spamtxt, parse_mode=ParseMode.HTML)

    message.reply_text("User {} whitelisted in SpamWatch!".format(mention_html(user_chat.id, user_chat.first_name 
                                                            or "Deleted Account")), parse_mode=ParseMode.HTML)

@run_async
def spamban(update: Update, context: CallbackContext):
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    args = message.text.split(" ")

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return

    user_chat = context.bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("That's not a user!")
        return

    if not sql.spam_not_in_hoe(user_id):
        msg = "User {} is not whitelisted from SpamWatch!".format(mention_html(user_chat.id, user_chat.first_name 
                                                                         or "Deleted Account"))
        
        message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    super_user = update.effective_user  # type: Optional[User]

    message.reply_text("Removing {} from SpamWatch whitelist.".format(user_chat.first_name or "Deleted Account"))

    send_gban = "<b>Regression of SpamWatch</b>" \
                "\n#UNWHITELIST" \
                "\n<b>Status:</b> <code>Ceased</code>" \
                "\n<b>Name:</b> {}".format(mention_html(user_chat.id, user_chat.first_name or "Deleted Account"))
    
    if user_chat.last_name:
        send_gban += "\n<b>Surname:</b> {}".format(mention_html(user_chat.id, user_chat.last_name))
    
    if user_chat.username:
        send_gban += "\n<b>Username:</b> @{}".format(html.escape(user_chat.username))
    
    if  user_chat:
        send_gban += "\n<b>ID:</b> <code>{}</code>".format(user_chat.id)
    
    if super_user.id in SUDO_USERS:
        send_gban += "\n<b>Sudo:</b> {}".format(mention_html(super_user.id, super_user.first_name))
    
    if super_user.id in SUPPORT_USERS:
        send_gban += "\n<b>Support:</b> {}".format(mention_html(super_user.id, super_user.first_name))

    context.bot.send_message(chat_id=GBAN_LOG, text=send_gban, parse_mode=ParseMode.HTML)
    
    sql.spam_unwhitelist(user_id)
    blacklist_t = "User {} removed from SpamWatch whitelist.".format(mention_html(user_chat.id, user_chat.first_name or 
                                                                                     "Deleted Account"))
    
    context.bot.send_message(chat_id=GBAN_LOG, text=blacklist_t, parse_mode=ParseMode.HTML)
                                                                            
    message.reply_text("User {} removed from SpamWatch whitelist.".format(mention_html(user_chat.id, user_chat.first_name 
                                                               or "Deleted Account")), parse_mode=ParseMode.HTML)

@run_async
@bot_admin
@can_restrict
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

        spam_ban_join(update, context, user.id, spamwatch_text)

@run_async
def enforce_spamwatch_ban(update: Update, context: CallbackContext):
    if sql.does_chat_spamwatch(update.effective_chat.id) and update.effective_chat.get_member(context.bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]
        #spamwatch_alert = sql.get_spamwatch_alert(chat.id)
        new_members = update.effective_message.new_chat_members
        
        is_banned = client.get_ban(user.id)

        if sql.spamwatch_whitelisted(user.id): # dont ban whitelisted users
            return

        if user and not is_user_admin(chat, user.id):
            if is_banned:
                if is_banned.reason:
                    spamwatch_text = is_banned.reason

                spam_ban(update, context, user.id, is_banned.reason)

        if msg.text:
            if user and not is_user_admin(chat, user.id):
                if is_banned:
                    if is_banned.reason:
                        spamwatch_text = is_banned.reason

                    spam_ban(update, context, user.id, is_banned.reason)

        elif msg.new_chat_members:
            for mem in new_members:
                welcome_spamwatch_ban(update, context, mem.id)

        elif new_members:
            for mem in new_members:
                welcome_spamwatch_ban(update, context, mem.id)

@run_async
@bot_admin
@can_restrict
def spam_ban(update: Update, context: CallbackContext, user_id, reason) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    reply = "User {} has been banned by " \
            "<a href=\"http://telegram.me/SpamWatchFederationLog\">SpamWatch</a>!".format(mention_html(user.id, user.first_name))
    
    if reason:
        reply += "\n<b>Reason:</b> <i>{}</i>".format(reason)

    try:
        chat.kick_member(user_id)
        message.reply_text(reply, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        return

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            chat.kick_member(user_id)
            context.bot.send_message(chat.id, reply, parse_mode=ParseMode.HTML, disable_web_page_preview=True, quote=False)
            return
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Well damn, I can't ban that user.")

    return ""

@run_async
@bot_admin
@can_restrict
def spam_ban_join(update: Update, context: CallbackContext, user_id, reason) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    
    if message.new_chat_members:
        new_members = update.effective_message.new_chat_members
        for mem in new_members:
            reply = "User {} has been banned by " \
                    "<a href=\"http://telegram.me/SpamWatchFederationLog\">SpamWatch</a>!".format(mention_html(mem.id, mem.first_name))
            
            if reason:
                reply += "\n<b>Reason:</b> <i>{}</i>".format(reason)

            try:
                chat.kick_member(user_id)
                message.reply_text(reply, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                return

            except BadRequest as excp:
                if excp.message == "Reply message not found":
                    # Do not reply
                    chat.kick_member(user_id)
                    message.reply_text(reply, parse_mode=ParseMode.HTML, disable_web_page_preview=True, quote=False)
                    return
                else:
                    LOGGER.warning(update)
                    LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                                    excp.message)
                    message.reply_text("Well damn, I can't ban that user.")

    return ""

@run_async
def spamwatchlist(update: Update, context: CallbackContext):
    spamwatch_whitelist = sql.get_spamwatch_list()

    if not spamwatch_whitelist:
        update.effective_message.reply_text("There aren't any whitelisted spam users!")
        return

    banfile = 'These guys are immunity to SpamWatch\n'
    for user in spamwatch_whitelist:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "spamwatch.txt"
        update.effective_message.reply_document(document=output, filename="spamwatch.txt",
                                                caption="Here is the list of currently whitelisted users.")

@run_async
@user_admin
def spamwatch_stat(update: Update, context: CallbackContext):
    chat = update.effective_chat
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(" ")
    args_option = ""
    
    if len(args) > 1:
        args_option = args[1].lower()
    
    if len(args) >= 2:
        if args_option != "" and args_option in ["on", "yes"]:
            sql.enable_spamw(update.effective_chat.id)
            spamstat_1 = "I've enabled SpamWatch ban for {}. Therefore, " \
                         "You're protected from spammers, spambots, trolls and unsavoury characters.".format(chat.title)
            msg.reply_text(spamstat_1)
        
        elif args_option != "" and args_option in ["off", "no"]:
            sql.disable_spamw(update.effective_chat.id)
            spamstat_2 = "I've disabled SpamWatch bans for {}. SpamWatch ban wont affect your users " \
                          "anymore. You'll be less protected from any trolls and spammers " \
                          "though!".format(chat.title)
            update.effective_message.reply_text(spamstat_2)
    else:
        msg.reply_text("Give me some arguments to choose a setting! on/off, yes/no!\n\n"
                       "Your current setting is: {}\n"
                       "When True, any SpamWatch bans that happen will also happen in your group. "
                       "When False, they won't, leaving you at the possible mercy of "
                       "spammers.".format(sql.does_chat_spamwatch(chat.id)))

    
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

UNSPAMBAN_HANDLER = CustomCommandHandler(CMD_PREFIX, "unspamban", unspamban,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
SPAMBAN_HANDLER = CustomCommandHandler(CMD_PREFIX, "spamban", spamban,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
SPAM_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_spamwatch_ban)
SPAM_STATUS = CustomCommandHandler(CMD_PREFIX, "spamwatch", spamwatch_stat, filters=Filters.group)
SPAM_LIST = CustomCommandHandler(CMD_PREFIX, "spamlist", spamwatchlist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

dispatcher.add_handler(SPAM_ENFORCER, SPAM_ENFORCE_GROUP)
dispatcher.add_handler(SPAM_STATUS)
dispatcher.add_handler(UNSPAMBAN_HANDLER)
dispatcher.add_handler(SPAMBAN_HANDLER)
dispatcher.add_handler(SPAM_LIST)
