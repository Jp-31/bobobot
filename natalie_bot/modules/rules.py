import html
from typing import Optional, List

from telegram import Message, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, Filters, CallbackContext
from telegram.utils.helpers import escape_markdown, mention_html

import natalie_bot.modules.sql.rules_sql as sql
from natalie_bot import dispatcher, CMD_PREFIX
from natalie_bot.modules.log_channel import loggable
from natalie_bot.modules.disable import DisableAbleCommandHandler
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import user_admin
from natalie_bot.modules.helper_funcs.string_handling import markdown_parser


@run_async
def get_rules(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    send_rules(update, chat_id)


# Do not async - not from a handler
def send_rules(update, chat_id, from_pm=False):
    bot = dispatcher.bot
    user = update.effective_user  # type: Optional[User]
    try:
        chat = bot.get_chat(chat_id)
    except BadRequest as excp:
        if excp.message == "Chat not found" and from_pm:
            bot.send_message(user.id, "The rules shortcut for this chat hasn't been set properly! Ask admins to "
                                      "fix this.")
            return
        else:
            raise

    rules = sql.get_rules(chat_id)
    chat_rules = sql.get_chat_rules_pref(chat.id)
    text = "The rules for *{}* are:\n\n{}".format(escape_markdown(chat.title), rules)
    
    if chat_rules and rules:
        update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    elif not rules:
        update.effective_message.reply_text("The group admins haven't set any rules for this chat yet. "
                                            "This probably doesn't mean it's lawless though...!")
    
    elif not chat_rules:
        if from_pm and rules:
            bot.send_message(user.id, text, parse_mode=ParseMode.MARKDOWN)
            
        elif rules:
            update.effective_message.reply_text("Contact me in PM to get {}'s rules.".format(chat.title),
                                                reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text="Rules",
                                                                       url="t.me/{}?start={}".format(bot.username,
                                                                                                     chat_id))]]))


@run_async
@user_admin
@loggable
def set_rules(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user = update.effective_user
    chat = update.effective_chat
    msg = update.effective_message  # type: Optional[Message]
    raw_text = msg.text
    args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
    if len(args) == 2:
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        markdown_rules = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)

        sql.set_rules(chat_id, markdown_rules)
        update.effective_message.reply_text("Successfully set rules for this group.")
    
    log = "<b>{}:</b>" \
          "\n#RULES" \
          "\n<b>• Action:</b> added" \
          "\n<b>• Admin:</b> {}" \
          "\n<b>• New rules:</b> \n{}".format(html.escape(chat.title), mention_html(user.id, user.first_name), markdown_rules)
    
    return log

@run_async
@user_admin
@loggable
def chat_rules(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    chat_id = update.effective_chat.id
    user = update.effective_user  # type: Optional[User]
    args = update.effective_message.text.split(" ")

    if not args:
        chat_rules_pref = sql.get_chat_rules_pref(chat.id)
        if chat_rules_pref:
            update.effective_message.reply_text("I should be sending current rules of this chat here.")
        else:
            update.effective_message.reply_text("I'm currently sending rules via my PM!")
        return ""

    if args[1].lower() in ("on", "yes"):
        sql.set_chat_rules(str(chat.id), True)
        update.effective_message.reply_text("I'll send rules of this chat here, instead of PM!")
        return "<b>{}:</b>" \
               "\n#RULES_SETTING" \
               "\n<b>Admin:</b> {}" \
               "\nHas toggled PM rules to <code>OFF</code>.".format(html.escape(chat.title),
                                                                         mention_html(user.id, user.first_name))
    elif args[1].lower() in ("off", "no"):
        sql.set_chat_rules(str(chat.id), False)
        update.effective_message.reply_text("I won't be sending rules here.")
        return "<b>{}:</b>" \
               "\n#RULES_SETTING" \
               "\n<b>Admin:</b> {}" \
               "\nHas toggled PM rules to <code>ON</code>.".format(html.escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
    else:
        # idek what you're writing, say yes or no
        update.effective_message.reply_text("I understand 'on/yes' or 'off/no' only!")
        return ""

@run_async
@user_admin
@loggable
def clear_rules(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user = update.effective_user
    chat = update.effective_chat
    sql.set_rules(chat_id, "")
    update.effective_message.reply_text("Successfully cleared rules!")
    log = "<b>{}:</b>" \
          "\n#RULES" \
          "\n<b>• Action:</b> cleared" \
          "\n<b>• Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name))
    
    return log


def __stats__():
    return "{} chats have rules set.".format(sql.num_chats())


def __import_data__(chat_id, data):
    # set chat rules
    rules = data.get('info', {}).get('rules', "")
    sql.set_rules(chat_id, rules)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "This chat has had it's rules set: `{}`".format(bool(sql.get_rules(chat_id)))


__help__ = """
Every chat works with different rules; this module will help make those rules clearer!

 - /rules: get the rules for this chat.

*Admin only:*
 - /setrules <your rules here>: set the rules for this chat.
 - /clearrules: clear the rules for this chat.
 - /chatrules <yes/no/on/off>: should the rules be sent to chat. Default: no.

"""

__mod_name__ = "Rules"

GET_RULES_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "rules", get_rules, filters=Filters.group)
SET_RULES_MODE = CustomCommandHandler(CMD_PREFIX, "chatrules", chat_rules, filters=Filters.group)
SET_RULES_HANDLER = CustomCommandHandler(CMD_PREFIX, "setrules", set_rules, filters=Filters.group)
RESET_RULES_HANDLER = CustomCommandHandler(CMD_PREFIX, "clearrules", clear_rules, filters=Filters.group)

dispatcher.add_handler(GET_RULES_HANDLER)
dispatcher.add_handler(SET_RULES_HANDLER)
dispatcher.add_handler(SET_RULES_MODE)
dispatcher.add_handler(RESET_RULES_HANDLER)
