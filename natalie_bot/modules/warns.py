import html
import re
from typing import Optional, List

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery
from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, DispatcherHandlerStop, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram.utils.helpers import mention_html

from natalie_bot import dispatcher, BAN_STICKER, CMD_PREFIX
from natalie_bot.modules.disable import DisableAbleCommandHandler
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import is_user_admin, bot_admin, user_admin_no_reply, user_admin, \
    can_restrict
from natalie_bot.modules.helper_funcs.extraction import extract_text, extract_user_and_text, extract_user
from natalie_bot.modules.helper_funcs.filters import CustomFilters
from natalie_bot.modules.helper_funcs.misc import split_message
from natalie_bot.modules.helper_funcs.string_handling import split_quotes, extract_time
from natalie_bot.modules.log_channel import loggable
from natalie_bot.modules.sql import warns_sql as sql
from natalie_bot.modules.sql import users_sql as sql_user

WARN_HANDLER_GROUP = 9


# Not async
def warn(user: User, chat: Chat, reason: str, message: Message, warner: User = None) -> str:
    if is_user_admin(chat, user.id): #ignore for admins
#         message.reply_text("Damn admins, can't even be warned!")
        return ""

    if warner:
        warner_tag = mention_html(warner.id, warner.first_name)
    
    else:
        warner_tag = "Automated warn filter."

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Remove warn (admin only)", callback_data="rm_warn({})".format(user.id))]])
    
    limit, soft_warn, warn_mode = sql.get_warn_setting(chat.id)
    num_warns, reasons = sql.warn_user(user.id, chat.id, reason)
    num = 1
    warn_time = sql.get_warn_time(chat.id)
    if num_warns >= limit:
        sql.reset_warns(user.id, chat.id)
        if not soft_warn:
            if not warn_mode:
                chat.kick_member(user.id)
                reply = "{} warnings, {} has been banned!".format(limit, mention_html(user.id, user.first_name))
            
            elif warn_mode == 1:
                chat.kick_member(user.id)
                reply = "{} warnings, {} has been banned!".format(limit, mention_html(user.id, user.first_name))
            
            elif warn_mode == 2:
                chat.unban_member(user.id)
                reply = "{} warnings, {} has been kicked!".format(limit, mention_html(user.id, user.first_name))
            
            elif warn_mode == 3:
                message.bot.restrict_chat_member(chat.id, user.id, can_send_messages=False)
                reply = "{} warnings, {} has been muted!".format(limit, mention_html(user.id, user.first_name))
            
            elif warn_mode == 4:
                warn_time = sql.get_warn_time(chat.id)
                mutetime = extract_time(message, warn_time)
                message.bot.restrict_chat_member(chat.id, user.id, until_date=mutetime, can_send_messages=False)
                reply = "{} warnings, {} has been temporarily muted for {}!".format(limit, mention_html(user.id, 
                                                                                    user.first_name), 
                                                                                    warn_time)
            elif warn_mode == 5:
                warn_time = sql.get_warn_time(chat.id)
                tbantime = extract_time(message, warn_time)
                chat.kick_member(user.id, until_date=tbantime)
                reply = "{} warnings, {} has been temporarily banned for {}!".format(limit, mention_html(user.id, 
                                                                                    user.first_name), 
                                                                                    warn_time)
        else:
            chat.kick_member(user.id)
            reply = "{} warnings, {} has been banned!".format(limit, mention_html(user.id, user.first_name))
            
        for warn_reason in reasons:
            reply += "\n {}. {}".format(num, html.escape(warn_reason))
            num += 1

        message.bot.send_sticker(chat.id, BAN_STICKER)  # banhammer natalie sticker
        
        log_reason = "<b>{}:</b>" \
                     "\n#WARN_ACTION" \
                     "\n<b>• Admin:</b> {}" \
                     "\n<b>• User:</b> {}" \
                     "\n<b>• ID:</b> <code>{}</code>".format(html.escape(chat.title),
                                                            warner_tag,
                                                            mention_html(user.id, user.first_name), user.id)
        if not warn_mode:
            log_reason += "\n<b>• Action:</b> banned"
        
        elif warn_mode == 1:
            log_reason += "\n<b>• Action:</b> banned"
        
        elif warn_mode == 2:
            log_reason += "\n<b>• Action:</b> kicked"
        
        elif warn_mode == 3:
            log_reason += "\n<b>• Action:</b> muted"
        
        elif warn_mode == 4:
            log_reason += "\n<b>• Action:</b> tmuted" \
                          "\n<b>• Time:</b> {}".format(warn_time)
                           
        elif warn_mode == 5:
            log_reason += "\n<b>• Action:</b> tbanned" \
                          "\n<b>• Time:</b> {}".format(warn_time)
            
        
        log_reason += "\n<b>• Counts:</b> <code>{}/{}</code>".format(num_warns, limit)
        
        if reason:
            log_reason += "\n<b>• Reason:</b> {}".format(reason)

    else:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Remove warn (admin only)", callback_data="rm_warn({})".format(user.id))]])

        if num_warns+1 == limit:
            if not warn_mode:
                action_mode = "banned"
            elif warn_mode == 1:
                action_mode = "banned"
            elif warn_mode == 2:
                action_mode = "kicked"
            elif warn_mode == 3:
                action_mode = "muted"
            elif warn_mode == 4:
                action_mode = "temporarily muted"
            elif warn_mode == 5:
                action_mode = "temporarily banned"
            reply = "{} has {}/{} warnings... watch out, you'll be {} in the last warn!".format(mention_html(user.id, 
                                                                                                 user.first_name), 
                                                                                                num_warns, 
                                                                                                limit, action_mode)
        else:
            reply = "{} has {}/{} warnings... watch out!".format(mention_html(user.id, user.first_name), num_warns, limit)
        if reason:
            reply += "\nReason for last warn:\n{}".format(html.escape(reason))

        log_reason = "<b>{}:</b>" \
                     "\n#WARN" \
                     "\n<b>• Admin:</b> {}" \
                     "\n<b>• User:</b> {}" \
                     "\n<b>• ID:</b> <code>{}</code>" \
                     "\n<b>• Counts:</b> <code>{}/{}</code>".format(html.escape(chat.title),
                                                                    warner_tag,
                                                                    mention_html(user.id, user.first_name), user.id, 
                                                                    num_warns, limit)
        if reason:
                log_reason += "\n<b>• Reason:</b> {}".format(reason)

    try:
        message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML, quote=False)
        else:
            raise
    return log_reason

@run_async
@bot_admin
@loggable
def button(update: Update, context: CallbackContext) -> str:
    query = update.callback_query  # type: Optional[CallbackQuery]
    user = update.effective_user  # type: Optional[User]
    match = re.match(r"rm_warn\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat = update.effective_chat  # type: Optional[Chat]
        res = sql.remove_warn(user_id, chat.id)
        
        if not is_user_admin(chat, int(user.id)):
            query.answer(text="You need to be an admin to do this.")
            return ""
        
        if res:
            update.effective_message.edit_text(
                "Warn removed by {}.".format(mention_html(user.id, user.first_name)),
                parse_mode=ParseMode.HTML)
            user_member = chat.get_member(user_id)
            return "<b>{}:</b>" \
                   "\n#UNWARN" \
                   "\n<b>• Admin:</b> {}" \
                   "\n<b>• User:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(user_member.user.id, user_member.user.first_name))
        else:
            update.effective_message.edit_text(
                "User {} has already has no warns.".format(mention_html(user.id, user.first_name)),
                parse_mode=ParseMode.HTML)

    return ""


@run_async
@user_admin
@can_restrict
@loggable
def warn_user(update: Update, context: CallbackContext) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    warner = update.effective_user  # type: Optional[User]
    
    user_id, reason = extract_user_and_text(message, message.text.split(" "))

    if user_id:
        if message.reply_to_message and message.reply_to_message.from_user.id == user_id:
            return warn(message.reply_to_message.from_user, chat, reason, message.reply_to_message, warner)
        else:
            return warn(chat.get_member(user_id).user, chat, reason, message, warner)
    else:
        message.reply_text("No user was designated!")
    return ""


@run_async
@user_admin
@bot_admin
@loggable
def reset_warns(update: Update, context: CallbackContext) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = message.text.split(" ")

    user_id = extract_user(message, args)

    if user_id:
        sql.reset_warns(user_id, chat.id)
        message.reply_text("Warnings have been reset!")
        warned = chat.get_member(user_id).user
        return "<b>{}:</b>" \
               "\n#RESETWARNS" \
               "\n<b>• Admin:</b> {}" \
               "\n<b>• User:</b> {}" \
               "\n<b>• ID:</b> <code>{}</code>".format(html.escape(chat.title),
                                                       mention_html(user.id, user.first_name),
                                                       mention_html(warned.id, warned.first_name),
                                                       warned.id)
    else:
        message.reply_text("No user has been designated!")
    return ""
    
@run_async
@user_admin
@bot_admin
@loggable
def remove_warns(update: Update, context: CallbackContext) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = message.text.split(" ")

    user_id = extract_user(message, args)

    if user_id:
        sql.remove_warn(user_id, chat.id)
        warned = chat.get_member(user_id).user
        rm_warnuser = chat.get_member(user_id)
        
        message.reply_text("Admin {} removed last warn for {}.".format(mention_html(user.id, user.first_name),
                                                                       mention_html(rm_warnuser.user.id, 
                                                                                    rm_warnuser.user.first_name)), 
                                                                                    parse_mode=ParseMode.HTML)
        return "<b>{}:</b>" \
               "\n#UNWARN" \
               "\n<b>• Admin:</b> {}" \
               "\n<b>• User:</b> {}" \
               "\n<b>• ID:</b> <code>{}</code>".format(html.escape(chat.title),
                                                       mention_html(user.id, user.first_name),
                                                       mention_html(warned.id, warned.first_name),
                                                       warned.id)
    else:
        message.reply_text("No user has been designated!")
    return ""


@run_async
def warns(update: Update, context: CallbackContext):
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    user_id = extract_user(message, message.text.split(" ")) or update.effective_user.id
    member = chat.get_member(user_id)
    result = sql.get_warns(user_id, chat.id)
    num = 1

    if result and result[0] != 0:
        num_warns, reasons = result
        limit, soft_warn, warn_mode = sql.get_warn_setting(chat.id)

        if reasons:
            text = "User {} has {}/{} warnings, for the following reasons:".format(mention_html(member.user.id, 
                                                                                   member.user.first_name),
                                                                                   num_warns, limit)
            for reason in reasons:
                text += "\n {}. {}".format(num, reason)
                num += 1

            msgs = split_message(text)
            for msg in msgs:
                update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)

    else:
        update.effective_message.reply_text("User {} hasn't got any warnings!".format(mention_html(member.user.id, 
                                                                                      member.user.first_name)),
                                                                                      parse_mode=ParseMode.HTML)


# Dispatcher handler stop - do not async
@user_admin
def add_warn_filter(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    args = msg.text.split(None, 1)  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) >= 2:
        # set trigger -> lower, so as to avoid adding duplicate filters with different cases
        keyword = extracted[0].lower()
        content = extracted[1]

    else:
        return

    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(WARN_HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, WARN_HANDLER_GROUP)

    sql.add_warn_filter(chat.id, keyword, content)

    update.effective_message.reply_text("Warn handler added for '{}'!".format(keyword))
    raise DispatcherHandlerStop


@user_admin
def remove_warn_filter(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    args = msg.text.split(None, 1)  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) < 1:
        return

    to_remove = extracted[0]

    chat_filters = sql.get_chat_warn_triggers(chat.id)

    if not chat_filters:
        msg.reply_text("No warning filters are active here!")
        return

    for filt in chat_filters:
        if filt == to_remove:
            sql.remove_warn_filter(chat.id, to_remove)
            msg.reply_text("Yep, I'll stop warning people for that.")
            raise DispatcherHandlerStop

    msg.reply_text("That's not a current warning filter - run /warnlist for all active warning filters.")


@run_async
def list_warn_filters(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    all_handlers = sql.get_chat_warn_triggers(chat.id)
    CURRENT_WARNING_FILTER_STRING = "The following warning filters are currently active in {}:\n".format(chat.title)

    if not all_handlers:
        update.effective_message.reply_text("No warning filters are active here!")
        return

    filter_list = CURRENT_WARNING_FILTER_STRING
    for keyword in all_handlers:
        entry = " • <code>{}</code>\n".format(html.escape(keyword))
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == CURRENT_WARNING_FILTER_STRING:
        update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)


@run_async
@loggable
def reply_filter(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]

    chat_warn_filters = sql.get_chat_warn_triggers(chat.id)
    to_match = extract_text(message)
    if not to_match:
        return ""

    for keyword in chat_warn_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            user = update.effective_user  # type: Optional[User]
            warn_filter = sql.get_warn_filter(chat.id, keyword)
            return warn(user, chat, warn_filter.reply, message)
    return ""


@run_async
@user_admin
@loggable
def set_warn_limit(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(" ")

    if args:
        if args[1].isdigit():
            if int(args[1]) < 3:
                msg.reply_text("The minimum warn limit is 3!")
            else:
                sql.set_warn_limit(chat.id, int(args[1]))
                msg.reply_text("Updated the warn limit to {}".format(args[1]))
                return "<b>{}:</b>" \
                       "\n#SET_WARN_LIMIT" \
                       "\n<b>• Admin:</b> {}" \
                       "\nSet the warn limit to <code>{}</code>".format(html.escape(chat.title),
                                                                        mention_html(user.id, user.first_name), args[1])
        else:
            msg.reply_text("Give me a number as an arg!")
    else:
        limit, soft_warn, warn_mode = sql.get_warn_setting(chat.id)

        msg.reply_text("The current warn limit is {}".format(limit))
    return ""


@run_async
@user_admin
def set_warn_strength(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(" ")

    if args:
        if args[1].lower() in ("on", "yes"):
            sql.set_warn_strength(chat.id, False)
            msg.reply_text("Too many warns will now result in a ban!")
            return "<b>{}:</b>\n" \
                   "<b>• Admin:</b> {}\n" \
                   "Has enabled strong warns. Users will be banned.".format(html.escape(chat.title),
                                                                            mention_html(user.id, user.first_name))

        elif args[1].lower() in ("off", "no"):
            sql.set_warn_strength(chat.id, True)
            msg.reply_text("Too many warns will now result in a kick! Users will be able to join again after.")
            return "<b>{}:</b>\n" \
                   "<b>• Admin:</b> {}\n" \
                   "Has disabled strong warns. Users will only be kicked.".format(html.escape(chat.title),
                                                                                  mention_html(user.id,
                                                                                               user.first_name))

        else:
            msg.reply_text("I only understand on/yes/no/off!")
    else:
        limit, soft_warn, warn_mode = sql.get_warn_setting(chat.id)
        if soft_warn:
            msg.reply_text("Warns are currently set to *kick* users when they exceed the limits.",
                           parse_mode=ParseMode.MARKDOWN)
        else:
            msg.reply_text("Warns are currently set to *ban* users when they exceed the limits.",
                           parse_mode=ParseMode.MARKDOWN)
    return ""

@run_async
@user_admin
@loggable
def set_warn_mode(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(" ")

    if len(args) > 1:
        if args[1].lower() in ("ban"):
            sql.set_warn_mode(chat.id, 1)
            msg.reply_text("Updated warning mode to: ban")
            
            return "<b>{}:</b>\n" \
                   "<b>• Admin:</b> {}\n" \
                   "Has updated warn mode to ban.".format(html.escape(chat.title),
                                                                            mention_html(user.id, user.first_name))

        elif args[1].lower() in ("kick"):
            sql.set_warn_mode(chat.id, 2)
            msg.reply_text("Updated warning mode to: kick")
            return "<b>{}:</b>\n" \
                   "<b>• Admin:</b> {}\n" \
                   "Has updated warn mode to kick.".format(html.escape(chat.title),
                                                                                  mention_html(user.id,
                                                                                               user.first_name))
        
        elif args[1].lower() in ("mute"):
            sql.set_warn_mode(chat.id, 3)
            msg.reply_text("Updated warning mode to: mute")
            return "<b>{}:</b>\n" \
                   "<b>• Admin:</b> {}\n" \
                   "Has updated warn mode to mute.".format(html.escape(chat.title), mention_html(user.id,
                                                                                               user.first_name))
        
        
        elif args[1].lower() in ("tmute"):
            try:
                val = args[2].lower()
                sql.set_warn_mode(chat.id, 4)
                sql.set_warn_time(chat.id, str(val))
                msg.reply_text("Updated warning mode to: tmute for {}".format(val))
            
                return "<b>{}:</b>\n" \
                       "<b>• Admin:</b> {}\n" \
                       "Has updated warn mode to tmute for {}.".format(html.escape(chat.title), mention_html(user.id,
                                                                                                   user.first_name), val)
            except:      
            	msg.reply_text("You haven't specified a time!")
            	return""
        
        elif args[1].lower() == "tban":
            try:
                val = args[2].lower()
                sql.set_warn_mode(chat.id, 5)
                sql.set_warn_time(chat.id, str(val))
                msg.reply_text("Updated warning mode to: tban for {}".format(val))
            
                return "<b>{}:</b>\n" \
                       "<b>• Admin:</b> {}\n" \
                       "Has updated warn mode to tban for {}.".format(html.escape(chat.title), mention_html(user.id,
                                                                                               user.first_name), val)
                
            except:      
            	msg.reply_text("You haven't specified a time!")
            	return""
                
        else:
            msg.reply_text("Unknown Type command. I only understand ban/kick/mute/tmute/tban!")
            
    else:
        limit, soft_warn, warn_mode = sql.get_warn_setting(chat.id)
        warn_time = sql.get_warn_time(chat.id)
        if not soft_warn:
            if not warn_mode:
                text = "You need to specify an action to take upon too many warns." \
                       "Current modes are: ban/kick/mute/tmute/tban"
            
            elif warn_mode == 1:
                text = "You need to specify an action to take upon too many warns.\n" \
                       "Current mode: `ban`"
            
            elif warn_mode == 2:
                text = "You need to specify an action to take upon too many warns.\n" \
                       "Current mode: `kick`"
           
            elif warn_mode == 3:
                text = "You need to specify an action to take upon too many warns.\n" \
                       "Current mode: `mute`"
                       
            elif warn_mode == 4:
                text = "You need to specify an action to take upon too many warns.\n" \
                       "Current mode: `tmute for {}`".format(warn_time)
            
            elif warn_mode == 5:
                text = "You need to specify an action to take upon too many warns.\n" \
                       "Current mode: `tban for {}`".format(warn_time)
            msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
        else:
            msg.reply_text("You need to specify an action to take upon too many warns. "
                           "Current modes are: ban/kick/mute/tmute/tban", parse_mode=ParseMode.MARKDOWN)
    return ""

def __stats__():
    return "{} overall warns, across {} chats.\n" \
           "{} warn filters, across {} chats.".format(sql.num_warns(), sql.num_warn_chats(),
                                                      sql.num_warn_filters(), sql.num_warn_filter_chats())


def __import_data__(chat_id, data):
    for user_id, count in data.get('warns', {}).items():
        for x in range(int(count)):
            sql.warn_user(user_id, chat_id)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    num_warn_filters = sql.num_warn_chat_filters(chat_id)
    limit, soft_warn, warn_mode = sql.get_warn_setting(chat_id)
    return "This chat has `{}` warn filters. It takes `{}` warns " \
           "before the user gets *{}*.".format(num_warn_filters, limit, "kicked" if soft_warn else "banned")


__help__ = """
Keep your members in check with warnings; stop them getting out of control!

 - /warns <userhandle>: get a user's number, and reason, of warnings.
 - /warnlist: list of all current warning filters

*Admin only:*
 - /warn <userhandle>: warn a user. After 3 warns, the user will be banned from the group. Can also be used as a reply.
 - /resetwarn <userhandle>: reset the warnings for a user. Can also be used as a reply.
 - /rmwarn <userhandle>: removes latest warn for a user. It also can be used as reply.
 - /unwarn <userhandle>: same as /rmwarn
 - /addwarn <keyword> <reply message>: set a warning filter on a certain keyword.
 - /nowarn <keyword>: stop a warning filter.
 - /setwarnlimit <num of warn>: sets the number of warns before an action is taken upon the user.
 - /setwarnmode ban/kick/mute/tmute/tban: set the action to perform when warnings have been exceeded.

If you're looking for a way to automatically warn users when they say certain things, use the /addwarn command.

An example of setting multiword warns filter:
`- /addwarn "very angry" This is an angry user`

This will automatically warn a user that triggers "very angry", with reason of 'This is an angry user'.

An example of how to set a new multiword warning:
`/warn @user Because warning is fun`

This will warn the user called @user, with a reason of 'Because warning is fun'
"""

__mod_name__ = "Warnings"

WARN_HANDLER = CustomCommandHandler(CMD_PREFIX, "warn", warn_user, filters=Filters.group)
RESET_WARN_HANDLER = CustomCommandHandler(CMD_PREFIX, ["resetwarn", "resetwarns"], reset_warns, filters=Filters.group)
REMOVE_WARNS_HANDLER = CustomCommandHandler(CMD_PREFIX, ["rmwarn", "unwarn"], remove_warns, filters=Filters.group)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(button, pattern=r"rm_warn")
MYWARNS_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "warns", warns, filters=Filters.group)
ADD_WARN_HANDLER = CustomCommandHandler(CMD_PREFIX, "addwarn", add_warn_filter, filters=Filters.group)
RM_WARN_HANDLER = CustomCommandHandler(CMD_PREFIX, ["nowarn", "stopwarn"], remove_warn_filter, filters=Filters.group)
LIST_WARN_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, ["warnlist", "warnfilters"], list_warn_filters, filters=Filters.group, admin_ok=True)
WARN_FILTER_HANDLER = MessageHandler(CustomFilters.has_text & Filters.group, reply_filter)
WARN_LIMIT_HANDLER = CustomCommandHandler(CMD_PREFIX, ["warnlimit", "setwarnlimit"], set_warn_limit, filters=Filters.group)
# WARN_STRENGTH_HANDLER = CommandHandler(CMD_PREFIX, "strongwarn", set_warn_strength, pass_args=True, filters=Filters.group)
WARN_MODE_HANDLER = CustomCommandHandler(CMD_PREFIX, ["warnmode", "setwarnmode"], set_warn_mode, filters=Filters.group)

dispatcher.add_handler(WARN_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
dispatcher.add_handler(RESET_WARN_HANDLER)
dispatcher.add_handler(REMOVE_WARNS_HANDLER)
dispatcher.add_handler(MYWARNS_HANDLER)
dispatcher.add_handler(ADD_WARN_HANDLER)
dispatcher.add_handler(RM_WARN_HANDLER)
dispatcher.add_handler(LIST_WARN_HANDLER)
dispatcher.add_handler(WARN_LIMIT_HANDLER)
# dispatcher.add_handler(WARN_STRENGTH_HANDLER)
dispatcher.add_handler(WARN_MODE_HANDLER)
dispatcher.add_handler(WARN_FILTER_HANDLER, WARN_HANDLER_GROUP)
