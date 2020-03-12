import html, re
from typing import Optional

import telegram
from telegram import ParseMode, InlineKeyboardMarkup, Message, Chat
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler, DispatcherHandlerStop, Filters, MessageHandler, run_async, CallbackContext
from telegram.utils.helpers import escape_markdown, mention_markdown, mention_html

from natalie_bot import dispatcher, LOGGER, CMD_PREFIX
from natalie_bot.modules.disable import DisableAbleCommandHandler
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import user_admin
from natalie_bot.modules.helper_funcs.extraction import extract_text
from natalie_bot.modules.helper_funcs.filters import CustomFilters
from natalie_bot.modules.log_channel import loggable
from natalie_bot.modules.helper_funcs.misc import build_keyboard
from natalie_bot.modules.helper_funcs.string_handling import split_quotes, button_markdown_parser, \
     escape_invalid_curly_brackets
from natalie_bot.modules.sql import cust_filters_sql as sql

HANDLER_GROUP = 10
BASIC_FILTER_STRING = "*List of filters in {}:*\n"

VALID_FORMATTERS = ['first', 'last', 'fullname', 'username', 'id', 'count', 'chatname', 'mention']


@run_async
def list_handlers(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    all_handlers = sql.get_chat_triggers(chat.id)
    chat_name = chat.title or chat.first or chat.username
    if not all_handlers:
        update.effective_message.reply_text("No filters are active here!")
        return

    filter_list = BASIC_FILTER_STRING
    for keyword in all_handlers:
        entry = " • `{}`\n".format((keyword))
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list, parse_mode=telegram.ParseMode.MARKDOWN)
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == BASIC_FILTER_STRING:
        update.effective_message.reply_text(filter_list.format(chat_name), parse_mode=telegram.ParseMode.MARKDOWN)


# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@user_admin
@loggable
def filters(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(None, 1)  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])
    if len(extracted) < 1:
        return
    # set trigger -> lower, so as to avoid adding duplicate filters with different cases
    keyword = extracted[0].lower()

    is_sticker = False
    is_document = False
    is_image = False
    is_voice = False
    is_audio = False
    is_video = False
    buttons = []

    # determine what the contents of the filter are - text, image, sticker, etc
    if len(extracted) >= 2:
        offset = len(extracted[1]) - len(msg.text)  # set correct offset relative to command + notename
        content, buttons = button_markdown_parser(extracted[1], entities=msg.parse_entities(), offset=offset)
        content = content.strip()
        if not content:
            msg.reply_text("There is no note message - You can't JUST have buttons, you need a message to go with it!")
            return ""

    elif msg.reply_to_message and msg.reply_to_message.sticker:
        content = msg.reply_to_message.sticker.file_id
        is_sticker = True

    elif msg.reply_to_message and msg.reply_to_message.document:
        content = msg.reply_to_message.document.file_id
        is_document = True

    elif msg.reply_to_message and msg.reply_to_message.photo:
        try:
            offset = len(msg.reply_to_message.caption)
        except:
            offset = 0
            LOGGER.log(2, "Photo has no caption.")

        ignore_underscore_case, buttons = button_markdown_parser(msg.reply_to_message.caption, 
                                                                 entities=msg.reply_to_message.parse_entities(), 
                                                                 offset=offset)
        content = msg.reply_to_message.photo[-1].file_id  # last elem = best quality
        is_image = True

    elif msg.reply_to_message and msg.reply_to_message.audio:
        content = msg.reply_to_message.audio.file_id
        is_audio = True

    elif msg.reply_to_message and msg.reply_to_message.voice:
        content = msg.reply_to_message.voice.file_id
        is_voice = True

    elif msg.reply_to_message and msg.reply_to_message.video:
        content = msg.reply_to_message.video.file_id
        is_video = True

    else:
        msg.reply_text("You didn't specify what to reply with!")
        return ""

    # Add the filter
    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, HANDLER_GROUP)

    sql.add_filter(chat.id, keyword, content, is_sticker, is_document, is_image, is_audio, is_voice, is_video,
                   buttons)
    log = "<b>{}:</b>" \
          "\n#FILTERS" \
          "\n<b>• Action:</b> added" \
          "\n<b>• Admin:</b> {}" \
          "\n<b>• Trigger:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name), keyword)

    update.effective_message.reply_text("Filter has been saved for '`{}`'.".format(keyword), parse_mode=ParseMode.MARKDOWN)

    send_filter_log(update, context, log)
    raise DispatcherHandlerStop

@loggable
def send_filter_log(update, context, log):
    return log

# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@user_admin
@loggable
def stop_filter(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user
    args = update.effective_message.text.split(None, 1)

    if len(args) < 2:
        return

    chat_filters = sql.get_chat_triggers(chat.id)

    if not chat_filters:
        update.effective_message.reply_text("No filters are active here!")
        return

    for keyword in chat_filters:
        if keyword == args[1]:
            sql.remove_filter(chat.id, args[1])
            update.effective_message.reply_text("Removed '`{}`', I will no longer reply to that!".format(keyword), parse_mode=ParseMode.MARKDOWN)
            
            log = "<b>{}:</b>" \
                  "\n#FILTERS" \
                  "\n<b>• Action:</b> cleared" \
                  "\n<b>• Admin:</b> {}" \
                  "\n<b>• Trigger:</b> {}".format(html.escape(chat.title), mention_html(user.id, 
                                                  user.first_name), keyword)
            return log
            raise DispatcherHandlerStop

    update.effective_message.reply_text("That's not a current filter - run /filters for all active filters.")


@run_async
def reply_filter(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    to_match = extract_text(message)
    if not to_match:
        return

    if message.reply_to_message:
        message = message.reply_to_message
    str_filter = ""

    chat_filters = sql.get_chat_triggers(chat.id)
    for keyword in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            filt = sql.get_filter(chat.id, keyword)
            buttons = sql.get_buttons(chat.id, filt.keyword)
            if filt.is_sticker:
                message.reply_sticker(filt.reply)
            elif filt.is_document:
                message.reply_document(filt.reply)
            elif filt.is_image:
                if len(buttons) > 0:
                    keyb = build_keyboard(buttons)
                    keyboard = InlineKeyboardMarkup(keyb)
                    message.reply_photo(filt.reply, reply_markup=keyboard)
                else:
                    message.reply_photo(filt.reply)
            elif filt.is_audio:
                message.reply_audio(filt.reply)
            elif filt.is_voice:
                message.reply_voice(filt.reply)
            elif filt.is_video:
                message.reply_video(filt.reply)
            elif filt.has_markdown:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                should_preview_disabled = True
                if "telegra.ph" in filt.reply or "youtu.be" in filt.reply:
                    should_preview_disabled = False

                try:
                    user = update.effective_user  # type: Optional[User]
                    chat = update.effective_chat  # type: Optional[Chat]
                    count = chat.get_members_count()
                    first_name = user.first_name or "No Name"
                    mention = mention_markdown(user.id, first_name)
                    
                    if user.last_name:
                        fullname = "{} {}".format(first_name, user.last_name)
                    else:
                        fullname = first_name
                    if user.username:
                            username = "@" + escape_markdown(user.username)
                    else:
                        username = mention
                    valid_format = escape_invalid_curly_brackets(filt.reply, VALID_FORMATTERS)
                    filt.reply = valid_format.format(first=escape_markdown(first_name),
                                            last=escape_markdown(user.last_name or first_name),
                                            fullname=escape_markdown(fullname), username=username, mention=mention,
                                            count=count, chatname=escape_markdown(chat.title), id=user.id)
                    message.reply_text(str_filter + "\n" + filt.reply, parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=should_preview_disabled,
                                       reply_markup=keyboard)
                except BadRequest as excp:
                    if excp.message == "Unsupported url protocol":
                        message.reply_text("You seem to be trying to use an unsupported url protocol. Telegram "
                                           "doesn't support buttons for some protocols, such as tg://. Please try "
                                           "again, or ask @stillmav for help.")
                    elif excp.message == "Reply message not found":
                        context.bot.send_message(chat.id, filt.reply, parse_mode=ParseMode.MARKDOWN,
                                         disable_web_page_preview=True,
                                         reply_markup=keyboard)
                    else:
                        message.reply_text("This note could not be sent, as it is incorrectly formatted. Ask in "
                                           "@stillmav if you can't figure out why!")
                        LOGGER.warning("Message %s could not be parsed", str(filt.reply))
                        LOGGER.exception("Could not parse filter %s in chat %s", str(filt.keyword), str(chat.id))

            else:
                # LEGACY - all new filters will have has_markdown set to True.
                message.reply_text(str_filter + "\n" + filt.reply)
            break


def __stats__():
    return "{} filters, across {} chats.".format(sql.num_filters(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    cust_filters = sql.get_chat_triggers(chat_id)
    return "There are `{}` custom filters here.".format(len(cust_filters))


__help__ = """
Make your chat more lively with filters; The {} will reply to certain words!

Filters are case insensitive; every time someone says your trigger words, {} will reply something else! can be used to create your own commands, if desired.

 - /filters: list all active filters in this chat.

*Admin only:*
 - /filter <keyword> <reply message>: Every time someone says "word", the bot will reply with "sentence". For multiple word filters, quote the first word.
 - /stop <filter keyword>: stop that filter.
 
 An example of how to set a filter would be via:
`/filter hello Hello there! How are you?`

A multiword filter could be set via:
`/filter "hello friend" Hello back! Long time no see!`

If you want to save an image, gif, or sticker, or any other data, do the following:
`/filter word while replying to a sticker or whatever data you'd like. Now, every time someone mentions "word", that sticker will be sent as a reply.`

Now, anyone saying "hello" will be replied to with "Hello there! How are you?".

Having buttons in filters are cool, everyone hates URLs visible. With button links you can make your chats look more \
tidy and simplified.

Here is an example of using buttons:
You can create a button using `[Name of button text](buttonurl://example.com)`.

If you wish to add more than 1 buttons simply do the following:
`[Button 1](buttonurl://example.com)`
`[Button 2](buttonurl://github.com:same)`
`[Button 3](buttonurl://google.com)`

The `:same` end of the link merges 2 buttons on same line as 1 button, resulting in 3 button to be separated \
from same line.

""".format(dispatcher.bot.first_name, dispatcher.bot.first_name)

__mod_name__ = "Filters"

FILTER_HANDLER = CustomCommandHandler(CMD_PREFIX, "filter", filters)
STOP_HANDLER = CustomCommandHandler(CMD_PREFIX, "stop", stop_filter)
LIST_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "filters", list_handlers, admin_ok=True)
CUST_FILTER_HANDLER = MessageHandler(CustomFilters.has_text, reply_filter, Filters.update.edited_message)

dispatcher.add_handler(FILTER_HANDLER)
dispatcher.add_handler(STOP_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(CUST_FILTER_HANDLER, HANDLER_GROUP)
