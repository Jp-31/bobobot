import html, time
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, MessageHandler, Filters, CallbackContext
from telegram.utils.helpers import mention_html

import natalie_bot.modules.sql.global_mutes_sql as sql
from natalie_bot import dispatcher, OWNER_ID, SUPER_ADMINS, SUDO_USERS, EVIDENCES_LOG, SUPPORT_USERS, \
     STRICT_GMUTE, GBAN_LOG, CMD_PREFIX, SPAMWATCH_TOKEN, LOGGER
from natalie_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from natalie_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from natalie_bot.modules.helper_funcs.filters import CustomFilters
from natalie_bot.modules.sql.users_sql import get_all_chats, get_users_by_chat, get_name_by_userid
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler

GMUTE_ENFORCE_GROUP = 8

MUTE_PERMISSIONS = ChatPermissions(can_send_messages=False)

UNMUTE_PERMISSIONS = ChatPermissions(can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)


GMUTE_ERRORS = {
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

UNGMUTE_ERRORS = {
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
def fmute(update: Update, context: CallbackContext):
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
        message.reply_text("I can't silence a support user! Only my creator can!")
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

    if sql.is_user_gmuted(user_id):
        if not reason:
            msg = "User {} is already globally muted; I'd change the reason, " \
                  "but you haven't given me one...".format(mention_html(user_chat.id, user_chat.first_name 
                                                                        or "Deleted Account"))

            message.reply_text(msg, parse_mode=ParseMode.HTML)
            return

        old_reason = sql.update_gmute_reason(user_id, user_chat.username or user_chat.first_name, reason)
        user_id, new_reason = extract_user_and_text(message, args)
        
        if old_reason == new_reason:
            same_reason = "User {} has already been globally muted, with the " \
                          "exact same reason.".format(mention_html(user_chat.id, user_chat.first_name or  
                                                                   "Deleted Account"))
            
            message.reply_text(same_reason, parse_mode=ParseMode.HTML)
            return
        
        if old_reason:
            muter = update.effective_user  # type: Optional[User]
            send_gmute = "<b>Emendation of Global mute</b>" \
                        "\n#GMUTE" \
                        "\n<b>Status:</b> <code>Amended</code>" \
                        "\n<b>Name:</b> {}".format(mention_html(user_chat.id, user_chat.first_name or 
                                                                "Deleted Account"))
    
            if user_chat.last_name:
                send_gmute += "\n<b>Surname:</b> {}".format(mention_html(user_chat.id, user_chat.last_name))
            
            if user_chat.username:
                send_gmute += "\n<b>Username:</b> @{}".format(html.escape(user_chat.username))
            
            if  user_chat:
                send_gmute += "\n<b>ID:</b> <code>{}</code>".format(user_chat.id)
            
            if muter.id in SUDO_USERS:
                send_gmute += "\n<b>Sudo:</b> {}".format(mention_html(muter.id, muter.first_name))
            
            if muter.id in SUPPORT_USERS:
                send_gmute += "\n<b>Support:</b> {}".format(mention_html(muter.id, muter.first_name))
            
            if reason:
                send_gmute += "\n<b>Previous:</b> {}".format(old_reason)
                send_gmute += "\n<b>Amended:</b> {}".format(new_reason)
            
            context.bot.send_message(chat_id=GBAN_LOG, text=send_gmute, parse_mode=ParseMode.HTML)
            old_msg = "User {} is already globally muted, for the following reason:\n" \
                      "<code>{}</code>\n" \
                      "I've gone and updated it with your new reason!".format(mention_html(user_chat.id, 
                                                                              user_chat.first_name or "Deleted Account"), 
                                                                              old_reason)

            message.reply_text(old_msg, parse_mode=ParseMode.HTML)
        
        else:
            muter = update.effective_user  # type: Optional[User]
            send_gmute = "<b>Emendation of Global mute</b>" \
                        "\n#GMUTE" \
                        "\n<b>Status:</b> <code>New reason</code>" \
                        "\n<b>Name:</b> {}".format(mention_html(user_chat.id, user_chat.first_name or 
                                                                "Deleted Account"))
    
            if user_chat.last_name:
                send_gmute += "\n<b>Surname:</b> {}".format(mention_html(user_chat.id, user_chat.last_name))
            
            if user_chat.username:
                send_gmute += "\n<b>Username:</b> @{}".format(html.escape(user_chat.username))
            
            if  user_chat:
                send_gmute += "\n<b>ID:</b> <code>{}</code>".format(user_chat.id)
            
            if muter.id in SUDO_USERS:
                send_gmute += "\n<b>Sudo:</b> {}".format(mention_html(muter.id, muter.first_name))
            
            if muter.id in SUPPORT_USERS:
                send_gmute += "\n<b>Support:</b> {}".format(mention_html(muter.id, muter.first_name))
            
            if reason:
                send_gmute += "\n<b>Reason:</b> {}".format(new_reason)
            
            context.bot.send_message(chat_id=GBAN_LOG, text=send_gmute, parse_mode=ParseMode.HTML)
            msg = "User {} is already globally muted, but had no reason set; " \
                  "I've gone and updated it!".format(mention_html(user_chat.id, user_chat.first_name or "Deleted Account"))

            message.reply_text(msg, parse_mode=ParseMode.HTML)

        return

    starting = "Starting global mutes for {}...".format(mention_html(user_chat.id, user_chat.first_name or "Deleted Account"))

    message.reply_text(starting, parse_mode=ParseMode.HTML)
    
    muter = update.effective_user  # type: Optional[User]
    send_gmute = "<b>Global mute</b>" \
                "\n#GMUTE" \
                "\n<b>Status:</b> <code>Enforced</code>" \
                "\n<b>Name:</b> {}".format(mention_html(user_chat.id, user_chat.first_name or "Deleted Account"))
    
    if user_chat.last_name:
        send_gmute += "\n<b>Surname:</b> {}".format(mention_html(user_chat.id, user_chat.last_name))
    
    if user_chat.username:
        send_gmute += "\n<b>Username:</b> @{}".format(html.escape(user_chat.username))
    
    if  user_chat:
        send_gmute += "\n<b>ID:</b> <code>{}</code>".format(user_chat.id)
    
    if muter.id in SUDO_USERS:
        send_gmute += "\n<b>Sudo:</b> {}".format(mention_html(muter.id, muter.first_name))
    
    if muter.id in SUPPORT_USERS:
        send_gmute += "\n<b>Support:</b> {}".format(mention_html(muter.id, muter.first_name))
    
    if reason:
        send_gmute += "\n<b>Reason:</b> {}".format(reason)
             

    context.bot.send_message(chat_id=GBAN_LOG, text=send_gmute, parse_mode=ParseMode.HTML)
    sql.gmute_user(user_id, user_chat.username or user_chat.first_name, reason)
    
    fmute_id = update.effective_chat  # type: Optional[Chat]
    chats = get_users_by_chat(fmute_id.id, user_id)
    for chat in chats:
        chat_id = chat.chat

        # Check if this group has disabled gmutes
        if not sql.does_chat_gmute(chat_id):
            continue

        try:
            context.bot.restrict_chat_member(update.effective_chat.id, int(user_id), MUTE_PERMISSIONS)
        except BadRequest as excp:
            if excp.message in GMUTE_ERRORS:
                pass
            else:
                message.reply_text("Could not fmute due to: {}".format(excp.message))
                sql.ungmute_user(user_id)
                return
        except TelegramError:
            pass
    
    silence_t = "User {} has been successfully globally muted".format(mention_html(user_chat.id, user_chat.first_name or 
                                                               "Deleted Account"))

    context.bot.send_message(chat_id=GBAN_LOG, text=silence_t, parse_mode=ParseMode.HTML)
    message.reply_text("User {} has been globally muted!".format(mention_html(user_chat.id, user_chat.first_name 
                                                            or "Deleted Account")), parse_mode=ParseMode.HTML)


@run_async
def ungmute(update: Update, context: CallbackContext):
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

    if not sql.is_user_gmuted(user_id):
        msg = "User {} is not globally muted!".format(mention_html(user_chat.id, user_chat.first_name 
                                                                         or "Deleted Account"))
        
        message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    muter = update.effective_user  # type: Optional[User]

    message.reply_text("Removing {} from global mutes.".format(user_chat.first_name or "Deleted Account"))

    send_gmute = "<b>Regression of Global mute</b>" \
                "\n#GMUTE" \
                "\n<b>Status:</b> <code>Ceased</code>" \
                "\n<b>Name:</b> {}".format(mention_html(user_chat.id, user_chat.first_name or "Deleted Account"))
    
    if user_chat.last_name:
        send_gmute += "\n<b>Surname:</b> {}".format(mention_html(user_chat.id, user_chat.last_name))
    
    if user_chat.username:
        send_gmute += "\n<b>Username:</b> @{}".format(html.escape(user_chat.username))
    
    if  user_chat:
        send_gmute += "\n<b>ID:</b> <code>{}</code>".format(user_chat.id)
    
    if muter.id in SUDO_USERS:
        send_gmute += "\n<b>Sudo:</b> {}".format(mention_html(muter.id, muter.first_name))
    
    if muter.id in SUPPORT_USERS:
        send_gmute += "\n<b>Support:</b> {}".format(mention_html(muter.id, muter.first_name))
            
   
    context.bot.send_message(chat_id=GBAN_LOG, text=send_gmute, parse_mode=ParseMode.HTML)
    
    unfmute_id = update.effective_chat  # type: Optional[Chat]
    chats = get_users_by_chat(unfmute_id.id, user_id)
    for chat in chats:
        chat_id = chat.chat

        # Check if this group has disabled gmutes
        if not sql.does_chat_gmute(chat_id):
            continue

        try:
            member = context.bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                context.bot.restrict_chat_member(update.effective_chat.id, int(user_id), UNMUTE_PERMISSIONS)

        except BadRequest as excp:
            if excp.message in UNGMUTE_ERRORS:
                pass
            else:
                message.reply_text("Could not un-gmute due to: {}".format(excp.message))
                context.bot.send_message(OWNER_ID, "Could not un-gmute due to: {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungmute_user(user_id)
    
    silence_t = "User {} has been pardoned from global mutes.".format(mention_html(user_chat.id, user_chat.first_name or 
                                                                                     "Deleted Account"))
    
    context.bot.send_message(chat_id=GBAN_LOG, text=silence_t, parse_mode=ParseMode.HTML)
    message.reply_text("User {} has been pardoned from global mutes.".format(mention_html(user_chat.id, user_chat.first_name 
                                                               or "Deleted Account")), parse_mode=ParseMode.HTML)

@run_async
def gmutelist(update: Update, context: CallbackContext):
    muted_users = sql.get_gmute_list()

    if not muted_users:
        update.effective_message.reply_text("There aren't any gmuted users! You're kinder than I expected...")
        return

    mutefile = 'Screw these guys.\n'
    for user in muted_users:
        mutefile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            mutefile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(mutefile)) as output:
        output.name = "gmutelist.txt"
        update.effective_message.reply_document(document=output, filename="gmutelist.txt",
                                                caption="Here is the list of currently gmuted users.")


def gmute_notification(update: Update, context: CallbackContext, user_id, should_message=False):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    user = context.bot.get_chat(user_id)
    user_r = sql.get_gmuted_user(user_id)
    
    
    chatmute_text = "User {} is currently globally muted and is silenced from {} with an " \
                   "immediate effect.".format(mention_html(user.id, user.first_name or "Deleted Account"), chat.title)
    
    if sql.is_user_gmuted(user_id):
        if user_r.reason:
            chatmute_text += "\n<b>Reason</b>: {}".format(user_r.reason)
                
        if should_message:
            try:
                msg.reply_text(chatmute_text, parse_mode=ParseMode.HTML)
            except:
                context.bot.send_message(chat.id, 
                                         chatmute_text, parse_mode=ParseMode.HTML)
                LOGGER.exception()

def check_and_mute(update, context, user_id):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message
    
    if sql.is_user_gmuted(user_id):
        context.bot.restrict_chat_member(update.effective_chat.id, int(user_id), MUTE_PERMISSIONS)

def welcome_gmute(update, context, user_id):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message
           
    if sql.is_user_gmuted(user_id):
        context.bot.restrict_chat_member(update.effective_chat.id, int(user_id), MUTE_PERMISSIONS)

@run_async
def enforce_gmute(update: Update, context: CallbackContext):
    # Not using @restrict handler to avoid spamming - just ignore if cant gmute.
    if sql.does_chat_gmute(update.effective_chat.id) and update.effective_chat.get_member(context.bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]
        gmute_alert = sql.get_gmute_alert(chat.id)
        new_members = update.effective_message.new_chat_members

        if user and not is_user_admin(chat, user.id):
            check_and_mute(update, context, user.id)
            
        if msg.text:
            if user and not is_user_admin(chat, user.id):
                check_and_mute(update, context, user.id)
                
                if gmute_alert:
                    gmute_notification(update, context, user.id,
                                  should_message=True)
                
        elif msg.new_chat_members:
            for mem in new_members:
                welcome_gmute(update, context, mem.id)
                if gmute_alert:
                    gmute_notification(update, context, mem.id,
                                  should_message=True)
                    
        elif new_members:
            for mem in new_members:
                welcome_gmute(update, context, mem.id)
                if gmute_alert:
                    gmute_notification(update, context, user.id,
                                  should_message=True)
                

@run_async
@user_admin
def gmutealert(update: Update, context: CallbackContext):
    chat = update.effective_chat
    args = update.effective_message.text.split(" ")
    args_option = ""
    bot = context.bot
    
    if len(args) > 1:
        args_option = args[1].lower()
        
    if len(args) > 1:
        if args_option != "" and args_option in ["on", "yes"]:
            sql.enable_alert(chat.id)
            update.effective_message.reply_text("Global mute notification is <code>enabled</code> for {}.".format(chat.title),
                                                 parse_mode=ParseMode.HTML)
        elif args_option != "" and args_option in ["off", "no"]:
            sql.disable_alert(chat.id)
            update.effective_message.reply_text("Global mute notification is <code>disabled</code> for {}.".format(chat.title),
                                                 parse_mode=ParseMode.HTML)
        else:
            update.effective_message.reply_text("Unknown Type command. I only understand on/yes or off/no!")
    else:
        alert = sql.does_chat_alert(chat.id)
        if not alert:
            aler_txt = "Global mute notifications are currently <code>enabled</code>; whenever a user " \
                       "that is muted in {} joins or speaks in {}, they will be silenced, " \
                       "along with a message " \
                       "explaining why.".format(bot.first_name, chat.title)
            update.effective_message.reply_text(aler_txt, parse_mode=ParseMode.HTML)
        else:
            aler_txt = "Global mute notifications are currently <code>disable</code>; whenever a user " \
                       "that is muted in {} joins or speaks in {}, they will be quietly silenced.".format(bot.first_name, 
                                                                                                          chat.title)
            update.effective_message.reply_text(aler_txt, parse_mode=ParseMode.HTML)
        


@run_async
@user_admin
def gmutestat(update: Update, context: CallbackContext):
    chat = update.effective_chat
    args = update.effective_message.text.split(" ")
    args_option = ""
    
    if len(args) > 1:
        args_option = args[1].lower()
        
    if len(args) >= 2:
        if args_option != "" and args_option in ["on", "yes"]:
            sql.enable_gmutes(update.effective_chat.id)
            update.effective_message.reply_text("I've enabled gmutes for {}. This will help protect you "
                                                "from spammers, unsavoury characters, and "
                                                "the biggest trolls.".format(chat.title))
        elif args_option != "" and args_option in ["off", "no"]:
            sql.disable_gmutes(update.effective_chat.id)
            update.effective_message.reply_text("I've disabled gmutes for {}. Global mute wont affect your users "
                                                "anymore. You'll be less protected from any trolls and spammers "
                                                "though!".format(chat.title))
    else:
        update.effective_message.reply_text("Give me some arguments to choose a setting! on/off, yes/no!\n\n"
                                            "Your current setting is: {}\n"
                                            "When True, any gmutes that happen will also happen in your group. "
                                            "When False, they won't, leaving you at the possible mercy of "
                                            "spammers.".format(sql.does_chat_gmute(update.effective_chat.id)))


def __stats__():
    return "{} gmuted users.".format(sql.num_gmuted_users())


def __user_info__(user_id):
    gmuted = sql.is_user_gmuted(user_id)
    user = sql.get_gmuted_user(user_id)
    text =""

    if gmuted:
        text = "This user is currently globally muted."
        if user.reason:
            text += "\nReason: {}".format(html.escape(user.reason))
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "This chat is enforcing *gmutes*: `{}`.".format(sql.does_chat_gmute(chat_id))


__help__ = """
It's all fun and games, until you start getting spammers in, and you need to mute them. Then you need to start \
muting more, and more, and it gets painful. With Global muting enforcing in your chat, {}'s admins actively \
muting spammers, trolls and unsavoury characters.

Global mutes will actively engage in muting spammers, you'd have to worry-less on spammers joining in and {} will \
remove them from your group quickly as possible.

You can disable the Global mutes by `/gmutestat off` or enable `/gmutestat on`.

*Admin only:*
 - /gmutestat <on/off/yes/no>: Will disable the effect of global mutes on your group, or return your current settings.
 - /gmutealert <on/off/yes/no>: Whether or not send global mute notification in the chat upon user join/speak in the chat.
""".format(dispatcher.bot.first_name, dispatcher.bot.first_name)

__mod_name__ = "Global Mutes"

GMUTE_HANDLER = CustomCommandHandler(CMD_PREFIX, ["fmute", "gmute"], fmute,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGMUTE_HANDLER = CustomCommandHandler(CMD_PREFIX, ["unfmute", "ungmute"], ungmute,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GMUTE_LIST = CustomCommandHandler(CMD_PREFIX, "gmutelist", gmutelist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
                           
GMUTE_STATUS = CustomCommandHandler(CMD_PREFIX, "gmutestat", gmutestat, filters=Filters.group)
GMUTE_ALERT = CustomCommandHandler(CMD_PREFIX, "gmutealert", gmutealert, filters=Filters.group)

GMUTE_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gmute)

dispatcher.add_handler(GMUTE_HANDLER)
dispatcher.add_handler(UNGMUTE_HANDLER)
dispatcher.add_handler(GMUTE_LIST)
dispatcher.add_handler(GMUTE_STATUS)
dispatcher.add_handler(GMUTE_ALERT)

if STRICT_GMUTE:  # enforce GMUTES if this is set
    dispatcher.add_handler(GMUTE_ENFORCER, GMUTE_ENFORCE_GROUP)
