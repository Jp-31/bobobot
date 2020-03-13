import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, CallbackContext
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery, ChatPermissions

from natalie_bot import dispatcher, LOGGER, CMD_PREFIX
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_admin, can_restrict
from natalie_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from natalie_bot.modules.helper_funcs.string_handling import extract_time
from natalie_bot.modules.log_channel import loggable

MUTE_PERMISSIONS = ChatPermissions(can_send_messages=False)

UNMUTE_PERMISSIONS = ChatPermissions(can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)

MEDIA_PERMISSIONS = ChatPermissions(can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_polls=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)

NOMEDIA_PERMISSIONS = ChatPermissions(can_send_messages=True,
                                     can_send_media_messages=False,
                                     can_send_polls=False,
                                     can_send_other_messages=False,
                                     can_add_web_page_previews=False)

@run_async
@bot_admin
@user_admin
@loggable
def mute(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = message.text.split(" ")

    user_id, reason = extract_user_and_text(message, args)
    if not user_id:
        message.reply_text("You'll need to either give me a username to mute, or reply to someone to be muted.")
        return ""

    if user_id == context.bot.id:
        message.reply_text("I'm not muting myself!")
        return ""

    member = chat.get_member(int(user_id))

    if member:
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("Afraid I can't stop an admin from talking!")

        elif member.can_send_messages is None or member.can_send_messages:
            log = "<b>{}:</b>" \
                   "\n#MUTE" \
                   "\n<b>• Admin:</b> {}" \
                   "\n<b>• User:</b> {}" \
                   "\n<b>• ID:</b> <code>{}</code>".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name), user_id)
            reply = "Shh!\n{} is muted!".format(mention_html(member.user.id, member.user.first_name))
            if reason:
                log += "\n<b>• Reason:</b> {}".format(reason)
                reply += "\n<b>Reason:</b> <i>{}</i>".format(reason)
            context.bot.restrict_chat_member(chat.id, user_id, MUTE_PERMISSIONS)
            
            message.reply_text(reply, parse_mode=ParseMode.HTML)
            
            return log

        else:
            message.reply_text("This user is already muted!")
    else:
        message.reply_text("This user isn't in the chat!")

    return ""


@run_async
@bot_admin
@user_admin
@loggable
def unmute(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = message.text.split(" ")

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You'll need to either give me a username to unmute, or reply to someone to be unmuted.")
        return ""

    member = chat.get_member(int(user_id))

    if member.status != 'kicked' and member.status != 'left':
        if member.can_send_messages and member.can_send_media_messages \
                and member.can_send_other_messages and member.can_add_web_page_previews:
            message.reply_text("This user already has the right to speak.")
        else:
            context.bot.restrict_chat_member(chat.id, int(user_id), UNMUTE_PERMISSIONS)
            
            reply = "Yep, {} can start talking again!".format(mention_html(member.user.id, member.user.first_name))
            message.reply_text(reply, parse_mode=ParseMode.HTML)
            return "<b>{}:</b>" \
                   "\n#UNMUTE" \
                   "\n<b>• Admin:</b> {}" \
                   "\n<b>• User:</b> {}" \
                   "\n<b>• ID:</b> <code>{}</code>".format(html.escape(chat.title),
                                                           mention_html(user.id, user.first_name),
                                                           mention_html(member.user.id, member.user.first_name), user_id)
    else:
        message.reply_text("This user isn't even in the chat, unmuting them won't make them talk more than they "
                           "already do!")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_mute(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = message.text.split(" ")

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("I can't seem to find this user")
            return ""
        else:
            raise

    if is_user_admin(chat, user_id, member):
        message.reply_text("I really wish I could mute admins...")
        return ""

    if user_id == context.bot.id:
        message.reply_text("I'm not gonna MUTE myself, are you crazy?")
        return ""

    if not reason:
        message.reply_text("You haven't specified a time to mute this user for!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP MUTED" \
          "\n<b>• Admin:</b> {}" \
          "\n<b>• User:</b> {}" \
          "\n<b>• ID:</b> <code>{}</code>" \
          "\n<b>• Time:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                       mention_html(member.user.id, member.user.first_name), user_id, time_val)
    if reason:
        log += "\n<b>• Reason:</b> {}".format(reason)

    try:
        if member.can_send_messages is None or member.can_send_messages:
            context.bot.restrict_chat_member(chat.id, user_id, MUTE_PERMISSIONS, until_date=mutetime)
            message.reply_text("{} muted for {}!".format(mention_html(member.user.id, member.user.first_name), time_val),
                               parse_mode=ParseMode.HTML)
            return log
        else:
            message.reply_text("This user is already muted.")

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text("{} muted for {}!".format(mention_html(member.user.id, member.user.first_name), time_val),
                                                         parse_mode=ParseMode.HTML, quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR muting user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Well damn, I can't mute that user.")

    return ""

@run_async
@bot_admin
@user_admin
@loggable
def nomedia(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = message.text.split(" ")

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You'll need to either give me a username to restrict, or reply to someone to be restricted.")
        return ""

    if user_id == context.bot.id:
        message.reply_text("I'm not restricting myself!")
        return ""

    member = chat.get_member(int(user_id))

    if member:
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("Afraid I can't restrict admins!")

        elif member.can_send_messages is None or member.can_send_messages:
            context.bot.restrict_chat_member(chat.id, user_id, NOMEDIA_PERMISSIONS)
            
            reply = "{} is restricted from sending media!".format(mention_html(member.user.id, member.user.first_name))
            message.reply_text(reply, parse_mode=ParseMode.HTML)
            return "<b>{}:</b>" \
                   "\n#RESTRICTED" \
                   "\n<b>• Admin:</b> {}" \
                   "\n<b>• User:</b> {}" \
                   "\n<b>• ID:</b> <code>{}</code>".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name), user_id)

        else:
            message.reply_text("This user is already restricted!")
    else:
        message.reply_text("This user isn't in the chat!")

    return ""

@run_async
@bot_admin
@user_admin
@loggable
def media(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = message.text.split(" ")

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You'll need to either give me a username to unrestrict, or reply to someone to be unrestricted.")
        return ""

    member = chat.get_member(int(user_id))

    if member.status != 'kicked' and member.status != 'left':
        if member.can_send_messages and member.can_send_media_messages \
                and member.can_send_other_messages and member.can_add_web_page_previews:
            message.reply_text("This user already has the rights to send anything.")
        else:
            context.bot.restrict_chat_member(chat.id, int(user_id), MEDIA_PERMISSIONS)
            
            reply = "Yep, {} can send media again!".format(mention_html(member.user.id, member.user.first_name))
            message.reply_text(reply, parse_mode=ParseMode.HTML)
            return "<b>{}:</b>" \
                   "\n#UNRESTRICTED" \
                   "\n<b>• Admin:</b> {}" \
                   "\n<b>• User:</b> {}" \
                   "\n<b>• ID:</b> <code>{}</code>".format(html.escape(chat.title),
                                                           mention_html(user.id, user.first_name),
                                                           mention_html(member.user.id, member.user.first_name), user_id)
    else:
        message.reply_text("This user isn't even in the chat, unrestricting them won't make them send anything than they "
                           "already do!")

    return ""

@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_nomedia(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = message.text.split(" ")

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("I can't seem to find this user")
            return ""
        else:
            raise

    if is_user_admin(chat, user_id, member):
        message.reply_text("I really wish I could restrict admins...")
        return ""

    if user_id == context.bot.id:
        message.reply_text("I'm not gonna RESTRICT myself, are you crazy?")
        return ""

    if not reason:
        message.reply_text("You haven't specified a time to restrict this user for!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP RESTRICTED" \
          "\n<b>• Admin:</b> {}" \
          "\n<b>• User:</b> {}" \
          "\n<b>• ID:</b> <code>{}</code>" \
          "\n<b>• Time:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                       mention_html(member.user.id, member.user.first_name), user_id, time_val)
    if reason:
        log += "\n<b>• Reason:</b> {}".format(reason)

    try:
        if member.can_send_messages is None or member.can_send_messages:
            context.bot.restrict_chat_member(chat.id, user_id, NOMEDIA_PERMISSIONS, until_date=mutetime)
            message.reply_text("{} restricted from sending media for {}!".format(mention_html(member.user.id, 
                                                                                 member.user.first_name), time_val), 
                                                                                 parse_mode=ParseMode.HTML)
            return log
        else:
            message.reply_text("This user is already restricted.")

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text("{} restricted from sending media for {}!".format(mention_html(member.user.id, 
                                                                                 member.user.first_name), time_val), 
                                                                                 parse_mode=ParseMode.HTML, quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR muting user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Well damn, I can't restrict that user.")

    return ""

@run_async
@bot_admin
@user_admin
@loggable
def smute(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = message.text.split(" ")
    
    update.effective_message.delete()
    user_id, reason = extract_user_and_text(message, args)
    if not user_id:
        return ""

    if user_id == context.bot.id:
        message.reply_text("Really?! You're not supposed silent mute me!")
        return ""

    member = chat.get_member(int(user_id))

    if member:
        if is_user_admin(chat, user_id, member=member):
           return ""

        elif member.can_send_messages is None or member.can_send_messages:
            context.bot.restrict_chat_member(chat.id, user_id, MUTE_PERMISSIONS)
            log = "<b>{}:</b>" \
                   "\n#SILENT_MUTE" \
                   "\n<b>• Admin:</b> {}" \
                   "\n<b>• User:</b> {}" \
                   "\n<b>• ID:</b> <code>{}</code>".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name), user_id)
            if reason:
               log += "\n<b>• Reason:</b> {}".format(reason)
            return log

    return ""

__help__ = ""


__mod_name__ = "Muting & Restricting"

MUTE_HANDLER = CustomCommandHandler(CMD_PREFIX, "mute", mute, filters=Filters.group)
SMUTE_HANDLER = CustomCommandHandler(CMD_PREFIX, "smute", smute, filters=Filters.group)
UNMUTE_HANDLER = CustomCommandHandler(CMD_PREFIX, "unmute", unmute, filters=Filters.group)
TEMPMUTE_HANDLER = CustomCommandHandler(CMD_PREFIX, ["tmute", "tempmute"], temp_mute, filters=Filters.group)
TEMP_NOMEDIA_HANDLER = CustomCommandHandler(CMD_PREFIX, ["trestrict", "temprestrict"], temp_nomedia, filters=Filters.group)
NOMEDIA_HANDLER = CustomCommandHandler(CMD_PREFIX, ["restrict", "nomedia"], nomedia, filters=Filters.group)
MEDIA_HANDLER = CustomCommandHandler(CMD_PREFIX, "unrestrict", media, filters=Filters.group)

dispatcher.add_handler(MUTE_HANDLER)
dispatcher.add_handler(SMUTE_HANDLER)
dispatcher.add_handler(UNMUTE_HANDLER)
dispatcher.add_handler(TEMPMUTE_HANDLER)
dispatcher.add_handler(TEMP_NOMEDIA_HANDLER)
dispatcher.add_handler(NOMEDIA_HANDLER)
dispatcher.add_handler(MEDIA_HANDLER)
