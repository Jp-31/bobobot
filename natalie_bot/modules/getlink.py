from typing import List

from telegram import Update, Bot, Chat, Message, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, CallbackContext
from telegram.ext.dispatcher import run_async
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import bot_admin
from natalie_bot.modules.helper_funcs.filters import CustomFilters

from natalie_bot import dispatcher, OWNER_ID, iSUDO_USERS, CMD_PREFIX

@run_async
@bot_admin
def getlink(update: Update, context: CallbackContext):
    if context.args:
        chat_id = int(context.args[0])
    else:
        update.effective_message.reply_text("You don't seem to be referring to a chat")
    chat = context.bot.get_chat(chat_id)
    bot_member = chat.get_member(context.bot.id)
    if bot_member.can_invite_users:
        invitelink = context.bot.exportChatInviteLink(chat_id)
        update.effective_message.reply_text(invitelink)
    else:
        update.effective_message.reply_text("I don't have access to the invite link!")


GETLINK_HANDLER = CustomCommandHandler(CMD_PREFIX, "getlink", getlink, filters=Filters.user(OWNER_ID) | CustomFilters.isudo_filter)

dispatcher.add_handler(GETLINK_HANDLER)
