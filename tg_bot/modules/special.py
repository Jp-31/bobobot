from io import BytesIO
from time import sleep
from typing import Optional, List
from telegram import TelegramError, Chat, Message
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler, CallbackContext
from telegram.ext.dispatcher import run_async
from tg_bot.modules.helper_funcs.chat_status import is_user_ban_protected

import telegram
import tg_bot.modules.sql.users_sql as sql
from tg_bot import dispatcher, iSUDO_USERS, OWNER_ID, LOGGER, CMD_PREFIX
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.handlers import CustomCommandHandler
from tg_bot.modules.disable import DisableAbleCommandHandler

USERS_GROUP=4
                                                                                                                                                                                                                                                                               
@run_async                                                                                                                                                                                                                                                                     
def quickscope(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(" ")                                                                                                                                                                                                                     
    if args:                                                                                                                                                                                                                                                                   
        chat_id = str(args[2])                                                                                                                                                                                                                                                 
        to_kick = str(args[1])                                                                                                                                                                                                                                                 
    else:                                                                                                                                                                                                                                                                      
        update.effective_message.reply_text("You don't seem to be referring to a chat/user")                                                                                                                                                                                   
    try:                                                                                                                                                                                                                                                                       
        context.bot.kick_chat_member(chat_id, to_kick)                                                                                                                                                                                                                                 
        update.effective_message.reply_text("Attempted banning " + to_kick + " from" + chat_id)                                                                                                                                                                                
    except BadRequest as excp:                                                                                                                                                                                                                                                 
        update.effective_message.reply_text(excp.message + " " + to_kick)                                                                                                                                                                                                      
                                                                                                                                                                                                                                                                               
@run_async                                                                                                                                                                                                                                                                     
def quickunban(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(" ")                                                                                                                                                                                                                     
    if args:                                                                                                                                                                                                                                                                   
        chat_id = str(args[2])                                                                                                                                                                                                                                                 
        to_kick = str(args[1])                                                                                                                                                                                                                                                 
    else:                                                                                                                                                                                                                                                                      
        update.effective_message.reply_text("You don't seem to be referring to a chat/user")                                                                                                                                                                                   
    try:                                                                                                                                                                                                                                                                       
        context.bot.unban_chat_member(chat_id, to_kick)                                                                                                                                                                                                                                
        update.effective_message.reply_text("Attempted unbanning " + to_kick + " from" + chat_id)
    except BadRequest as excp:
        update.effective_message.reply_text(excp.message + " " + to_kick)

@run_async
def banall(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(" ")
    if args:
        chat_id = str(args[1])
        all_mems = sql.get_chat_members(chat_id)
    else:
        chat_id = str(update.effective_chat.id)
        all_mems = sql.get_chat_members(chat_id)
    for mems in all_mems:
        try:
            context.bot.kick_chat_member(chat_id, mems.user)
            update.effective_message.reply_text("Tried banning " + str(mems.user))
            sleep(0.1)
        except BadRequest as excp:
            update.effective_message.reply_text(excp.message + " " + str(mems.user))
            continue


@run_async
def snipe(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(" ")
    try:
        chat_id = str(args[1])
        del args[1]
    except TypeError as excp:
        update.effective_message.reply_text("Please give me a chat to echo to!")
    to_send = " ".join(args)
    if len(to_send) >= 2:
        try:
            context.bot.sendMessage(int(chat_id), str(to_send))
        except TelegramError:
            LOGGER.warning("Couldn't send to group %s", str(chat_id))
            update.effective_message.reply_text("Couldn't send the message. Perhaps I'm not part of that group?")


__help__ = ""  # no help string

__mod_name__ = "Special"

SNIPE_HANDLER = CustomCommandHandler(CMD_PREFIX, "snipe", snipe, filters=CustomFilters.sudo_filter | CustomFilters.isudo_filter)
BANALL_HANDLER = CustomCommandHandler(CMD_PREFIX, "banall", banall, filters=Filters.user(OWNER_ID) | CustomFilters.isudo_filter)
QUICKSCOPE_HANDLER = CustomCommandHandler(CMD_PREFIX, "quickscope", quickscope, filters=CustomFilters.sudo_filter | CustomFilters.isudo_filter)
QUICKUNBAN_HANDLER = CustomCommandHandler(CMD_PREFIX, "quickunban", quickunban, filters=CustomFilters.sudo_filter | CustomFilters.isudo_filter)

dispatcher.add_handler(SNIPE_HANDLER)
dispatcher.add_handler(BANALL_HANDLER)
dispatcher.add_handler(QUICKSCOPE_HANDLER)
dispatcher.add_handler(QUICKUNBAN_HANDLER)
