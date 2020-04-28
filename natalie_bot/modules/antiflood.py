import html, time
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, run_async, CallbackContext
from telegram.utils.helpers import mention_html

from natalie_bot import dispatcher, CMD_PREFIX
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict, can_delete
from natalie_bot.modules.helper_funcs.string_handling import extract_time
from natalie_bot.modules.log_channel import loggable
from natalie_bot.modules.sql import antiflood_sql as sql

FLOOD_GROUP = 3

permissions = ChatPermissions(can_send_messages=False)

@run_async
@loggable
def check_flood(update: Update, context: CallbackContext) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    limit = sql.get_flood_limit(chat.id)
    flood_time = sql.get_flood_time(chat.id)

    if not user:  # ignore channels
        return ""

    # ignore admins
    if is_user_admin(chat, user.id):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""
    
    soft_flood = sql.get_flood_strength(chat.id)
    if soft_flood:  # mute
        if flood_time[:1] == "0":
                reply_perm = "I don't like the flooding, Remain quiet!" \
                        "\n{} has been muted!".format(mention_html(user.id, user.first_name))
                context.bot.restrict_chat_member(chat.id, user.id, permissions)
                msg.reply_text(reply_perm, parse_mode=ParseMode.HTML)
                msg.delete()
        else:
            mutetime = extract_time(update.effective_message, flood_time)
            reply_temp = "I don't like the flooding, Remain quiet for {}!" \
                     "\n{} has been muted!".format(flood_time, mention_html(user.id, user.first_name))
            context.bot.restrict_chat_member(chat.id, user.id, permissions, until_date=mutetime)            
            msg.reply_text(reply_temp, parse_mode=ParseMode.HTML)
            msg.delete()
           
    else:  # ban
        chat.kick_member(user.id)
        reply_ban = "Frankly, I like to leave the flooding to natural disasters." \
                    "\n{} has been banned!".format(mention_html(user.id, user.first_name))
        msg.reply_text(reply_ban, parse_mode=ParseMode.HTML)
        msg.delete()
    try:
        log = "<b>{}:</b>" \
              "\n#FLOOD_CONTROL" \
              "\n<b>• User:</b> {}" \
              "\n<b>• ID:</b> <code>{}</code>".format(html.escape(chat.title), mention_html(user.id, user.first_name), user.id)
        
        if soft_flood:
           log +="\n<b>• Action:</b> muted"
           log +="\n<b>• Time:</b> {}".format(flood_time)
           
           if flood_time[:1] == "0":
              log +="\n<b>• Time:</b> permanently"
        
        else:
           log +="\n<b>• Action:</b> banned"
        
        log +="\n<b>• Reason:</b> Exceeded flood limit of {} consecutive messages.".format(limit)
                                                                               
        
        return log

    except BadRequest:
        msg.reply_text("I can't kick people here, give me permissions first! Until then, I'll disable anti-flood.")
        sql.set_flood(chat.id, 0)
        return "<b>{}:</b>" \
               "\n#INFO" \
               "\nDon't have kick permissions, so automatically disabled anti-flood.".format(chat.title)


@run_async
@user_admin
@can_restrict
@loggable
def set_flood(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = message.text.split(" ")

    if len(args) >= 1:
        val = args[1].lower()
        if val == "off" or val == "no" or val == "0":
            sql.set_flood(chat.id, 0)
            message.reply_text("Anti-flood has been disabled.")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat.id, 0)
                message.reply_text("Anti-flood has been disabled.")
                return "<b>{}:</b>" \
                       "\n#SETFLOOD" \
                       "\n<b>• Admin:</b> {}" \
                       "\nDisabled Anti-flood.".format(html.escape(chat.title), mention_html(user.id, user.first_name))

            elif amount < 1:
                message.reply_text("Anti-flood has to be either 0 (disabled) or least 1")
                return ""

            else:
                sql.set_flood(chat.id, amount)
                message.reply_text("Anti-flood has been updated and set to {}".format(amount))
                return "<b>{}:</b>" \
                       "\n#SETFLOOD" \
                       "\n<b>• Admin:</b> {}" \
                       "\nSet anti-flood to <code>{}</code>.".format(html.escape(chat.title),
                                                                    mention_html(user.id, user.first_name), amount)

        else:
            message.reply_text("Unrecognised argument - please use a number, 'off', or 'no'.")
    else:
        message.reply_text("Give me an argument! Set a number to enforce against consecutive spams.\n" \
                           "i.e `/setflood 5`: to control consecutive of messages.", parse_mode=ParseMode.MARKDOWN)
    return ""


@run_async
def flood(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message # type: Optional[Message]
    limit = sql.get_flood_limit(chat.id)
    flood_time = sql.get_flood_time(chat.id)
    if limit == 0:
        update.effective_message.reply_text("I'm not currently enforcing flood control!")
    else:
        soft_flood = sql.get_flood_strength(chat.id)
        if soft_flood:
            if flood_time == "0":
                msg.reply_text("I'm currently muting users permanently if they send more than {} " 
                               "consecutive messages.".format(limit, parse_mode=ParseMode.MARKDOWN))
            else:
                msg.reply_text("I'm currently muting users for {} if they send more than {} " 
                               "consecutive messages.".format(flood_time, limit, parse_mode=ParseMode.MARKDOWN))
        else:
            msg.reply_text("I'm currently banning users if they send more than {} " 
                           "consecutive messages.".format(limit, parse_mode=ParseMode.MARKDOWN))
 

@run_async
@user_admin
@loggable
def flood_time(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    flood_time = sql.get_flood_time(chat.id)
    args = message.text.split(" ")
    
    if len(args) >= 1:
        var = args[1]
        if var[:1] == "0":
            mutetime = "0"
            sql.set_flood_time(chat.id, str(var))
            text = "Flood time updated to permanent."
            log =  "<b>{}:</b>\n" \
                   "#FLOOD_TIME\n" \
                   "<b>• Admin:</b> {}\n" \
                   "Has disabled flood time and users will be permanently muted.".format(html.escape(chat.title),
                                                                                  mention_html(user.id,
                                                                                               user.first_name))
            message.reply_text(text)
            return log
       
        else:
            mutetime = extract_time(message, var)
            if mutetime == "":
                return ""
            sql.set_flood_time(chat.id, str(var))
            text = "Flood time updated to {}, Users will be restricted temporarily.".format(var)
            log =  "<b>{}:</b>\n" \
                   "#FLOOD_TIME\n" \
                   "<b>• Admin:</b> {}\n" \
                   "Has updated flood time and users will be muted for {}.".format(html.escape(chat.title),
                                                                                   mention_html(user.id,
                                                                                               user.first_name), 
                                                                                               var)
            message.reply_text(text)
            return log
    else:
        if str(flood_time) == "0":
            message.reply_text("Current settings: flood restrict time is permanent.")
            return ""
        else:
            message.reply_text("Current settings: flood restrict time currently is {}.".format(flood_time))
            return ""

@run_async
@user_admin
@loggable
def set_flood_strength(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(" ")

    if args:
        if args[1].lower() in ("on", "yes"):
            sql.set_flood_strength(chat.id, False)
            msg.reply_text("Exceeding consecutive flood limit will result in a ban!")
            return "<b>{}:</b>\n" \
                   "<b>• Admin:</b> {}\n" \
                   "Has enabled strong flood and users will be banned.".format(html.escape(chat.title),
                                                                            mention_html(user.id, user.first_name))

        elif args[1].lower() in ("off", "no"):
            sql.set_flood_strength(chat.id, True)
            msg.reply_text("Exceeding consecutive flood limit will result in a mute.")
            return "<b>{}:</b>\n" \
                   "<b>• Admin:</b> {}\n" \
                   "Has disabled strong flood and users will only be muted.".format(html.escape(chat.title),
                                                                                  mention_html(user.id,
                                                                                               user.first_name))

        else:
            msg.reply_text("I only understand on/yes/no/off!")
    else:
        soft_flood = sql.get_flood_strength(chat.id)
        if soft_flood == True:
            msg.reply_text("Flood strength is currently set to *mute* users when they exceed the limits, "
                           "user will be muted.",
                           parse_mode=ParseMode.MARKDOWN)
                 
        elif soft_flood:
            msg.reply_text("The default configuration for flood control is currently set as a ban.",
                           parse_mode=ParseMode.MARKDOWN)
        
        elif soft_flood == False:
            msg.reply_text("Flood strength is currently set to *ban* users when they exceed the limits, "
                           "user will be banned.",
                           parse_mode=ParseMode.MARKDOWN)
    return ""

def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    soft_flood = sql.get_flood_strength(chat_id)
    flood_time = sql.get_flood_time(chat_id)
    if limit == 0:
        return "*Not* currently enforcing flood control."
    else:
        if soft_flood:
            return "Anti-flood is set to `{}` messages and *MUTE* if exceeded.".format(limit)
        else:
            return "Anti-flood is set to `{}` messages and *BAN* if exceeded.".format(limit)
__help__ = """
You know how sometimes, people join, send 100 messages, and ruin your chat? With antiflood, that happens no more!

Antiflood allows you to take action on users that send more than x messages in a row. Exceeding the set flood \
will result in banning or muting the user.

 - /flood: Get the current flood control setting

*Admin only:*
 - /setflood <int/'no'/'off'>: enables or disables flood control
 - /strongflood <on/yes/off/no>: If set to on, exceeding the flood limit will result in a ban. Else, will just mute.
 - /setfloodtime x(m/h/d): set flood time for x time. m = minutes, h = hours, d = days. Restricts user from sending any \
messages for period.
 
If you want to flood mute someone temporarily do the following commands:
`/strongflood off`
`/setfloodtime 3h`
The above following commands will mute any spam flooders temporarily for 3 hours.

"""

__mod_name__ = "Anti-Flood"

FLOOD_BAN_HANDLER = MessageHandler(Filters.all & ~Filters.status_update & Filters.group, check_flood)
SET_FLOOD_HANDLER = CustomCommandHandler(CMD_PREFIX, "setflood", set_flood, filters=Filters.group)
SET_FLOOD_TIME_HANDLER = CustomCommandHandler(CMD_PREFIX, "setfloodtime", flood_time, filters=Filters.group)
FLOOD_HANDLER = CustomCommandHandler(CMD_PREFIX, "flood", flood, filters=Filters.group)
FLOOD_STRENGTH_HANDLER = CustomCommandHandler(CMD_PREFIX, "strongflood", set_flood_strength, filters=Filters.group)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(SET_FLOOD_TIME_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_STRENGTH_HANDLER)
