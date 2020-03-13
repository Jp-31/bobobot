from html import escape
import time, spamwatch
import re
import threading
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, CallbackQuery, ChatPermissions
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler, run_async, CallbackQueryHandler, CallbackContext
from telegram.utils.helpers import mention_html

import natalie_bot.modules.sql.welcome_sql as sql
from natalie_bot.modules.sql.global_bans_sql import get_gbanned_user
from natalie_bot import dispatcher, OWNER_ID, LOGGER, CMD_PREFIX, SPAMWATCH_TOKEN
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import user_admin, can_delete, is_user_ban_protected, is_user_admin, can_restrict, can_message
from natalie_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from natalie_bot.modules.helper_funcs.msg_types import get_welcome_type
from natalie_bot.modules.helper_funcs.string_handling import markdown_parser, \
    escape_invalid_curly_brackets, markdown_to_html
from natalie_bot.modules.log_channel import loggable

VALID_WELCOME_FORMATTERS = ['first', 'last', 'fullname', 'username', 'id', 'count', 'chatname', 'mention']
client = spamwatch.Client(SPAMWATCH_TOKEN)

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}

WELCOME_PERMISSIONS_SOFT = ChatPermissions(can_send_messages=True, 
                                     can_send_media_messages=False, 
                                     can_send_other_messages=False, 
                                     can_add_web_page_previews=False)

WELCOME_PERMISSIONS_STRONG = ChatPermissions(can_send_messages=False, 
                                     can_send_media_messages=False, 
                                     can_send_other_messages=False, 
                                     can_add_web_page_previews=False)

WELCOME_PERMISSIONS_AGGRESSIVE = ChatPermissions(can_send_messages=False, 
                                     can_send_media_messages=False, 
                                     can_send_other_messages=False, 
                                     can_add_web_page_previews=False)

USER_PERMISSIONS_UNMUTE = ChatPermissions(can_send_messages=True, 
                                    can_send_media_messages=True, 
                                    can_send_other_messages=True, 
                                    can_add_web_page_previews=True)
# do not async
@can_message
def send(update, context, message, keyboard, backup_message, caption=None, type=None):
    try:
        if caption and type == 'photo':
            msg = update.effective_message.reply_photo(message, caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        elif caption and type == 'video':
            msg = update.effective_message.reply_video(message, duration=None, caption=caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        elif caption and type == 'document':
            msg = update.effective_message.reply_document(message, filename=None, caption=caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        else:
            msg = update.effective_message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except IndexError:
        msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                  "\nNote: the current message was "
                                                                  "invalid due to markdown issues. Could be "
                                                                  "due to the user's name."),
                                                  parse_mode=ParseMode.MARKDOWN)
    except KeyError:
        msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                  "\nNote: the current message is "
                                                                  "invalid due to an issue with some misplaced "
                                                                  "curly brackets. Please update"),
                                                  parse_mode=ParseMode.MARKDOWN)
    except BadRequest as excp:
        if excp.message == "Button_url_invalid":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNote: the current message has an invalid url "
                                                                      "in one of its buttons. Please update."),
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Unsupported url protocol":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNote: the current message has buttons which "
                                                                      "use url protocols that are unsupported by "
                                                                      "telegram. Please update."),
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Wrong url host":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNote: the current message has some bad urls. "
                                                                      "Please update."),
                                                      parse_mode=ParseMode.MARKDOWN)
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("Could not parse! got invalid url host errors")
        else:
            msg = context.bot.send_message(update.effective_chat.id, markdown_parser(backup_message +
                                                                      "\nNote: An error occured when sending the "
                                                                      "custom message. Please update."),
                                                      parse_mode=ParseMode.MARKDOWN)
            LOGGER.exception("Couldn't send a welcome message: {}".format(excp))

    return msg

def format_welcome_message(welc_caption, first_name, chat, new_mem):
    welc_caption = markdown_to_html(welc_caption)
    if new_mem.last_name:
        fullname = "{} {}".format(
            first_name, new_mem.last_name)
    else:
        fullname = first_name
    count = chat.get_members_count()
    mention = mention_html(new_mem.id, first_name)
    if new_mem.username:
        username = "@" + escape(new_mem.username)
    else:
        username = mention

    valid_format = escape_invalid_curly_brackets(
        welc_caption, VALID_WELCOME_FORMATTERS)

    res = valid_format.format(first=escape(first_name),
                                last=escape(
                                new_mem.last_name or first_name),
                                fullname=escape(fullname), username=username, mention=mention,
                                count=count, chatname=escape(chat.title), id=new_mem.id)

    return res

@run_async
@can_message
@loggable
def new_member(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message # type: Optional[Message]
    chat_name = chat.title or chat.first or chat.username # type: Optional:[chat name]
    should_welc, cust_welcome, welc_type, welc_caption = sql.get_welc_pref(chat.id)
    welc_mutes = sql.welcome_mutes(chat.id)
    human_checks = sql.get_human_checks(user.id, chat.id)
    prev_welc = sql.get_clean_pref(chat.id)
    media = False
    no_mute = False

    try:
        for mem in msg.new_chat_members:
            user_id = mem.id
    except:
        LOGGER.log("User being added or no ID found for user.")
    
    gban_checks = get_gbanned_user(user_id)
    
    join_log = sql.get_join_event_pref(chat.id)
    join_members = msg.new_chat_members

    if should_welc:
        sent = None
        new_members = msg.new_chat_members
        for new_mem in new_members:
            spamwatch_banned = client.get_ban(new_mem.id)
            user_add = context.bot.get_chat_member(chat.id, user.id)

            # edge case of empty name - occurs for some bugs.
            first_name = new_mem.first_name or "PersonWithNoName"
            # Give the owner a special welcome
            log = ""
            if join_log == True:
                log += "<b>{}:</b>" \
                       "\n#WELCOME" \
                       "\n<b>A new user has joined:</b>" \
                       "\n<b>• User:</b> {}" \
                       "\n<b>• ID:</b> <code>{}</code>".format(escape(chat.title), mention_html(mem.id, mem.first_name), mem.id)
                if user.id != mem.id:
                    log += "\n<b>• Added by:</b> {}".format(mention_html(user.id, user.first_name))

            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text("Master is in the houseeee, let's get this party started!")
                continue

            #### BAN CHECKERS ####
            # Ignore welc messages for gbanned users
            if gban_checks:
                continue

            # Ignore welc messages for SpamWatch banned users
            if spamwatch_banned:
                continue

            # Make bot greet admins
            elif new_mem.id == context.bot.id:
                update.effective_message.reply_text("Hey {}, I'm {}! Thank you for adding me to {}" 
                " and be sure to check /help in PM for more commands and tricks!".format(user.first_name, 
                                                                                         context.bot.first_name, chat_name))

            else:
                # If welcome message is media, send with appropriate function
                if welc_type != sql.Types.TEXT and welc_type != sql.Types.BUTTON_TEXT:
                    if welc_type == sql.Types.PHOTO:
                        media = True
                        type = 'photo'
                        if welc_caption:
                            res = format_welcome_message(welc_caption, first_name, chat, new_mem)
                            buttons = sql.get_welc_buttons(chat.id)
                            keyb = build_keyboard(buttons)

                        keyboard = InlineKeyboardMarkup(keyb)

                        sent = send(update, context, cust_welcome, keyboard,
                                    sql.DEFAULT_WELCOME.format(first=first_name, chatname=chat_name), res, type)

                        if sent:
                            sql.set_clean_welcome(chat.id, sent.message_id)
                    elif welc_type == sql.Types.VIDEO:
                        media = True
                        type = 'video'
                        if welc_caption:
                            res = format_welcome_message(welc_caption, first_name, chat, new_mem)
                            buttons = sql.get_welc_buttons(chat.id)
                            keyb = build_keyboard(buttons)

                        keyboard = InlineKeyboardMarkup(keyb)

                        sent = send(update, context, cust_welcome, keyboard,
                                    sql.DEFAULT_WELCOME.format(first=first_name, chatname=chat_name), res, type)

                        if sent:
                            sql.set_clean_welcome(chat.id, sent.message_id)
                    elif welc_type == sql.Types.DOCUMENT:
                        media = True
                        type = 'document'
                        if welc_caption:
                            res = format_welcome_message(
                                welc_caption, first_name, chat, new_mem)
                            buttons = sql.get_welc_buttons(chat.id)
                            keyb = build_keyboard(buttons)

                        keyboard = InlineKeyboardMarkup(keyb)

                        sent = send(update, context, cust_welcome, keyboard,
                                    sql.DEFAULT_WELCOME.format(first=first_name, chatname=chat_name), res, type)

                        if sent:
                            sql.set_clean_welcome(chat.id, sent.message_id)
                    else:
                        media = True
                        ENUM_FUNC_MAP[welc_type](chat.id, cust_welcome)

                # else, move on
                if media == False:
                    if welc_caption:
                        res = format_welcome_message(welc_caption, first_name, chat, new_mem)
                        buttons = sql.get_welc_buttons(chat.id)
                        keyb = build_keyboard(buttons)
                    else:
                        res = sql.DEFAULT_WELCOME.format(first=first_name, chatname=chat_name)
                        keyb = []

                    keyboard = InlineKeyboardMarkup(keyb)

                    sent = send(update, context, res, keyboard,
                                sql.DEFAULT_WELCOME.format(first=first_name, chatname=chat_name))  # type: Optional[Message]
                #User exception from mutes:
                if is_user_ban_protected(chat, new_mem.id, chat.get_member(new_mem.id)) or human_checks or gban_checks:
                    no_mute = True

                if not no_mute:
                    #Join welcome: soft mute
                    if welc_mutes == "soft":
                        context.bot.restrict_chat_member(chat.id, new_mem.id, WELCOME_PERMISSIONS_SOFT,
                                                        until_date=(int(time.time() + 24 * 60 * 60)))
                    #Join welcome: strong mute
                    if welc_mutes == "strong":
                        mute_message = msg.reply_text("Hey {} (`{}`),\nClick the button below to prove you're human:".format(new_mem.first_name, 
                                                                                                                            new_mem.id),
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Tap here to speak", 
                            callback_data="user_join_({})".format(new_mem.id))]]), parse_mode=ParseMode.MARKDOWN)
                        context.bot.restrict_chat_member(chat.id, new_mem.id, WELCOME_PERMISSIONS_STRONG)

                    #Join welcome: aggressive mute
                    elif welc_mutes == "aggressive":
                        mute_message = msg.reply_text("Hey {} (`{}`),\nClick the button below to prove you're human:".format(new_mem.first_name, 
                                                                                                                            new_mem.id), 
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Tap here to speak",
                            callback_data="user_join_({})".format(new_mem.id))]]), parse_mode=ParseMode.MARKDOWN)
                        context.bot.restrict_chat_member(chat.id, new_mem.id, WELCOME_PERMISSIONS_AGGRESSIVE)
            delete_join(update, context)

            if prev_welc:
                try:
                    context.bot.delete_message(chat.id, prev_welc)
                except BadRequest as excp:
                    pass

            if sent:
                sql.set_clean_welcome(chat.id, sent.message_id)

            if not human_checks and welc_mutes == "aggressive":
                t = threading.Thread(target=aggr_mute_check, args=(
                    context.bot, chat, mute_message.message_id, new_mem.id,))
                t.start()

            return log

    return ""

def aggr_mute_check(bot: Bot, chat: Chat, message_id, user_id):
    time.sleep(60)
    if bot.get_chat_member(chat.id, user_id).can_send_messages:
        bot.delete_message(chat.id, message_id)
        return
    bot.delete_message(chat.id, message_id)
    chat.kick_member(user_id)
    chat.unban_member(user_id)

@run_async
def left_member(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)
    cust_goodbye = markdown_to_html(cust_goodbye)

    if should_goodbye:
        left_mem = update.effective_message.left_chat_member
        gban_checks = get_gbanned_user(left_mem.id)
        spamwatch_banned = client.get_ban(left_mem.id)
        if left_mem:
            # Ignore bot being kicked
            if left_mem.id == context.bot.id:
                return

            ### BAN CHECKERS ###
            # Ignore gbanned users
            if gban_checks:
                return

            # Ignore spamwatch banned users
            if spamwatch_banned:
                return

            # Give the owner a special goodbye
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text("RIP Master")
                return

            # if media goodbye, use appropriate function for it
            if goodbye_type != sql.Types.TEXT and goodbye_type != sql.Types.BUTTON_TEXT:
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
                return

            first_name = left_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.
            if cust_goodbye:
                if left_mem.last_name:
                    fullname = "{} {}".format(first_name, left_mem.last_name)
                else:
                    fullname = first_name
                count = chat.get_members_count()
                mention = mention_html(left_mem.id, first_name)
                if left_mem.username:
                    username = "@" + escape(left_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(cust_goodbye, VALID_WELCOME_FORMATTERS)
                res = valid_format.format(first=escape(first_name),
                                          last=escape(left_mem.last_name or first_name),
                                          fullname=escape(fullname), username=username, mention=mention,
                                          count=count, chatname=escape(chat.title), id=left_mem.id)
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)

            else:
                res = sql.DEFAULT_GOODBYE
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)

            send(update, context, res, keyboard, sql.DEFAULT_GOODBYE)


@run_async
@user_admin
def welcome(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(" ")
    args_option = ""

    if len(args) > 1:
        args_option = args[1].lower()
    # if no args, show current replies.
    if len(args) == 1 or args_option == "noformat":
        noformat = args and args_option == "noformat"
        pref, welcome_m, welcome_type, welc_caption = sql.get_welc_pref(chat.id)

        if welcome_m == None:
            welcome_m = welc_caption

        update.effective_message.reply_text(
            "This chat has it's welcome setting set to: `{}`.\n*The welcome message "
            "(not filling the {{}}) is:*".format(pref),
            parse_mode=ParseMode.MARKDOWN)

        if welcome_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, context, welcome_m, keyboard, sql.DEFAULT_WELCOME)

        else:
            if noformat:
                buttons = sql.get_welc_buttons(chat.id)
                if buttons:
                    welc_caption += revert_buttons(buttons)
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m, caption=welc_caption)

            else:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m, caption=welc_caption, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 2:
        if args_option != "" and args_option in ("on", "yes"):
            sql.set_welc_preference(str(chat.id), True)
            update.effective_message.reply_text("I'll be polite!")

        elif args_option != "" and args_option in ("off", "no"):
            sql.set_welc_preference(str(chat.id), False)
            update.effective_message.reply_text("I'm sulking, not saying hello anymore.")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("I understand 'on/yes' or 'off/no' only!")

@run_async
@user_admin
def goodbye(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(" ")
    args_option = ""
    
    if len(args) > 1:
        args_option = args[1].lower()

    if len(args) == 1 or args_option == "noformat":
        noformat = args and args_option == "noformat"
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        update.effective_message.reply_text(
            "This chat has it's goodbye setting set to: `{}`.\n*The goodbye  message "
            "(not filling the {{}}) is:*".format(pref),
            parse_mode=ParseMode.MARKDOWN)

        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                update.effective_message.reply_text(goodbye_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, context, goodbye_m, keyboard, sql.DEFAULT_GOODBYE)

        else:
            if noformat:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)

            else:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 1:
        if args_option != "" and args_option in ("on", "yes"):
            sql.set_gdbye_preference(str(chat.id), True)
            update.effective_message.reply_text("I'll be sorry when people leave!")

        elif args_option != "" and args_option in ("off", "no"):
            sql.set_gdbye_preference(str(chat.id), False)
            update.effective_message.reply_text("They leave, they're dead to me.")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("I understand 'on/yes' or 'off/no' only!")


@run_async
@user_admin
@loggable
def set_welcome(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("You didn't specify what to reply with!")
        return ""

    sql.set_custom_welcome(chat.id, content, text, data_type, buttons)
    msg.reply_text("Successfully set custom welcome message!")

    return "<b>{}:</b>" \
           "\n#SET_WELCOME" \
           "\n<b>Admin:</b> {}" \
           "\nSet the welcome message.".format(escape(chat.title),
                                               mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def reset_welcome(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    sql.set_custom_welcome(chat.id, None, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    update.effective_message.reply_text("Successfully reset welcome message to default!")
    return "<b>{}:</b>" \
           "\n#RESET_WELCOME" \
           "\n<b>Admin:</b> {}" \
           "\nReset the welcome message to default.".format(escape(chat.title),
                                                            mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def set_goodbye(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("You didn't specify what to reply with!")
        return ""

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
    msg.reply_text("Successfully set custom goodbye message!")
    return "<b>{}:</b>" \
           "\n#SET_GOODBYE" \
           "\n<b>Admin:</b> {}" \
           "\nSet the goodbye message.".format(escape(chat.title),
                                               mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def reset_goodbye(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    sql.set_custom_gdbye(chat.id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    update.effective_message.reply_text("Successfully reset goodbye message to default!")
    return "<b>{}:</b>" \
           "\n#RESET_GOODBYE" \
           "\n<b>Admin:</b> {}" \
           "\nReset the goodbye message.".format(escape(chat.title),
                                                 mention_html(user.id, user.first_name))

@run_async
@user_admin
@loggable
def welcomemute(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message # type: Optional[Message]
    args = msg.text.split(" ")
    args_option = ""

    if len(args) > 1:
        args_option = args[1].lower()

    if len(args) >= 2:
        if  args_option != "" and args_option in ("off", "no"):
            sql.set_welcome_mutes(chat.id, False)
            msg.reply_text("I will no longer mute people on joining!")
            return "<b>{}:</b>" \
                   "\n#WELCOME_MUTE" \
                   "\n<b>• Admin:</b> {}" \
                   "\nHas toggled welcome mute to <b>OFF</b>.".format(escape(chat.title),
                                                                      mention_html(user.id, user.first_name))
        elif args_option != "" and args_option in ("soft"):
             sql.set_welcome_mutes(chat.id, "soft")
             msg.reply_text("I will restrict user's permission to send media for 24 hours")
             return "<b>{}:</b>" \
                    "\n#WELCOME_MUTE" \
                    "\n<b>• Admin:</b> {}" \
                    "\nHas toggled welcome mute to <b>SOFT</b>.".format(escape(chat.title),
                                                                       mention_html(user.id, user.first_name))
        elif args_option != "" and args_option in ("strong"):
             sql.set_welcome_mutes(chat.id, "strong")
             msg.reply_text("I will now mute people when they join and"
                           " click on the button to be unmuted.")
             return "<b>{}:</b>" \
                    "\n#WELCOME_MUTE" \
                    "\n<b>• Admin:</b> {}" \
                    "\nHas toggled welcome mute to <b>STRONG</b>.".format(escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
        elif args_option != "" and args_option in ("aggressive"):
             sql.set_welcome_mutes(chat.id, "aggressive")
             msg.reply_text("I will now mute people when they join and"
                           " click on the button to be unmuted, else they will be kicked within a minute if failed to verify.")
             return "<b>{}:</b>" \
                    "\n#WELCOME_MUTE" \
                    "\n<b>• Admin:</b> {}" \
                    "\nHas toggled welcome mute to <b>AGGRESSIVE</b>.".format(escape(chat.title),
                                                                              mention_html(user.id, user.first_name))

        else:
            msg.reply_text("Please enter `off`/`on`/`soft`/`strong`/`aggressive`!", parse_mode=ParseMode.MARKDOWN)
            return ""
    else:
        curr_setting = sql.welcome_mutes(chat.id)
        reply = "\n Give me a setting! Choose one of: `off`/`no` or `soft` or `strong` or `aggressive` only! \nCurrent setting: `{}`"
        msg.reply_text(reply.format(curr_setting), parse_mode=ParseMode.MARKDOWN)
        return ""

@run_async
@user_admin
@loggable
def clean_welcome(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = update.effective_message.text.split(" ")
    args_option = ""
    
    if len(args) > 1:
        args_option = args[1].lower()

    if len(args) == 1:
        clean_pref = sql.get_clean_pref(chat.id)
        if clean_pref:
            update.effective_message.reply_text("I should be deleting welcome messages up to two days old.")
        else:
            update.effective_message.reply_text("I'm currently not deleting old welcome messages!")
        return ""

    if args_option != "" and args_option in ("on", "yes"):
        sql.set_clean_welcome(str(chat.id), True)
        update.effective_message.reply_text("I'll try to delete old welcome messages!")
        return "<b>{}:</b>" \
               "\n#CLEAN_WELCOME" \
               "\n<b>Admin:</b> {}" \
               "\nHas toggled clean welcomes to <code>ON</code>.".format(escape(chat.title),
                                                                         mention_html(user.id, user.first_name))
    elif args_option != "" and args_option in ("off", "no"):
        sql.set_clean_welcome(str(chat.id), False)
        update.effective_message.reply_text("I won't delete old welcome messages.")
        return "<b>{}:</b>" \
               "\n#CLEAN_WELCOME" \
               "\n<b>Admin:</b> {}" \
               "\nHas toggled clean welcomes to <code>OFF</code>.".format(escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
    else:
        # idek what you're writing, say yes or no
        update.effective_message.reply_text("I understand 'on/yes' or 'off/no' only!")
        return ""

@run_async
@user_admin
@loggable
def del_joined(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = update.effective_message.text.split(" ")
    args_option = ""
    
    if len(args) > 1:
        args_option = args[1].lower()

    if  len(args) == 1:
        del_pref = sql.get_del_pref(chat.id)
        if del_pref:
            update.effective_message.reply_text("I should be deleting `user` joined the chat messages now.")
        else:
            update.effective_message.reply_text("I'm currently not deleting old joined messages!")
        return ""

    if args_option != "" and args_option in ("on", "yes"):
        sql.set_del_joined(str(chat.id), True)
        update.effective_message.reply_text("I'll try to delete old joined messages!")
        return "<b>{}:</b>" \
               "\n#CLEAN_SERVICE" \
               "\n<b>• Admin:</b> {}" \
               "\nHas toggled joined deletion to <code>ON</code>.".format(escape(chat.title),
                                                                         mention_html(user.id, user.first_name))
    elif args_option != "" and args_option in ("off", "no"):
        sql.set_del_joined(str(chat.id), False)
        update.effective_message.reply_text("I won't delete old joined messages.")
        return "<b>{}:</b>" \
               "\n#CLEAN_SERVICE" \
               "\n<b>• Admin:</b> {}" \
               "\nHas toggled joined deletion to <code>OFF</code>.".format(escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
    else:
        # idek what you're writing, say yes or no
        update.effective_message.reply_text("I understand 'on/yes' or 'off/no' only!")
        return ""

@run_async
@user_admin
@loggable
def join_event_log(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = update.effective_message.text.split(" ")
    args_option = ""
    
    if len(args) > 1:
        args_option = args[1].lower()

    if  len(args) == 1:
        del_pref = sql.get_join_event_pref(chat.id)
        if del_pref:
            update.effective_message.reply_text("I'm currently sending join events logs.")
        else:
            update.effective_message.reply_text("I'm currently not sending any join event logs!")
        return ""

    if args_option != "" and args_option in ("on", "yes"):
        sql.set_join_event(str(chat.id), True)
        update.effective_message.reply_text("I'll send any new join user event to log channel.")
        return "<b>{}:</b>" \
               "\n#WELCOME" \
               "\n<b>• Admin:</b> {}" \
               "\nHas toggled joined events to <code>ON</code>.".format(escape(chat.title),
                                                                         mention_html(user.id, user.first_name))
    elif args_option != "" and args_option in ("off", "no"):
        sql.set_join_event(str(chat.id), False)
        update.effective_message.reply_text("I won't be sending any logs of new joined users to the log channel.")
        return "<b>{}:</b>" \
               "\n#WELCOME" \
               "\n<b>• Admin:</b> {}" \
               "\nHas toggled joined events to <code>OFF</code>.".format(escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
    else:
        # idek what you're writing, say yes or no
        update.effective_message.reply_text("I understand 'on/yes' or 'off/no' only!")
        return ""

@run_async
def delete_join(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    join = update.effective_message.new_chat_members
    if can_delete(chat, context.bot.id):
        del_join = sql.get_del_pref(chat.id)
        if del_join:
            try:
                update.message.delete()
            except:
                LOGGER.log(2, "Could not delete join message. Line: 609")
            
@run_async
@can_restrict
def user_button(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    query = update.callback_query  # type: Optional[CallbackQuery]
    match = re.match(r"user_join_\((.+?)\)", query.data)
    message = update.effective_message  # type: Optional[Message]
    db_checks = sql.set_human_checks(user.id, chat.id)
    join_user =  int(match.group(1))
    
    if join_user == user.id:
        query.answer(text="Yus! You're a human, Unmuted!")
        context.bot.restrict_chat_member(chat.id, user.id, USER_PERMISSIONS_UNMUTE)
        context.bot.deleteMessage(chat.id, message.message_id)
        db_checks
    
    
    member = chat.get_member(int(user.id))
    admin = update.effective_user
    id_join =  int(match.group(1))
    if member:
        if is_user_admin(chat, user.id, member=member):
            query.answer(text="User has been unmuted!")
            update.effective_message.edit_text(
                    "User has been unmuted by {}".format(admin.first_name))
            sql.set_human_checks(id_join, chat.id)
            context.bot.restrict_chat_member(chat.id, id_join, USER_PERMISSIONS_UNMUTE)
            time.sleep(60)
            context.bot.deleteMessage(chat.id, message.message_id)
        else:
            query.answer(text="You're not allowed to do this!")
    else:
        query.answer(text="You're not allowed to do this!")
WELC_HELP_TXT = "Your group's welcome/goodbye messages can be personalised in multiple ways. If you want the messages" \
                " to be individually generated, like the default welcome message is, you can use *these* variables:\n" \
                " - `{{first}}`: this represents the user's *first* name\n" \
                " - `{{last}}`: this represents the user's *last* name. Defaults to *first name* if user has no " \
                "last name.\n" \
                " - `{{fullname}}`: this represents the user's *full* name. Defaults to *first name* if user has no " \
                "last name.\n" \
                " - `{{username}}`: this represents the user's *username*. Defaults to a *mention* of the user's " \
                "first name if has no username.\n" \
                " - `{{mention}}`: this simply *mentions* a user - tagging them with their first name.\n" \
                " - `{{id}}`: this represents the user's *id*\n" \
                " - `{{count}}`: this represents the user's *member number*.\n" \
                " - `{{chatname}}`: this represents the *current chat name*.\n" \
                "\nEach variable MUST be surrounded by `{{}}` to be replaced.\n" \
                "Welcome messages also support markdown, so you can make any elements bold/italic/code/links. " \
                "Buttons are also supported, so you can make your welcomes look awesome with some nice intro " \
                "buttons.\n" \
                "To create a button linking to your rules, use this: `[Rules](buttonurl://t.me/{}?start=group_id)`. " \
                "Simply replace `group_id` with your group's id, which can be obtained via /id, and you're good to " \
                "go. Note that group ids are usually preceded by a `-` sign; this is required, so please don't " \
                "remove it.\n" \
                "If you're feeling fun, you can even set images/gifs/videos/voice messages as the welcome message by " \
                "replying to the desired media, and calling /setwelcome.".format(dispatcher.bot.username)


@run_async
@user_admin
def welcome_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


# TODO: get welcome data from group butler snap
# def __import_data__(chat_id, data):
#     welcome = data.get('info', {}).get('rules')
#     welcome = welcome.replace('$username', '{username}')
#     welcome = welcome.replace('$name', '{fullname}')
#     welcome = welcome.replace('$id', '{id}')
#     welcome = welcome.replace('$title', '{chatname}')
#     welcome = welcome.replace('$surname', '{lastname}')
#     welcome = welcome.replace('$rules', '{rules}')
#     sql.set_custom_welcome(chat_id, welcome, sql.Types.TEXT)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref, _, _ = sql.get_welc_pref(chat_id)
    goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
    clean_welc_pref = sql.get_clean_pref(chat_id)
    welc_mutes_pref = sql.get_welc_mutes_pref(chat_id)
    clean_service_pref = sql.get_del_pref(chat_id)
    return "This chat has it's welcome preference set to `{}`.\n" \
           "It's goodbye preference is `{}`. \n\n" \
           "*Service preferences:*\n" \
           "\nClean welcome: `{}`" \
           "\nWelcome mutes: `{}`" \
           "\nClean service: `{}`".format(welcome_pref, goodbye_pref, clean_welc_pref, 
                                          welc_mutes_pref, clean_service_pref)


__help__ = """
{}

*Admin only:*
 - /welcome <on/off>: enable/disable welcome messages.
 - /welcome: shows current welcome settings.
 - /welcome noformat: shows current welcome settings, without the formatting - useful to recycle your welcome messages!
 - /goodbye -> same usage and args as /welcome.
 - /setwelcome <sometext>: set a custom welcome message. If used replying to media, uses that media.
 - /setgoodbye <sometext>: set a custom goodbye message. If used replying to media, uses that media.
 - /resetwelcome: reset to the default welcome message.
 - /resetgoodbye: reset to the default goodbye message.
 - /cleanwelcome <on/off>: On new member, try to delete the previous welcome message to avoid spamming the chat.
 - /cleanservice <on/off>: when someone joins, try to delete the *user* joined the group message.
 - /joinlog <on/off>: when someone joins, send log to channel of join event.
 - /welcomemute <off/soft/strong/aggressive>: all users that join, get muted; a button gets added to the welcome message for them to unmute themselves. \
This proves they aren't a bot! 

*welcome mute types:*
soft - restricts users ability to post media for 24 hours. 
strong - mutes on join until they prove they're not bots.
aggressive - mutes on join until they prove they're not bots, else will be kicked within a minute.

 - /welcomehelp: view more formatting information for custom welcome/goodbye messages.
 
Buttons in welcome messages are made easy, everyone hates URLs visible. With button links you can make your chats look more \
tidy and simplified.

An example of using buttons:
You can create a button using `[button text](buttonurl://example.com)`.

If you wish to add more than 1 buttons simply do the following:
`[Button 1](buttonurl://example.com)`
`[Button 2](buttonurl://github.com:same)`
`[Button 3](buttonurl://google.com)`

The `:same` end of the link merges 2 buttons on same line as 1 button, resulting in 3rd button to be separated \
from same line.

Tip: Buttons must be placed at the end of welcome messages. 
""".format(WELC_HELP_TXT)

__mod_name__ = "Greetings"

NEW_MEM_HANDLER = MessageHandler(Filters.status_update.new_chat_members, new_member)
LEFT_MEM_HANDLER = MessageHandler(Filters.status_update.left_chat_member, left_member)
WELC_PREF_HANDLER = CustomCommandHandler(CMD_PREFIX, "welcome", welcome, filters=Filters.group)
GOODBYE_PREF_HANDLER = CustomCommandHandler(CMD_PREFIX, "goodbye", goodbye, filters=Filters.group)
SET_WELCOME = CustomCommandHandler(CMD_PREFIX, "setwelcome", set_welcome, filters=Filters.group)
SET_GOODBYE = CustomCommandHandler(CMD_PREFIX, "setgoodbye", set_goodbye, filters=Filters.group)
RESET_WELCOME = CustomCommandHandler(CMD_PREFIX, "resetwelcome", reset_welcome, filters=Filters.group)
RESET_GOODBYE = CustomCommandHandler(CMD_PREFIX, "resetgoodbye", reset_goodbye, filters=Filters.group)
CLEAN_WELCOME = CustomCommandHandler(CMD_PREFIX, "cleanwelcome", clean_welcome, filters=Filters.group)
WELCOMEMUTE_HANDLER = CustomCommandHandler(CMD_PREFIX, "welcomemute", welcomemute, filters=Filters.group)
DEL_JOINED_HANDLER = CustomCommandHandler(CMD_PREFIX, ["rmjoin", "cleanservice"], del_joined, filters=Filters.group)
JOIN_EVENT_HANDLER = CustomCommandHandler(CMD_PREFIX, "joinlog", join_event_log, filters=Filters.group)
WELCOME_HELP = CustomCommandHandler(CMD_PREFIX, "welcomehelp", welcome_help)
BUTTON_VERIFY_HANDLER = CallbackQueryHandler(user_button, pattern=r"user_join_")

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(WELCOMEMUTE_HANDLER)
dispatcher.add_handler(BUTTON_VERIFY_HANDLER)
dispatcher.add_handler(DEL_JOINED_HANDLER)
dispatcher.add_handler(JOIN_EVENT_HANDLER)
dispatcher.add_handler(WELCOME_HELP)
