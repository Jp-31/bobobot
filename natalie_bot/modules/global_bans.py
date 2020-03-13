import html, time, spamwatch
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.utils.helpers import mention_html

import natalie_bot.modules.sql.global_bans_sql as sql
from natalie_bot import dispatcher, OWNER_ID, SUPER_ADMINS, SUDO_USERS, EVIDENCES_LOG, SUPPORT_USERS, \
     STRICT_GBAN, GBAN_LOG, CMD_PREFIX, SPAMWATCH_TOKEN, LOGGER
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from natalie_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from natalie_bot.modules.helper_funcs.filters import CustomFilters
from natalie_bot.modules.sql.users_sql import get_all_chats, get_users_by_chat, get_name_by_userid

GBAN_ENFORCE_GROUP = 6
client = spamwatch.Client(SPAMWATCH_TOKEN) # initialize spamwatch client with the token from the config file

GBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Only the creator of a basic group can kick group administrators",
    "Channel_private",
    "Not in the chat"
}

UNGBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Method is available for supergroup and channel chats only",
    "Not in the chat",
    "Channel_private",
    "Chat_admin_required",
    "Peer_id_invalid",
}


@run_async
def gban(update: Update, context: CallbackContext):
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    args = message.text.split(" ")
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("You're playing with fire! Sudo war is catastrophic.")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("I can't global ban a support user! Only my creator can!")
        return
    
    if int(user_id) in SUPER_ADMINS:
        message.reply_text("This is one of the super admin users appointed by the hierarchy. "
                           "Therefore, I can't touch this user!")
        return

    if user_id == context.bot.id:
        message.reply_text("Only my creator can decide the fate!")
        return

    try:
        user_chat = context.bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("That's not a user!")
        return

    if sql.is_user_gbanned(user_id):
        if not reason:
            msg = "User {} is already globally banned; I'd change the reason, " \
                  "but you haven't given me one...".format(mention_html(user_chat.id, user_chat.first_name 
                                                                        or "Deleted Account"))
            message.reply_text(msg, parse_mode=ParseMode.HTML)
            return

        old_reason = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        user_id, new_reason = extract_user_and_text(message, args)
        
        if old_reason == new_reason:
            same_reason = "User {} has already been globally banned, with the " \
                          "exact same reason.".format(mention_html(user_chat.id, user_chat.first_name or  
                                                                   "Deleted Account"))
            
            message.reply_text(same_reason, parse_mode=ParseMode.HTML)
            return
        
        if old_reason:
            banner = update.effective_user  # type: Optional[User]
            send_gban = "<b>Emendation of Global Ban</b>" \
                        "\n#GBAN" \
                        "\n<b>Status:</b> <code>Amended</code>" \
                        "\n<b>Name:</b> {}".format(mention_html(user_chat.id, user_chat.first_name or 
                                                                "Deleted Account"))
    
            if user_chat.last_name:
                send_gban += "\n<b>Surname:</b> {}".format(mention_html(user_chat.id, user_chat.last_name))
            
            if user_chat.username:
                send_gban += "\n<b>Username:</b> @{}".format(html.escape(user_chat.username))
            
            if  user_chat:
                send_gban += "\n<b>ID:</b> <code>{}</code>".format(user_chat.id)
            
            if banner.id in SUDO_USERS:
                send_gban += "\n<b>Sudo:</b> {}".format(mention_html(banner.id, banner.first_name))
            
            if banner.id in SUPPORT_USERS:
                send_gban += "\n<b>Support:</b> {}".format(mention_html(banner.id, banner.first_name))
            
            if reason:
                send_gban += "\n<b>Previous:</b> {}".format(old_reason)
                send_gban += "\n<b>Amended:</b> {}".format(new_reason)
            
            context.bot.send_message(chat_id=GBAN_LOG, text=send_gban, parse_mode=ParseMode.HTML)
            old_msg = "User {} is already globally banned, for the following reason:\n" \
                      "<code>{}</code>\n" \
                      "I've gone and updated it with your new reason!".format(mention_html(user_chat.id, 
                                                                              user_chat.first_name or "Deleted Account"), 
                                                                              old_reason)
            message.reply_text(old_msg, parse_mode=ParseMode.HTML)
        
        else:
            banner = update.effective_user  # type: Optional[User]
            send_gban = "<b>Emendation of Global Ban</b>" \
                        "\n#GBAN" \
                        "\n<b>Status:</b> <code>New reason</code>" \
                        "\n<b>Name:</b> {}".format(mention_html(user_chat.id, user_chat.first_name or 
                                                                "Deleted Account"))
    
            if user_chat.last_name:
                send_gban += "\n<b>Surname:</b> {}".format(mention_html(user_chat.id, user_chat.last_name))
            
            if user_chat.username:
                send_gban += "\n<b>Username:</b> @{}".format(html.escape(user_chat.username))
            
            if  user_chat:
                send_gban += "\n<b>ID:</b> <code>{}</code>".format(user_chat.id)
            
            if banner.id in SUDO_USERS:
                send_gban += "\n<b>Sudo:</b> {}".format(mention_html(banner.id, banner.first_name))
            
            if banner.id in SUPPORT_USERS:
                send_gban += "\n<b>Support:</b> {}".format(mention_html(banner.id, banner.first_name))
            
            if banner.id in SUPER_ADMINS:
                send_gban += "\n<b>Super Admin:</b> {}".format(mention_html(banner.id, banner.first_name))
            
            if reason:
                send_gban += "\n<b>Reason:</b> {}".format(new_reason)
            
            
            context.bot.send_message(chat_id=GBAN_LOG, text=send_gban, parse_mode=ParseMode.HTML)
            msg = "User {} is already globally banned, but had no reason set; " \
                  "I've gone and updated it!".format(mention_html(user_chat.id, user_chat.first_name or "Deleted Account"))
            message.reply_text(msg, parse_mode=ParseMode.HTML)

        return

    starting = "Initiating global ban for {}...".format(mention_html(user_chat.id, user_chat.first_name or "Deleted Account"))

    message.reply_text(starting, parse_mode=ParseMode.HTML)
    
    banner = update.effective_user  # type: Optional[User]
    send_gban = "<b>Global Ban</b>" \
                "\n#GBAN" \
                "\n<b>Status:</b> <code>Enforced</code>" \
                "\n<b>Name:</b> {}".format(mention_html(user_chat.id, user_chat.first_name or "Deleted Account"))
    
    if user_chat.last_name:
        send_gban += "\n<b>Surname:</b> {}".format(mention_html(user_chat.id, user_chat.last_name))
    
    if user_chat.username:
        send_gban += "\n<b>Username:</b> @{}".format(html.escape(user_chat.username))
    
    if  user_chat:
        send_gban += "\n<b>ID:</b> <code>{}</code>".format(user_chat.id)
    
    if banner.id in SUDO_USERS:
        send_gban += "\n<b>Sudo:</b> {}".format(mention_html(banner.id, banner.first_name))
    
    if banner.id in SUPPORT_USERS:
        send_gban += "\n<b>Support:</b> {}".format(mention_html(banner.id, banner.first_name))
    
    if reason:
        send_gban += "\n<b>Reason:</b> {}".format(reason)
    

    context.bot.send_message(chat_id=GBAN_LOG, text=send_gban, parse_mode=ParseMode.HTML)
    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)
    
    fban_id = update.effective_chat  # type: Optional[Chat]
    chats = get_users_by_chat(fban_id.id, user_id)
    for chat in chats:
        chat_id = chat.chat

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            context.bot.kick_chat_member(chat_id, user_id)
        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text("Could not gban due to: {}".format(excp.message))
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass
    
    blacklist_t = "User {} has been successfully globally banned".format(mention_html(user_chat.id, user_chat.first_name or 
                                                               "Deleted Account"))
    
    
    context.bot.send_message(chat_id=GBAN_LOG, text=blacklist_t, parse_mode=ParseMode.HTML)

    message.reply_text("User {} has been globally banned!".format(mention_html(user_chat.id, user_chat.first_name 
                                                            or "Deleted Account")), parse_mode=ParseMode.HTML)


@run_async
def ungban(update: Update, context: CallbackContext):
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

    if not sql.is_user_gbanned(user_id):
        msg = "User {} is not globally banned!".format(mention_html(user_chat.id, user_chat.first_name 
                                                                         or "Deleted Account"))
        
        message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    banner = update.effective_user  # type: Optional[User]

    message.reply_text("Removing {} from global ban.".format(user_chat.first_name or "Deleted Account"))

    send_gban = "<b>Regression of Global Ban</b>" \
                "\n#GBAN" \
                "\n<b>Status:</b> <code>Ceased</code>" \
                "\n<b>Name:</b> {}".format(mention_html(user_chat.id, user_chat.first_name or "Deleted Account"))
    
    if user_chat.last_name:
        send_gban += "\n<b>Surname:</b> {}".format(mention_html(user_chat.id, user_chat.last_name))
    
    if user_chat.username:
        send_gban += "\n<b>Username:</b> @{}".format(html.escape(user_chat.username))
    
    if  user_chat:
        send_gban += "\n<b>ID:</b> <code>{}</code>".format(user_chat.id)
    
    if banner.id in SUDO_USERS:
        send_gban += "\n<b>Sudo:</b> {}".format(mention_html(banner.id, banner.first_name))
    
    if banner.id in SUPPORT_USERS:
        send_gban += "\n<b>Support:</b> {}".format(mention_html(banner.id, banner.first_name))

    context.bot.send_message(chat_id=GBAN_LOG, text=send_gban, parse_mode=ParseMode.HTML)    
    unfban_id = update.effective_chat  # type: Optional[Chat]
    chats = get_users_by_chat(unfban_id.id, user_id)
    for chat in chats:
        chat_id = chat.chat

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = context.bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                context.bot.unban_chat_member(chat_id, user_id)

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text("Could not un-gban due to: {}".format(excp.message))
                context.bot.send_message(OWNER_ID, "Could not un-gban due to: {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)
    
    blacklist_t = "User {} has been ungbanned.".format(mention_html(user_chat.id, user_chat.first_name or 
                                                                                     "Deleted Account"))
    
    context.bot.send_message(chat_id=GBAN_LOG, text=blacklist_t, parse_mode=ParseMode.HTML)
                                                                            
    message.reply_text("User {} has been pardoned from global ban.".format(mention_html(user_chat.id, user_chat.first_name 
                                                               or "Deleted Account")), parse_mode=ParseMode.HTML)

@run_async
def gbanlist(update: Update, context: CallbackContext):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text("There aren't any gbanned users! You're kinder than I expected...")
        return

    banfile = 'Screw these guys.\n'
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(document=output, filename="gbanlist.txt",
                                                caption="Here is the list of currently gbanned users.")

def gban_notification(update: Update, context: CallbackContext, user_info, should_message=True):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    chat_member = user_info
    user_r = sql.get_gbanned_user(chat_member.user.id)
    
    
    chatban_text = "User {} is currently globally banned and is removed from {} with an " \
                   "immediate effect.".format(mention_html(chat_member.user.id, 
                                                           chat_member.user.first_name 
                                                           or "Deleted Account"), chat.title)
    
    if sql.is_user_gbanned(chat_member.user.id):
        if user_r.reason:
            chatban_text += "\n<b>Reason</b>: {}".format(user_r.reason)
                
        if should_message:
            try:
                msg.reply_text(chatban_text, parse_mode=ParseMode.HTML)
            except:
                context.bot.send_message(chat.id, 
                                            chatban_text, parse_mode=ParseMode.HTML)
                LOGGER.exception("Reply with gban notification.")

def check_and_ban(update, context, user_id):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message
       
    if sql.is_user_gbanned(user_id):
        chat.kick_member(user_id)

def welcome_gban(update, context, user_id):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message
           
    if sql.is_user_gbanned(user_id):
        chat.kick_member(user_id)
        try:
            if msg:
                msg.delete()
        except:
            LOGGER.log(2, "Could not find the message to delete.")

@run_async
def enforce_gban(update: Update, context: CallbackContext):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if sql.does_chat_gban(update.effective_chat.id) and update.effective_chat.get_member(context.bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]
        gban_alert = sql.get_gban_alert(chat.id)
        new_members = update.effective_message.new_chat_members
        user_info = context.bot.get_chat_member(chat.id, user.id)

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, context, user.id)

        if msg.text:
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, context, user.id)

                if gban_alert:
                    gban_notification(update, context, user_info,
                                  should_message=True)
                    
        elif msg.new_chat_members:
            for mem in new_members:
                user_info = context.bot.get_chat_member(chat.id, mem.id)
                welcome_gban(update, context, mem.id)
                if gban_alert:
                    gban_notification(update, context, user_info,
                                  should_message=True)

        elif new_members:
            for mem in new_members:
                welcome_gban(update, context, mem.id)
                if gban_alert:
                    gban_notification(update, context, user_info,
                                  should_message=True)

@run_async
@user_admin
def gbanalert(update: Update, context: CallbackContext):
    chat = update.effective_chat
    args = update.effective_message.text.split(" ")
    args_option = ""
    bot = context.bot
    
    if len(args) > 1:
        args_option = args[1].lower()
        
    if len(args) > 1:
        if args_option != "" and args_option in ["on", "yes"]:
            sql.enable_alert(chat.id)
            update.effective_message.reply_text("Global ban notification is <code>enabled</code> for {}.".format(chat.title),
                                                 parse_mode=ParseMode.HTML)
        elif args_option != "" and args_option in ["off", "no"]:
            sql.disable_alert(chat.id)
            update.effective_message.reply_text("Global ban notification is <code>disabled</code> for {}.".format(chat.title),
                                                 parse_mode=ParseMode.HTML)
        else:
            update.effective_message.reply_text("Unknown Type command. I only understand on/yes or off/no!")
    else:
        alert = sql.does_chat_alert(chat.id)
        if not alert:
            aler_txt = "Global ban notifications are currently <code>enabled</code>; whenever a user " \
                       "that is banned in {} joins or speaks in {}, they will be removed, " \
                       "along with a message " \
                       "explaining why.".format(bot.first_name, chat.title)
            update.effective_message.reply_text(aler_txt, parse_mode=ParseMode.HTML)
        else:
            aler_txt = "Global ban notifications are currently <code>disable</code>; whenever a user " \
                       "that is banned in {} joins or speaks in {}, they will be quietly removed.".format(bot.first_name, 
                                                                                                          chat.title)
            update.effective_message.reply_text(aler_txt, parse_mode=ParseMode.HTML)
        

@run_async
def msg_evidence(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    args = msg.text.split(" ")
    user_id, reason = extract_user_and_text(msg, args)
    user_chat = context.bot.get_chat(user_id)
    send_proof = msg.reply_to_message.forward(EVIDENCES_LOG)
    saved = msg.reply_text("Global Ban evidence submitted!")
    msg.delete()
    
    try:
       time.sleep(3)
       saved.delete()
    
    except TelegramError as e:
        if e.message == "Peer_id_invalid":
               msg.reply_text("Contact me in PM first.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                   text="Start", url=f"t.me/{context.bot.username}")]]))
        return
    
    if send_proof:
        saved
        banner = update.effective_user  # type: Optional[User]
        send_gban = "<b>Global Ban Evidence</b>" \
                    "\n#EVIDENCE" \
                    "\n<b>Status:</b> <code>Submitted</code>" \
                    "\n<b>Name:</b> {}".format(mention_html(user_chat.id, user_chat.first_name or "Deleted Account"))
        if user_chat.last_name:
            send_gban += "\n<b>Surname:</b> {}".format(mention_html(user_chat.id, user_chat.last_name))
        
        if user_chat.username:
            send_gban += "\n<b>Username:</b> @{}".format(html.escape(user_chat.username))
        
        if  user_chat:
            send_gban += "\n<b>ID:</b> <code>{}</code>".format(user_chat.id)
        
        if banner.id in SUDO_USERS:
            send_gban += "\n<b>Sudo:</b> {}".format(mention_html(banner.id, banner.first_name))
        
        if banner.id in SUPPORT_USERS:
            send_gban += "\n<b>Support:</b> {}".format(mention_html(banner.id, banner.first_name))
        
        if reason:
                send_gban += "\n<b>Description of Evidence:</b> \n{}".format(reason)
        
        
        context.bot.send_message(chat_id=EVIDENCES_LOG, text=send_gban, parse_mode=ParseMode.HTML)
       
    
    else:
       msg.reply_text("Failed to submit proof.")


@run_async
@user_admin
def gbanstat(update: Update, context: CallbackContext):
    chat = update.effective_chat
    args = update.effective_message.text.split(" ")
    args_option = ""
    
    if len(args) > 1:
        args_option = args[1].lower()
        
    if len(args) >= 2:
        if args_option != "" and args_option in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("I've enabled gbans for {}. This will help protect you "
                                                "from spammers, unsavoury characters, and "
                                                "the biggest trolls.".format(chat.title))
        elif args_option != "" and args_option in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("I've disabled gbans for {}. Global ban wont affect your users "
                                                "anymore. You'll be less protected from any trolls and spammers "
                                                "though!".format(chat.title))
    else:
        update.effective_message.reply_text("Give me some arguments to choose a setting! on/off, yes/no!\n\n"
                                            "Your current setting is: {}\n"
                                            "When True, any gbans that happen will also happen in your group. "
                                            "When False, they won't, leaving you at the possible mercy of "
                                            "spammers.".format(sql.does_chat_gban(update.effective_chat.id)))

def __stats__():
    return "{} gbanned users.".format(sql.num_gbanned_users())


def __user_info__(user_id):
    is_banned = client.get_ban(user_id)
    gbanned = sql.is_user_gbanned(user_id)

    user_sw = client.get_ban(user_id)
    user_gb = sql.get_gbanned_user(user_id)
    text =""
    
    if is_banned:
        text = "This user is currently banned by SpamWatch."
        if user_sw.reason:
            text += "\nReason: {}".format(html.escape(user_sw.reason))
    
    if gbanned:
        text = "This user is currently globally banned."
        if user_gb.reason:
            text += "\nReason: {}".format(html.escape(user_gb.reason))
            
    if is_banned and gbanned:
        text = "This user is currently globally and SpamWatch banned."
        if user_gb.reason:
            text += "\nGlobal Ban Reason: {}".format(html.escape(user_gb.reason))
            
        if user_sw.reason:
            text += "\nSpamWatch Ban Reason: {}".format(html.escape(user_sw.reason))
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "This chat is enforcing *gbans*: `{}`.".format(sql.does_chat_gban(chat_id))


__help__ = """
It's all fun and games, until you start getting spammers in, and you need to ban them. Then you need to start \
banning more, and more, and it gets painful. With Global bans enforcing in your chat, {}'s admins actively \
bans spammers, trolls and unsavoury characters.

Global bans will actively engage in banning spammers, you'd have to worry-less on spammers joining in and {} will \
remove them from your group quickly as possible.

You can disable the Global bans by `/gbanstat off` or enable `/gbanstat on`.

*Admin only:*
 - /gbanstat <on/off/yes/no>: Will disable the effect of global bans on your group, or return your current settings.
 - /gbanalert <on/off/yes/no>: Whether or not send global ban notification in the chat upon user join/speak in the chat.
""".format(dispatcher.bot.first_name, dispatcher.bot.first_name)

__mod_name__ = "Global Bans"

GBAN_HANDLER = CustomCommandHandler(CMD_PREFIX, ["fban", "gban"], gban,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGBAN_HANDLER = CustomCommandHandler(CMD_PREFIX, ["unfban", "ungban"], ungban,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GBAN_LIST = CustomCommandHandler(CMD_PREFIX, "gbanlist", gbanlist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GBAN_STATUS = CustomCommandHandler(CMD_PREFIX, "gbanstat", gbanstat, filters=Filters.group)
GBAN_ALERT = CustomCommandHandler(CMD_PREFIX, "gbanalert", gbanalert, filters=Filters.group)
PROOF_HANDLER = CustomCommandHandler(CMD_PREFIX, ["proof", "p"], msg_evidence, 
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)
dispatcher.add_handler(GBAN_ALERT)
dispatcher.add_handler(PROOF_HANDLER)

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
