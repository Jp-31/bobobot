import html
from telegram import Message, Update, Bot, User, Chat, ParseMode
from typing import List, Optional
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.utils.helpers import mention_html
from tg_bot import dispatcher, OWNER_ID, iSUDO_USERS, SUDO_USERS, SUPPORT_USERS, STRICT_GBAN, CMD_PREFIX
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GKICK_ERRORS = {
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
    "Not in the chat",
    "Method is available for supergroup and channel chats only",
    "Reply message not found"
}

@run_async
def gkick(update: Update, context: CallbackContext):
    message = update.effective_message
    args = message.text.split(" ")
    user_id = extract_user(message, args)
    try:
        user_chat = context.bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message in GKICK_ERRORS:
            pass
        else:
            message.reply_text("User cannot be Globally kicked because: {}".format(excp.message))
            return
    except TelegramError:
            pass

    if not user_id:
        message.reply_text("You do not seems to be referring to a user")
        return
    if int(user_id) in SUDO_USERS or int(user_id) in SUPPORT_USERS:
        message.reply_text("OHHH! Someone's trying to gkick a sudo/support user! *Grabs popcorn*")
        return

    if int(user_id) == OWNER_ID:
        message.reply_text("Wow! Someone's so noob that he want to gkick my owner! *Grabs Potato Chips*")
        return

    if user_id == context.bot.id:
        message.reply_text("Welp, I'm not gonna to gkick myself!")
        return


    if int(user_id) in iSUDO_USERS:
        message.reply_text("")
        return

    chats = get_all_chats()
    banner = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "<b>Global Kick</b>" \
                 "\n#GKICK" \
                 "\n<b>Status:</b> <code>Enforcing</code>" \
                 "\n<b>Sudo Admin:</b> {}" \
                 "\n<b>User:</b> {}" \
                 "\n<b>ID:</b> <code>{}</code>".format(mention_html(banner.id, banner.first_name),
                                              mention_html(user_chat.id, user_chat.first_name), 
                                                           user_chat.id), 
                html=True)
    message.reply_text("Globally kicking user @{}".format(user_chat.username))
    for chat in chats:
        try:
             context.bot.unban_chat_member(chat.chat_id, user_id)  # Unban_member = kick (and not ban)
        except BadRequest as excp:
            if excp.message in GKICK_ERRORS:
                pass
            else:
                message.reply_text("User cannot be Globally kicked because: {}".format(excp.message))
                return
        except TelegramError:
            pass
        
@run_async
@user_admin
def gkickstat(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(" ")
    if len(args) > 0:
        if args[1].lower() in ["on", "yes"]:
            sql.enable_gkick(update.effective_chat.id)
            update.effective_message.reply_text("I've enabled gkicks in this group. This will help protect you "
                                                "from spammers and unsavoury characters.")
        elif args[1].lower() in ["off", "no"]:
            sql.disable_gkick(update.effective_chat.id)
            update.effective_message.reply_text("I've disabled gkicks in this group. GKicks wont affect your users "
                                                "anymore. You'll be less protected from spammers though!")
    else:
        update.effective_message.reply_text("Give me some arguments to choose a setting! on/off, yes/no!\n\n"
                                            "Your current setting is: {}\n"
                                            "When True, any gkicks that happen will also happen in your group. "
                                            "When False, they won't, leaving you at the possible mercy of "
                                            "spammers.".format(sql.does_chat_gkick(update.effective_chat.id)))

__help__ = """
*Admin only:*
 - /gkickstat <on/off/yes/no>: Will disable the effect of global kicks on your group, or return your current settings.
Gkick, also known as global kicks, are used by the bot owners to kick spammers across all groups. This helps protect \
you and your groups by removing spam flooders as quickly as possible. They can be disabled for you group by calling \
/gkickstat
"""

__mod_name__ = "Global Kicks"

GKICK_HANDLER = CommandHandler(CMD_PREFIX, "gkick", gkick,
                              filters=CustomFilters.sudo_filter | CustomFilters.isudo_filter | CustomFilters.support_filter)

GKICK_STATUS = CommandHandler(CMD_PREFIX, "gkickstat", gkickstat, filters=Filters.group)

dispatcher.add_handler(GKICK_HANDLER)
dispatcher.add_handler(GKICK_STATUS)
