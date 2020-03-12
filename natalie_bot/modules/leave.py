from telegram import TelegramError, Chat, Message
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler, CallbackContext
from telegram.ext.dispatcher import run_async
from typing import List
from natalie_bot.modules.helper_funcs.filters import CustomFilters
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler

import telegram
from natalie_bot import dispatcher, OWNER_ID, iSUDO_USERS, CMD_PREFIX

@run_async
def leave(update: Update, context: CallbackContext):
    if context.args:
        chat_id = str(context.args[0])
        del context.args[0]
        try:
            context.bot.leave_chat(int(chat_id))
            update.effective_message.reply_text("Left the group successfully!")
        except telegram.TelegramError:
            update.effective_message.reply_text("Attempt failed.")
    else:
        update.effective_message.reply_text("Give me a valid chat id") 

__help__ = ""

__mod_name__ = "Leave"

LEAVE_HANDLER = CustomCommandHandler(CMD_PREFIX, "leave", leave, filters=Filters.user(OWNER_ID) | CustomFilters.isudo_filter)
dispatcher.add_handler(LEAVE_HANDLER)
