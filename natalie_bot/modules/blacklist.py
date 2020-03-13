import html
import re
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async, CallbackContext
from telegram.utils.helpers import mention_html

import natalie_bot.modules.sql.blacklist_sql as sql
from natalie_bot import dispatcher, LOGGER, CMD_PREFIX
from natalie_bot.modules.disable import DisableAbleCommandHandler
from natalie_bot.modules.log_channel import loggable
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import user_admin, user_not_admin
from natalie_bot.modules.helper_funcs.extraction import extract_user_and_text, extract_text
from natalie_bot.modules.helper_funcs.misc import split_message

BLACKLIST_GROUP = 11

BASE_BLACKLIST_STRING = "The following blacklist filters are currently active in {}:\n"


@run_async
def blacklist(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    chat_name = chat.title or chat.first or chat.username
    all_blacklisted = sql.get_chat_blacklist(chat.id)
    args = msg.text.split(" ")

    filter_list = BASE_BLACKLIST_STRING

    if len(args) > 1 and args[1].lower() == 'copy':
        for trigger in all_blacklisted:
            filter_list += "<code>{}</code>\n".format(html.escape(trigger))
    else:
        for trigger in all_blacklisted:
            filter_list += " • <code>{}</code>\n".format(html.escape(trigger))

    split_text = split_message(filter_list)
    for text in split_text:
        if text == BASE_BLACKLIST_STRING:
            msg.reply_text("There are no blacklisted messages here!")
            return
        msg.reply_text(text.format(chat_name), parse_mode=ParseMode.HTML)


@run_async
@user_admin
@loggable
def add_blacklist(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user
    words = msg.text.split(None, 1)
    if len(words) > 1:
        text = words[1]
        to_blacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        
        log = "<b>{}:</b>" \
          "\n#BLACKLISTS" \
          "\n<b>• Action:</b> added" \
          "\n<b>• Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, 
                                                                  user.first_name))
        for trigger in to_blacklist:
            sql.add_to_blacklist(chat.id, trigger.lower())

        if len(to_blacklist) == 1:
            msg.reply_text("Added <code>{}</code> to the blacklist!".format(html.escape(to_blacklist[0])),
                           parse_mode=ParseMode.HTML)
            log += "\n<b>• Trigger:</b>\n"
            for trigger in to_blacklist:
               log += "  <code>{}</code>\n".format(trigger)

        else:
            msg.reply_text(
                "Added <code>{}</code> triggers to the blacklist.".format(len(to_blacklist)), parse_mode=ParseMode.HTML)
            num = 1
            log += "\n<b>• Triggers:</b>\n"
            for trigger in to_blacklist:
               log += "  {}. <code>{}</code>\n".format(num, trigger)
               num += 1 
        
        return log

    else:
        msg.reply_text("Tell me which words you would like to add to the blacklist.")


@run_async
@user_admin
@loggable
def unblacklist(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    user = update.effective_user # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    words = msg.text.split(None, 1)
    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        successful = 0
        log = "<b>{}:</b>" \
              "\n#BLACKLISTS" \
              "\n<b>• Action:</b> cleared" \
              "\n<b>• Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, 
                                                                  user.first_name), to_unblacklist)
        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat.id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                msg.reply_text("Removed <code>{}</code> from the blacklist!".format(html.escape(to_unblacklist[0])),
                               parse_mode=ParseMode.HTML)
                log += "\n<b>• Trigger:</b>\n"
                for trigger in to_unblacklist:
                    log += "  <code>{}</code>\n".format(trigger)
            else:
                msg.reply_text("This isn't a blacklisted trigger...!")

        elif successful == len(to_unblacklist):
            msg.reply_text(
                "Removed <code>{}</code> triggers from the blacklist.".format(
                    successful), parse_mode=ParseMode.HTML)
            num = 1
            log += "\n<b>• Triggers:</b>\n"
            for trigger in to_unblacklist:
                log += "  {}. <code>{}</code>\n".format(num, trigger)
                num += 1 

        elif not successful:
            msg.reply_text(
                "None of these triggers exist, so they weren't removed.".format(
                    successful, len(to_unblacklist) - successful), parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "Removed <code>{}</code> triggers from the blacklist. {} did not exist, "
                "so were not removed.".format(successful, len(to_unblacklist) - successful),
                parse_mode=ParseMode.HTML)
        
        return log
    else:
        msg.reply_text("Tell me which words you would like to remove from the blacklist.")


@run_async
@user_not_admin
def del_blacklist(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    to_match = extract_text(message)
    if not to_match:
        return

    chat_filters = sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("Error while deleting blacklist message.")
            break


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return "There are {} blacklisted words.".format(blacklisted)


def __stats__():
    return "{} blacklist triggers, across {} chats.".format(sql.num_blacklist_filters(),
                                                            sql.num_blacklist_filter_chats())


__mod_name__ = "Word Blacklists"

__help__ = """
Blacklists are used to stop certain triggers from being said in a group. Any time the trigger is mentioned, \
the message will immediately be deleted. A good combo is sometimes to pair this up with warn filters!

*NOTE:* blacklists do not affect group admins.

 - /blacklist: View the current blacklisted words.

*Admin only:*
 - /addblacklist <triggers>: Add a trigger to the blacklist. Each line is considered one trigger, so using different \
lines will allow you to add multiple triggers.
 - /unblacklist <triggers>: Remove triggers from the blacklist. Same newline logic applies here, so you can remove \
multiple triggers at once.
 - /rmblacklist <triggers>: Same as above.
 
Tip: To copy list of saved blacklist simply use `/blacklist copy`, {} will send non-bulleted list of blacklist.
""".format(dispatcher.bot.first_name)

BLACKLIST_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "blacklist", blacklist, filters=Filters.group, admin_ok=True)
ADD_BLACKLIST_HANDLER = CustomCommandHandler(CMD_PREFIX, "addblacklist", add_blacklist, filters=Filters.group)
UNBLACKLIST_HANDLER = CustomCommandHandler(CMD_PREFIX, ["unblacklist", "rmblacklist"], unblacklist, filters=Filters.group)
BLACKLIST_DEL_HANDLER = MessageHandler(
    (Filters.text | Filters.command | Filters.sticker | Filters.photo) & Filters.group, del_blacklist)

dispatcher.add_handler(BLACKLIST_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
dispatcher.add_handler(UNBLACKLIST_HANDLER)
dispatcher.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)
