import asyncio
import datetime
import html
import telegram
import tg_bot.modules.sql.mention_sql as sql

from typing import Optional, List

from telegram import Message, Chat, Update, Bot, ParseMode, User
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, RegexHandler, run_async
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER

PING_STRING = "<b>{} pinged users for {}:</b>\n"

@run_async
def ping_list(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    msg_user = update.effective_user # Not called user as it will give issues later on.

    print("date: " + str(datetime.datetime.utcnow()))
    last_execution = sql.last_execution(chat.id, datetime.datetime.utcnow())

    if last_execution != False:
        all_handlers = sql.get_ping_list(msg_user.id, chat.id)
        asyncio.sleep(1) # Needed to read the all_handlers length otherwise it wasn't finished fetching the data yet.
        chat_name = chat.title or chat.first or chat.username
        if not all_handlers:
            update.effective_message.reply_text("There are no subscribed members here!")
            return

        ping_list = PING_STRING
        entry = ""
        times = 0
        num = 1
        for i in range(len(all_handlers)):
            if i != 0 and (i % 10) == 0:
                times += 1 # To set from where the remainder needs to get it's data
                for keyword in all_handlers[(i - 10):i]:
                    user = bot.get_chat(keyword["user"])
                    entry = " {},".format(mention_html(user.id, user.first_name))
                    if num%10 == 0:
                        update.effective_message.reply_text(ping_list.format(mention_html(msg_user.id, msg_user.first_name), chat_name), parse_mode=telegram.ParseMode.HTML)
                        ping_list = entry
                    else:
                        ping_list += entry
                    num += 1

            if (i + 1) == len(all_handlers):
                pos = i - (i - 10 * times)
                for keyword in all_handlers[pos:(i + 1)]:
                    user = bot.get_chat(keyword["user"])
                    entry = " {},".format(mention_html(user.id, user.first_name))
                    if keyword == all_handlers[len(all_handlers)-1]:
                        ping_list += entry.strip(entry[-1])
                        ping_list += "\nPinged these users because they are subscribed to /pingme!"
                    else:
                        ping_list += entry
                    num += 1

        if not ping_list == PING_STRING:
            update.effective_message.reply_text(ping_list.format(mention_html(msg_user.id, msg_user.first_name), chat_name), parse_mode=telegram.ParseMode.HTML)
    else:
        update.effective_message.reply_text("Command has been used in the last 10 minutes.\n\nIn terms of Anti-Spam measurements there's a 10 minute cooldown on this command.")
        return

#Pingall
@run_async
def ping(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    ping_txt = "Pinging subscribed users for <b>{}</b>:\n".format(chat.title)
    entry_list = "- {}"
    keyboard = []
    message.reply_text(ping_txt + entry_list, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@run_async
def pingme(bot: Bot, update: Update):
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    subscribe_user = sql.add_mention(user.id, chat.id)

    try:
        user_name = user.first_name + " " + user.last_name
    except:
        user_name = user.first_name

    if subscribe_user == True:
        subs = "{} subscribed to Pinger!".format(user_name)
        keyboard = []
        message.reply_text(subs, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        subs = "You are already subscribed to Pinger."
        keyboard = []
        message.reply_text(subs, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@run_async
def unpingme(bot: Bot, update: Update):
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    unsubscribe_user = sql.remove_mention(user.id, chat.id)

    try:
        user_name = user.first_name + " " + user.last_name
    except:
        user_name = user.first_name

    if unsubscribe_user == True:
        subs = "{} unsubscribed from Pinger.".format(user_name)
        keyboard = []
        message.reply_text(subs, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        subs = "You are not subscribed to Pinger."
        keyboard = []
        message.reply_text(subs, reply_markup=keyboard, parse_mode=ParseMode.HTML)

@run_async
@user_admin
def unping_all(bot: Bot, update: Update):
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    unsubscribe_all_users = sql.reset_all_mentions(user.id, chat.id)

    if unsubscribe_all_users:
        try:
            user_name = user.first_name + " " + user.last_name
        except:
            user_name = user.first_name
        subs = "{} unsubscribed all users from Pinger.".format(mention_html(user.id, user_name))
        keyboard = []
        message.reply_text(subs, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        subs = "There are no users subscribed to Pinger in this chat."
        keyboard = []
        message.reply_text(subs, reply_markup=keyboard, parse_mode=ParseMode.HTML)

__help__ = """
Pinger is an essential feature to mention all subscribed members in the group. \
Any chat members can subscribe to pinger.

 - /pingtime: mention all subscribed members.
 - /pingme: registers to pinger.
 - /unpingme: unsubscribes from pinger.

*Admin only:*
 - /unpingall: clears all subscribed members.
 
*Tip:* Use `/disable pingtime` to turn off /pingtime for everyone except admins.
"""

__mod_name__ = "Pinger"

PINGER_HANDLER = DisableAbleCommandHandler("pingtime", ping_list, admin_ok=True)
PINGERME_HANDLER = CommandHandler("pingme", pingme)
UNPINGERME_HANDLER = CommandHandler("unpingme", unpingme)
UNPINGERALL_HANDLER = CommandHandler("unpingall", unping_all)

dispatcher.add_handler(PINGER_HANDLER)
dispatcher.add_handler(PINGERME_HANDLER)
dispatcher.add_handler(UNPINGERME_HANDLER)
dispatcher.add_handler(UNPINGERALL_HANDLER)
