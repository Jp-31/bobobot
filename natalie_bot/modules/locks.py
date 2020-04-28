import html, time
from typing import Optional, List

import telegram.ext as tg
from telegram import Message, Chat, Update, Bot, ParseMode, User, MessageEntity, ChatPermissions
from telegram import TelegramError
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackContext, PrefixHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from alphabet_detector import AlphabetDetector

import natalie_bot.modules.sql.locks_sql as sql
from natalie_bot import dispatcher, SUDO_USERS, LOGGER, CMD_PREFIX
from natalie_bot.modules.disable import DisableAbleCommandHandler
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import can_delete, is_user_admin, user_not_admin, user_admin, \
    bot_can_delete, is_bot_admin
from natalie_bot.modules.helper_funcs.filters import CustomFilters
from natalie_bot.modules.log_channel import loggable
from natalie_bot.modules.sql import users_sql
from natalie_bot.modules.sql.urlwhitelist_sql import get_whitelisted_urls

ad = AlphabetDetector()

LOCK_PERMISSIONS = ChatPermissions(can_send_messages=False)

UNLOCK_PERMISSIONS = ChatPermissions(can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True,
                                     can_send_polls=True)

LOCK_TYPES = {'sticker': Filters.sticker,
              'animatedsticker': CustomFilters.animated_sticker,
              'audio': Filters.audio,
              'poll': Filters.poll,
              'voice': Filters.voice,
              'document': Filters.document,
              'video': Filters.video,
              'videonote': Filters.video_note,
              'contact': Filters.contact,
              'command': Filters.command,
              'photo': Filters.photo,
              'gif': Filters.document & CustomFilters.mime_type("video/mp4"),
              'apk': Filters.document.mime_type("application/vnd.android.package-archive"),
              'url': Filters.entity(MessageEntity.URL) | Filters.caption_entity(MessageEntity.URL),
              'email': Filters.entity(MessageEntity.EMAIL) | Filters.caption_entity(MessageEntity.EMAIL),
              'bots': Filters.status_update.new_chat_members,
              'forward': Filters.forwarded,
              'game': Filters.game,
              'location': Filters.location,
              'rtl': 'rtl',
              }

GIF = Filters.document & CustomFilters.mime_type("video/mp4")
OTHER = Filters.game | Filters.sticker | GIF
MEDIA = Filters.audio | Filters.document | Filters.video | Filters.video_note | Filters.voice \
        | Filters.photo | Filters.document.mime_type("application/vnd.android.package-archive")
MESSAGES = Filters.text | Filters.contact | Filters.poll | Filters.location | Filters.venue | Filters.command | MEDIA | OTHER
PREVIEWS = Filters.entity("url")

RESTRICTION_TYPES = {'messages': MESSAGES,
                     'media': MEDIA,
                     'other': OTHER,
                     # 'previews': PREVIEWS, # NOTE: this has been removed cos its useless atm.
                     'all': Filters.all}

PERM_GROUP = 1
REST_GROUP = 2


class CustomCommandHandler(tg.PrefixHandler):
    def __init__(self, prefix, command, callback, **kwargs):
        super().__init__(prefix, command, callback, **kwargs)

    def check_update(self, update: Update):
        if isinstance(update, Update) and update.effective_message:
            message = update.effective_message

            if message.text:
                sql_result = (
                    sql.is_restr_locked(update.effective_chat.id, 'messages') and not is_user_admin(update.effective_chat,
                                                                                                    update.effective_user.id))
                text_list = message.text.split()
                if text_list[0].split("@")[0].lower() in self.command and len(text_list[0].split("@")) > 1 and text_list[0].split("@")[1] == message.bot.username:
                    filter_result = self.filters(update)
                    if filter_result:
                        return text_list[1:], filter_result and not sql_result
                    else:
                        return False and not sql_result
                else:
                    if text_list[0].lower() not in self.command:
                        return None
                    filter_result = self.filters(update)
                    if filter_result:
                        return text_list[1:], filter_result and not sql_result
                    else:
                        return False and not sql_result
    
    def collect_additional_context(self, context, update, dispatcher, check_result):
        if check_result != True and check_result != False and check_result is not None:
            context.args = check_result[0]
            if isinstance(check_result[1], dict):
                context.update(check_result[1])


tg.CommandHandler = CustomCommandHandler


# NOT ASYNC
def restr_members(bot, chat_id, members, messages=False, media=False, other=False, previews=False):
    for mem in members:
        if mem.user in SUDO_USERS:
            pass
        try:
            bot.restrict_chat_member(chat_id, mem.user,
                                     can_send_messages=messages,
                                     can_send_media_messages=media,
                                     can_send_other_messages=other,
                                     can_add_web_page_previews=previews)
        except TelegramError:
            pass


# NOT ASYNC
def unrestr_members(bot, chat_id, members, messages=True, media=True, other=True, previews=True):
    for mem in members:
        try:
            bot.restrict_chat_member(chat_id, mem.user,
                                     can_send_messages=messages,
                                     can_send_media_messages=media,
                                     can_send_other_messages=other,
                                     can_add_web_page_previews=previews)
        except TelegramError:
            pass


@run_async
def locktypes(update: Update, context: CallbackContext):
    update.effective_message.reply_text("\n - ".join(["Locks: "] + list(LOCK_TYPES) + list(RESTRICTION_TYPES)))


@user_admin
@bot_can_delete
@loggable
def lock(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = message.text.split(" ")
    
    if can_delete(chat, context.bot.id):
        if len(args) >= 2:
            if args[1] in LOCK_TYPES:
                sql.update_lock(chat.id, args[1], locked=True)
                message.reply_text("Locked {} messages for all non-admins!".format(args[1]))

                return "<b>{}:</b>" \
                       "\n#LOCK" \
                       "\n<b>• Admin:</b> {}" \
                       "\nLocked <code>{}</code>.".format(html.escape(chat.title),
                                                          mention_html(user.id, user.first_name), args[1])
            elif args[1] in "all":
                context.bot.set_chat_permissions(update.message.chat.id, LOCK_PERMISSIONS)
                sql.update_restriction(chat.id, args[1], locked=True)
                message.reply_text("Locked {} messages for all non-admins!".format(args[1]))
                context.bot.send_message(chat.id, "***Chat is currently muted.***", parse_mode=ParseMode.MARKDOWN)

                return "<b>{}:</b>" \
                       "\n#LOCK" \
                       "\n<b>• Admin:</b> {}" \
                       "\nLocked <code>{}</code>.".format(html.escape(chat.title),
                                                          mention_html(user.id, user.first_name), args[1])

            elif args[1] in RESTRICTION_TYPES:
                sql.update_restriction(chat.id, args[1], locked=True)
                if args[1] == "previews":
                    members = users_sql.get_chat_members(str(chat.id))
                    restr_members(context.bot, chat.id, members, messages=True, media=True, other=True)

                message.reply_text("Locked {} for all non-admins!".format(args[1]))
                return "<b>{}:</b>" \
                       "\n#LOCK" \
                       "\n<b>• Admin:</b> {}" \
                       "\nLocked <code>{}</code>.".format(html.escape(chat.title),
                                                          mention_html(user.id, user.first_name), args[1])

            else:
                message.reply_text("You've entered an unknown locktypes, Try /locktypes for the list of lockables")

    else:
        message.reply_text("I'm not an administrator, or haven't got delete rights.")

    return ""


@run_async
@user_admin
@loggable
def unlock(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = message.text.split(" ")
    
    if is_user_admin(chat, message.from_user.id):
        if len(args) >= 2:
            if args[1] in LOCK_TYPES:
                sql.update_lock(chat.id, args[1], locked=False)
                message.reply_text("Unlocked {} for everyone!".format(args[1]))
                return "<b>{}:</b>" \
                       "\n#UNLOCK" \
                       "\n<b>• Admin:</b> {}" \
                       "\nUnlocked <code>{}</code>.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name), args[1])
            
            elif args[1] in "all":
                context.bot.set_chat_permissions(update.message.chat.id, UNLOCK_PERMISSIONS)
                sql.update_restriction(chat.id, args[1], locked=False)
                message.reply_text("Unlocked all for everyone!".format(args[1]))
                context.bot.send_message(chat.id, "***Chat is unmuted.***", parse_mode=ParseMode.MARKDOWN)

                return "<b>{}:</b>" \
                       "\n#UNLOCK" \
                       "\n<b>• Admin:</b> {}" \
                       "\nUnlocked <code>{}</code>.".format(html.escape(chat.title),
                                                          mention_html(user.id, user.first_name), args[1])

            elif args[1] in RESTRICTION_TYPES:
                sql.update_restriction(chat.id, args[1], locked=False)
                """
                members = users_sql.get_chat_members(chat.id)
                if args[1] == "messages":
                    unrestr_members(context.bot, chat.id, members, media=False, other=False, previews=False)

                elif args[1] == "media":
                    unrestr_members(context.bot, chat.id, members, other=False, previews=False)

                elif args[1] == "other":
                    unrestr_members(context.bot, chat.id, members, previews=False)

                elif args[1] == "previews":
                    unrestr_members(context.bot, chat.id, members)

                elif args[1] == "all":
                    unrestr_members(context.bot, chat.id, members, True, True, True, True)
                """
                message.reply_text("Unlocked {} for everyone!".format(args[1]))

                return "<b>{}:</b>" \
                       "\n#UNLOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nUnlocked <code>{}</code>.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name), args[1])
            else:
                message.reply_text("What are you trying to unlock...? Try /locktypes for the list of lockables")

        else:
            context.bot.sendMessage(chat.id, "What are you trying to unlock...?")

    return ""

@run_async
@user_not_admin
def del_lockables(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    
    for lockable, filter in LOCK_TYPES.items():
        if lockable == "rtl":
            if sql.is_locked(chat.id, lockable) and can_delete(chat, context.bot.id):
                if message.caption:
                    check = ad.detect_alphabet(u'{}'.format(message.caption))
                    if 'ARABIC' in check:
                        try:
                            message.delete()
                        except BadRequest as excp:
                            if excp.message == "Message to delete not found":
                                pass
                            else:
                                LOGGER.exception("ERROR in lockables")
                if message.text:
                    check = ad.detect_alphabet(u'{}'.format(message.text))
                    if 'ARABIC' in check:
                        try:
                            message.delete()
                        except BadRequest as excp:
                            if excp.message == "Message to delete not found":
                                pass
                            else:
                                LOGGER.exception("ERROR in lockables")
            break
        if filter(update) and sql.is_locked(chat.id, lockable) and can_delete(chat, context.bot.id):
            if lockable == "bots":
                new_members = update.effective_message.new_chat_members
                for new_mem in new_members:
                    if new_mem.is_bot:
                        if not is_bot_admin(chat, context.bot.id):
                            message.reply_text("I see a bot, and I've been told to stop them joining... "
                                               "but I'm not admin!")
                            return

                        chat.kick_member(new_mem.id)
                        message.reply_text("Only admins are allowed to add bots to this chat! Get outta here.")
            else:
                chat_id = chat.id
                whitelist = get_whitelisted_urls(chat_id)
                for i in whitelist:
                    if i.__eq__(message.text):
                       return
                try:
                    message.delete()
                    lock_message = context.bot.send_message(chat.id, "Message deleted because it contained a locked item: {}.".format(lockable))
                    time.sleep(2)
                    lock_message.delete()
                except BadRequest as excp:
                    if excp.message == "Message to delete not found":
                        pass
                    else:
                        LOGGER.exception("ERROR in lockables bots")

            break

@run_async
@user_not_admin
def rest_handler(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    for restriction, filter in RESTRICTION_TYPES.items():
        if filter(update) and sql.is_restr_locked(chat.id, restriction) and can_delete(chat, context.bot.id):
            try:
                msg.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("ERROR in restrictions")
            break


def build_lock_message(chat_id):
    locks = sql.get_locks(chat_id)
    restr = sql.get_restr(chat_id)
    if not (locks or restr):
        res = "There are no current locks in this chat."
    else:
        res = "These are the locks in this chat:"
        if restr:
            res += "\n - all = `{}`" \
                   "\n - messages = `{}`" \
                   "\n - media = `{}`" \
                   "\n - other = `{}`" \
                   "\n - previews = `{}`".format(all([restr.messages, 
                                            restr.media,
                                            restr.other,
                                            restr.preview]),
                                            restr.messages,
                                            restr.media, 
                                            restr.other, 
                                            restr.preview)

        if locks:
            res += "\n - audio = `{}`" \
                   "\n - apk = `{}`" \
                   "\n - animatedsticker = `{}`" \
                   "\n - bots = `{}`" \
                   "\n - command = `{}`" \
                   "\n - contact = `{}`" \
                   "\n - document = `{}`" \
                   "\n - email = `{}`" \
                   "\n - forward = `{}`" \
                   "\n - game = `{}`" \
                   "\n - gif = `{}`" \
                   "\n - location = `{}`" \
                   "\n - poll = `{}`" \
                   "\n - photo = `{}`" \
                   "\n - rtl = `{}` " \
                   "\n - sticker = `{}`" \
                   "\n - url = `{}`" \
                   "\n - voice = `{}`" \
                   "\n - video = `{}`" \
                   "\n - videonote = `{}`".format(locks.audio,
                                             locks.apk, 
                                             locks.animatedsticker,
                                             locks.bots, 
                                             locks.command, 
                                             locks.contact, 
                                             locks.document,
                                             locks.email,
                                             locks.forward, 
                                             locks.game,
                                             locks.gif, 
                                             locks.location, 
                                             locks.poll, 
                                             locks.photo, 
                                             locks.rtl,
                                             locks.sticker, 
                                             locks.url, 
                                             locks.voice, 
                                             locks.video, 
                                             locks.videonote)
    return res


@run_async
@user_admin
def list_locks(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]

    res = build_lock_message(chat.id)

    update.effective_message.reply_text(res, parse_mode=ParseMode.MARKDOWN)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return build_lock_message(chat_id)


__help__ = """
Do stickers annoy you? or want to avoid people sharing links? or pictures? \
You're in the right place!

The locks module allows you to lock away some common items in the \
telegram world; the bot will automatically delete them!

 - /locktypes: a list of possible locktypes
 - /whitelist: a list of possible whitelisted domains

*Admin only:*
 - /lock <type>: lock items of a certain type (not available in private)
 - /unlock <type>: unlock items of a certain type (not available in private)
 - /locks: the current list of locks in this chat.
 
 - /addwhitelist <domains>: Add a domain to the whitelist. Each line is considered one domain, \
 so using different lines will allow you to add multiple domains.
 - /unwhitelist <domains>: Remove domains from the whitelist. Same newline logic applies here, \
 so you can remove multiple domains at once.
 - /rmwhitelist <domains>: Same as above.


Locks can be used to restrict a group's users.
eg:
Locking urls will auto-delete all messages with urls which haven't been whitelisted, locking stickers will delete all \
stickers, etc.
Locking bots will stop non-admins from adding bots to the chat.
"""

__mod_name__ = "Locks & Whitelists"

LOCKTYPES_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "locktypes", locktypes)
LOCK_HANDLER = CustomCommandHandler(CMD_PREFIX, "lock", lock, filters=Filters.group)
UNLOCK_HANDLER = CustomCommandHandler(CMD_PREFIX, "unlock", unlock, filters=Filters.group)
LOCKED_HANDLER = CustomCommandHandler(CMD_PREFIX, "locks", list_locks, filters=Filters.group)

dispatcher.add_handler(LOCK_HANDLER)
dispatcher.add_handler(UNLOCK_HANDLER)
dispatcher.add_handler(LOCKTYPES_HANDLER)
dispatcher.add_handler(LOCKED_HANDLER)

dispatcher.add_handler(MessageHandler(Filters.all & Filters.group & (~ Filters.user(777000)), del_lockables), PERM_GROUP)
dispatcher.add_handler(MessageHandler(Filters.all & Filters.group & (~ Filters.user(777000)), rest_handler), REST_GROUP)
