import time
from functools import wraps
from typing import Optional

from telegram import User, Chat, ChatMember, Update, Bot
from telegram.ext import CallbackContext

from natalie_bot import DEL_CMDS, iSUDO_USERS, SUDO_USERS, WHITELIST_USERS, SUPER_ADMINS, LOGGER


def can_delete(chat: Chat, bot_id: int) -> bool:
    return chat.get_member(bot_id).can_delete_messages

def bot_send_messages(chat: Chat, bot_id: int) -> bool:
    return chat.get_member(bot_id).can_send_messages

def is_user_ban_protected(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if chat.type == 'private' \
            or user_id in SUDO_USERS \
            or user_id in iSUDO_USERS \
            or user_id in WHITELIST_USERS \
            or user_id in SUPER_ADMINS \
            or chat.all_members_are_administrators:
        return True

    if not member:
        member = chat.get_member(user_id)
    return member.status in ('administrator', 'creator')


def is_user_admin(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if chat.type == 'private' \
            or user_id in SUDO_USERS \
            or user_id in iSUDO_USERS \
            or user_id in SUPER_ADMINS \
            or chat.all_members_are_administrators:
        return True

    if not member:
        member = chat.get_member(user_id)
    return member.status in ('administrator', 'creator')


def is_bot_admin(chat: Chat, bot_id: int, bot_member: ChatMember = None) -> bool:
    if chat.type == 'private' \
            or chat.all_members_are_administrators:
        return True

    if not bot_member:
        bot_member = chat.get_member(bot_id)
    return bot_member.status in ('administrator', 'creator')


def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    member = chat.get_member(user_id)
    return member.status not in ('left', 'kicked')


def bot_can_delete(func):
    @wraps(func)
    def delete_rights(update: Update, context: CallbackContext, *args, **kwargs):
        if can_delete(update.effective_chat, context.bot.id):
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text("I can't delete messages here! "
                                                "Make sure I'm admin and can delete other user's messages.")

    return delete_rights


def can_pin(func):
    @wraps(func)
    def pin_rights(update: Update, context: CallbackContext, *args, **kwargs):
        if update.effective_chat.get_member(context.bot.id).can_pin_messages:
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text("I can't pin messages here! "
                                                "Make sure I'm admin and can pin messages.")

    return pin_rights


def can_promote(func):
    @wraps(func)
    def promote_rights(update: Update, context: CallbackContext, *args, **kwargs):
        if update.effective_chat.get_member(context.bot.id).can_promote_members:
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text("I can't promote/demote people here! "
                                                "Make sure I'm admin and can appoint new admins.")

    return promote_rights


def can_restrict(func):
    @wraps(func)
    def promote_rights(update: Update, context: CallbackContext, *args, **kwargs):
        if update.effective_chat.get_member(context.bot.id).can_restrict_members:
            return func(update, context, *args, **kwargs)
        else:
            try:
                update.effective_message.reply_text("I can't restrict people here! "
                                                    "Make sure I'm admin and can restrict members.")
            except:
                LOGGER.log(2, "Cannot send messages: Chat ID {}".format(str(update.effective_chat.id)))

    return promote_rights

def can_message(func):
    @wraps(func)
    def send_msg_rights(update: Update, context: CallbackContext, *args, **kwargs):
        is_muted = bot_send_messages(update.effective_chat, context.bot.id)
        if (not is_muted or is_muted == True) and is_muted != False:
            return func(update, context, *args, **kwargs)
        else:
            try:
                context.bot.leave_chat(int(update.effective_chat.id))
                LOGGER.log(2, "Left a group where I was muted.")
            except telegram.TelegramError:
                LOGGER.log(2, "Could not leave chat.")
        
    return send_msg_rights

def bot_admin(func):
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        if is_bot_admin(update.effective_chat, context.bot.id):
            return func(update, context, *args, **kwargs)
        else:
            try:
                update.effective_message.reply_text("I'm not admin!")
            except:
                LOGGER.log(2, "Reply message not found.")

    return is_admin

def user_admin(func):
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        user = update.effective_user  # type: Optional[User]
        message = update.effective_message
        if user and is_user_admin(update.effective_chat, user.id):
            return func(update, context, *args, **kwargs)

        elif not user:
            pass

        elif DEL_CMDS and message.text != None and " " not in message.text:
            update.effective_message.delete()

        else:
            try:
                msg = update.effective_message.reply_text("Who dis non-admin telling me what to do?")
                time.sleep(5)
                msg.delete()
            except:
                LOGGER.log(2, "Reply message not found.")
            

    return is_admin


def user_admin_no_reply(func):
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        user = update.effective_user  # type: Optional[User]
        message = update.effective_message
        if user and is_user_admin(update.effective_chat, user.id):
            return func(update, context, *args, **kwargs)

        elif not user:
            pass

        elif DEL_CMDS and message.text != None and " " not in message.text:
            message.delete()

    return is_admin


def user_not_admin(func):
    @wraps(func)
    def is_not_admin(update: Update, context: CallbackContext, *args, **kwargs):
        user = update.effective_user  # type: Optional[User]
        if user and not is_user_admin(update.effective_chat, user.id):
            return func(update, context, *args, **kwargs)

    return is_not_admin
