import html
from typing import Optional, List
import tldextract

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, RegexHandler, CallbackContext, MessageHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from natalie_bot import dispatcher, CMD_PREFIX
import natalie_bot.modules.sql.setlink_sql as sql
from natalie_bot.modules.disable import DisableAbleCommandHandler
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import bot_admin, can_promote, user_admin, can_pin
from natalie_bot.modules.helper_funcs.extraction import extract_user
from natalie_bot.modules.helper_funcs.msg_types import get_message_type
from natalie_bot.modules.helper_funcs.misc import build_keyboard_alternate
from natalie_bot.modules.helper_funcs.string_handling import markdown_parser
from natalie_bot.modules.log_channel import loggable

ENUM_FUNC_MAP = {
    'Types.TEXT': dispatcher.bot.send_message,
    'Types.BUTTON_TEXT': dispatcher.bot.send_message,
    'Types.STICKER': dispatcher.bot.send_sticker,
    'Types.DOCUMENT': dispatcher.bot.send_document,
    'Types.PHOTO': dispatcher.bot.send_photo,
    'Types.AUDIO': dispatcher.bot.send_audio,
    'Types.VOICE': dispatcher.bot.send_voice,
    'Types.VIDEO': dispatcher.bot.send_video
}

@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def promote(update: Update, context: CallbackContext) -> str:
    chat_id = update.effective_chat.id
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = message.text.split(" ")

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'administrator' or user_member.status == 'creator':
        message.reply_text("How am I meant to promote someone that's already an admin?")
        return ""

    if user_id == context.bot.id:
        message.reply_text("I can't promote myself! Get an admin to do it for me.")
        return ""

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(context.bot.id)

    context.bot.promoteChatMember(chat_id, user_id,
                          can_change_info=bot_member.can_change_info,
                          can_post_messages=bot_member.can_post_messages,
                          can_edit_messages=bot_member.can_edit_messages,
                          can_delete_messages=bot_member.can_delete_messages,
                          can_invite_users=bot_member.can_invite_users,
                          can_restrict_members=bot_member.can_restrict_members,
                          can_pin_messages=bot_member.can_pin_messages,
                          can_promote_members=bot_member.can_promote_members)

    message.reply_text("Successfully promoted!")
    return "<b>{}:</b>" \
           "\n#PROMOTED" \
           "\n<b>• Admin:</b> {}" \
           "\n<b>• User:</b> {}".format(html.escape(chat.title),
                                      mention_html(user.id, user.first_name),
                                      mention_html(user_member.user.id, user_member.user.first_name))


@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def demote(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    args = message.text.split(" ")

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'creator':
        message.reply_text("This person CREATED the chat, how would I demote them?")
        return ""

    if not user_member.status == 'administrator':
        message.reply_text("Can't demote what wasn't promoted!")
        return ""

    if user_id == context.bot.id:
        message.reply_text("I can't demote myself! Get an admin to do it for me.")
        return ""

    try:
        context.bot.promoteChatMember(int(chat.id), int(user_id),
                              can_change_info=False,
                              can_post_messages=False,
                              can_edit_messages=False,
                              can_delete_messages=False,
                              can_invite_users=False,
                              can_restrict_members=False,
                              can_pin_messages=False,
                              can_promote_members=False)
        message.reply_text("Successfully demoted!")
        return "<b>{}:</b>" \
               "\n#DEMOTED" \
               "\n<b>• Admin:</b> {}" \
               "\n<b>• User:</b> {}".format(html.escape(chat.title),
                                          mention_html(user.id, user.first_name),
                                          mention_html(user_member.user.id, user_member.user.first_name))

    except BadRequest:
        message.reply_text("Could not demote. I might not be admin, or the admin status was appointed by another "
                           "user, so I can't act upon them!")
        return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def pin(update: Update, context: CallbackContext) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(" ")

    is_group = chat.type != "private" and chat.type != "channel"

    prev_message = update.effective_message.reply_to_message

    is_silent = True
    if len(args) > 1:
        is_silent = not (args[1].lower() == 'notify' or args[1].lower() == 'loud' or args[1].lower() == 'violent')

    if prev_message and is_group:
        try:
            context.bot.pinChatMessage(chat.id, prev_message.message_id, disable_notification=is_silent)
        except BadRequest as excp:
            if excp.message == "Chat_not_modified":
                pass
            else:
                raise
        return "<b>{}:</b>" \
               "\n#PINNED" \
               "\n<b>• Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name))

    return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def unpin(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user  # type: Optional[User]

    try:
        context.bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message == "Chat_not_modified":
            pass
        else:
            raise

    return "<b>{}:</b>" \
           "\n#UNPINNED" \
           "\n<b>• Admin:</b> {}".format(html.escape(chat.title),
                                       mention_html(user.id, user.first_name))

@run_async
@bot_admin
@user_admin
def invite(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message #type: Optional[Messages]
    
    if chat.username:
        update.effective_message.reply_text("@{}".format(chat.username))
    elif chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        bot_member = chat.get_member(context.bot.id)
        if bot_member.can_invite_users:
            invitelink = context.bot.exportChatInviteLink(chat.id)
            linktext = "Successfully generated new link for *{}:*".format(chat.title)
            link = "`{}`".format(invitelink)
            message.reply_text(linktext, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            message.reply_text(link, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            message.reply_text("I don't have access to the invite link, try changing my permissions!")
    else:
        message.reply_text("I can only give you invite links for supergroups and channels, sorry!")

@run_async
def link_public(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message #type: Optional[Messages]
    chat_id = update.effective_chat.id
    invitelink = sql.get_link(chat_id)
    
    if chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        if chat.username:
           message.reply_text("Link of <b>{}</b>:\n<code>http://t.me/{}</code>".format(chat.title, 
                                                                                       chat.username), 
                                                                                       parse_mode=ParseMode.HTML)
    
        elif invitelink:
             modes = sql.get_link_mode(chat.id)
             if modes == 0:
                message.reply_text("Link of *{}*:\n`{}`".format(chat.title, invitelink), parse_mode=ParseMode.MARKDOWN)
            
             elif modes == 1:
                message.reply_text("Link of *{}*:\n".format(chat.title), parse_mode=ParseMode.MARKDOWN,                
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Join Chat",
                                                                       url="{}".format(invitelink))]]))
            
             elif modes == 2:
                message.reply_text("[{}]({})".format(chat.title, invitelink), parse_mode=ParseMode.MARKDOWN, 
                                                     disable_web_page_preview=True)

             else:
                message.reply_text("Link of <b>{}</b>:\n{}".format(chat.title, invitelink),
                                                                   parse_mode=ParseMode.HTML,
                                                                   disable_web_page_preview=True)
                
        else:
            message.reply_text("The admins of *{}* haven't set link."
                               " \nLink can be set by following: `/setlink` and get link of chat "
                               "using /invitelink, paste the "
                               "link after `/setlink` append.".format(chat.title), parse_mode=ParseMode.MARKDOWN)
        
    else:
        message.reply_text("I can only can save links for private supergroups, sorry!")

@run_async
@user_admin
def set_link(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message
    urls = message.text.split(None, 1)
    
    if chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        if chat.username:
            message.reply_text("{} is a public chat, Current link:\n<code>http://t.me/{}</code>".format(chat.title, 
                                                                                                        chat.username), 
                                                                                               parse_mode=ParseMode.HTML)
        elif len(urls) > 1:
            urls = urls[1]
            to_link = list(set(uri.strip()
                                    for uri in urls.split("\n") if uri.strip()))
            link_suffix = []
        
            for uri in to_link:
                extract_url = tldextract.extract(uri)
                if extract_url.domain and extract_url.suffix:
                    link_suffix.append(extract_url.domain + "." + extract_url.suffix)
                    sql.set_link(chat.id, urls)
                    message.reply_text("The link has been set for {}!\nRetrieve link by #link".format((chat.title)))
                
                else:
                    message.reply_text("Give me valid chat link!")
        
        else:
            reply = "This is not a <b>public supergroup</b>, so you need to write the link near <code>/setlink</code>."
            message.reply_text(reply, parse_mode=ParseMode.HTML)
    else:
         message.reply_text("I can only can save links for private supergroups, sorry!")

@run_async
@user_admin
def clear_link(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message
    chat_id = update.effective_chat.id
    
    if chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
       if chat.username:
           message.reply_text("There are no link set for {} and chat is public.".format(chat.title), parse_mode=ParseMode.HTML)
       
       elif not sql.get_link(chat_id):
          message.reply_text("There is no link set on {}!".format(chat.title))
       
       else:
            sql.rm_link(chat_id, "")
            message.reply_text("Link removed for {}!".format(chat.title))
       
    else:
        message.reply_text("I can only can save links for private supergroups, sorry!")

@run_async
@user_admin
@loggable
def linkmode(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message # type: Optional[Message] 
    args = msg.text.split(" ")
    
    if len(args) >= 1:
        val = args[1].lower()
        if (val == "code"):
            sql.set_link_mode(chat.id, 0)
            msg.reply_text("Link mode set to CODE.")
            return "<b>{}:</b>" \
                   "\n#LINK_MODE" \
                   "\n<b>• Admin:</b> {}" \
                   "\nHas toggled link mode to <b>CODE</b>.".format(html.escape(chat.title),
                                                                      mention_html(user.id, user.first_name))
        elif (val == "button"):
             sql.set_link_mode(chat.id, 1)
             msg.reply_text("Link mode set to BUTTON.")
             return "<b>{}:</b>" \
                    "\n#LINK_MODE" \
                    "\n<b>• Admin:</b> {}" \
                    "\nHas toggled link mode to <b>BUTTON</b>.".format(html.escape(chat.title),
                                                                       mention_html(user.id, user.first_name))
        elif (val == "hyperlink"):
             sql.set_link_mode(chat.id, 2)
             msg.reply_text("Link mode set to HYPERLINK.")
             return "<b>{}:</b>" \
                    "\n#LINK_MODE" \
                    "\n<b>• Admin:</b> {}" \
                    "\nHas toggled link mode to <b>HYPERLINK</b>.".format(html.escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
        
        elif (val == "bare"):
             sql.set_link_mode(chat.id, 3)
             msg.reply_text("Link mode set to BARE LINK.")
             return "<b>{}:</b>" \
                    "\n#LINK_MODE" \
                    "\n<b>• Admin:</b> {}" \
                    "\nHas toggled link mode to <b>BARE LINK</b>.".format(html.escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
                                                                          
        else:
            msg.reply_text("Please enter `code`, `button`, `hyperlink` or `bare`!", parse_mode=ParseMode.MARKDOWN)
            return ""
    else:
        curr_setting = sql.get_link_mode(chat.id)
        reply = "\n Give me a setting! Choose one of: `code`, `button`, `hyperlink` or `bare` only!"
        msg.reply_text(reply.format(curr_setting), parse_mode=ParseMode.MARKDOWN)
        return ""
    
@can_pin
@user_admin
@run_async
@loggable
def permapin(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    text, data_type, content, buttons = get_message_type(message)
    kbuttons = build_keyboard_alternate(buttons)
    log = "<b>{}:</b>" \
                  "\n#PERMAPINNED" \
                  "\n<b>• Admin:</b> {}" \
                  "\nHas pinned custom message.".format(html.escape(chat.title), mention_html(user.id, user.first_name))
    
    try:
        message.delete()
    except BadRequest:
        pass
    if str(data_type) in ('Types.BUTTON_TEXT', 'Types.TEXT'):
        try:
            sendingmsg = context.bot.send_message(chat.id, text + "\n\nLast edited by {}".format(mention_markdown(user.id, user.first_name)), 
                                                                                     parse_mode=ParseMode.MARKDOWN,
                                                                                     disable_web_page_preview=True, 
                                                                                     reply_markup=InlineKeyboardMarkup(kbuttons))
               
        except BadRequest:
            context.bot.send_message("Wrong markdown text!\nIf you don't know what markdown is, "
                             "please type `/markdownhelp` in PM.", parse_mode=ParseMode.MARKDOWN)
            return log
    
    else:
        sendingmsg = ENUM_FUNC_MAP[str(data_type)](chat.id, content, caption=text, parse_mode=ParseMode.MARKDOWN, 
                                   disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(kbuttons))
    try:
        context.bot.pinChatMessage(chat.id, sendingmsg.message_id)
    except BadRequest:
        update.effective_message.reply_text("I don't have rights to pin messages!")
    return log

@run_async
def adminlist(update: Update, context: CallbackContext):
    administrators = update.effective_chat.get_administrators()
    msg = update.effective_message
    text = "Members of <b>{}</b>:".format(update.effective_chat.title or "this chat")
    for admin in administrators:
        user = admin.user
        status = admin.status
        name = "{} {}".format(mention_html(user.id, user.first_name), 
                              mention_html(user.id, user.last_name or "") or "Deleted Account")

        if status == "creator":
            text += "\n <b>Creator:</b>"
            text += "\n<code>🤴🏻 </code>{} \n\n <b>Administrators:</b>".format(name)

    for admin in administrators:
        user = admin.user
        status = admin.status
        chat = update.effective_chat
        count = chat.get_members_count()
        name = "{} {}".format(mention_html(user.id, user.first_name), 
                              mention_html(user.id, user.last_name or "") or "Deleted Account")

        if status == "administrator":
            text += "\n<code>👮🏻 </code>{}".format(name)
            members = "\n\n<b>Members:</b>\n<code>🙎🏻‍♂️ </code> {} users".format(count)
    
    msg.reply_text(text + members, parse_mode=ParseMode.HTML)

def __stats__():
    return "{} chats have links set.".format(sql.num_chats())

def __chat_settings__(chat_id, user_id):
    return "You are *admin*: `{}`".format(
        dispatcher.bot.get_chat_member(chat_id, user_id).status in ("administrator", "creator"))


__help__ = """
Lazy to promote or demote someone for admins? Want to see basic information about chat? \
All stuff about chatroom such as admin lists, pinning or grabbing an invite link can be \
done easily using {}.

 - /adminlist: list of admins and members in the chat
 - /staff: same as /adminlist
 - /link: get the group link for this chat.

*Admin only:*
 - /pin: silently pins the message replied to - add 'loud' or 'notify' to give notifies to users.
 - /unpin: unpins the currently pinned message.
 - /permapin <message>: Pin a custom message via the bot. This message can contain markdown, \
and can be used in replies to media to include extra buttons and captions.
 - /invitelink: generates new invite link.
 - /setlink <your group link here>: setlink link. (Private supergroups only)
 - /clearlink: clear the group link for this chat. (Private supergroups only)
 - /linkmode <code/button/hyperlink/bare>: set your preferred ways to show group link.

 - /promote: promotes the user replied to
 - /demote: demotes the user replied to
 
 An example of set a link:
`/setlink https://t.me/joinchat/HwiIk1RADK5gRMr9FBdOrwtae`

An example of promoting someone to admins:
`/promote @username`; this promotes a user to admins.
""".format(dispatcher.bot.first_name)

__mod_name__ = "Admin"

PIN_HANDLER = CustomCommandHandler(CMD_PREFIX, "pin", pin, filters=Filters.group)
UNPIN_HANDLER = CustomCommandHandler(CMD_PREFIX, "unpin", unpin, filters=Filters.group)
LINK_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "link", link_public)
SET_LINK_HANDLER = CustomCommandHandler(CMD_PREFIX, "setlink", set_link, filters=Filters.group)
LINKMODE_HANDLER = CustomCommandHandler(CMD_PREFIX, "linkmode", linkmode, filters=Filters.group)
RESET_LINK_HANDLER = CustomCommandHandler(CMD_PREFIX, "clearlink", clear_link, filters=Filters.group)
HASH_LINK_HANDLER = MessageHandler(Filters.regex(r"#link"), link_public)
INVITE_HANDLER = CustomCommandHandler(CMD_PREFIX, "invitelink", invite, filters=Filters.group)
PERMAPIN_HANDLER = CustomCommandHandler(CMD_PREFIX, ["permapin", "perma"], permapin, filters=Filters.group)
PROMOTE_HANDLER = CustomCommandHandler(CMD_PREFIX, "promote", promote, filters=Filters.group)
DEMOTE_HANDLER = CustomCommandHandler(CMD_PREFIX, "demote", demote, filters=Filters.group)
ADMINLIST_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, ["adminlist", "staff"], adminlist, filters=Filters.group)

dispatcher.add_handler(PIN_HANDLER)
dispatcher.add_handler(UNPIN_HANDLER)
dispatcher.add_handler(INVITE_HANDLER)
dispatcher.add_handler(LINK_HANDLER)
dispatcher.add_handler(SET_LINK_HANDLER)
dispatcher.add_handler(LINKMODE_HANDLER)
dispatcher.add_handler(RESET_LINK_HANDLER)
dispatcher.add_handler(HASH_LINK_HANDLER)
dispatcher.add_handler(PERMAPIN_HANDLER)
dispatcher.add_handler(PROMOTE_HANDLER)
dispatcher.add_handler(DEMOTE_HANDLER)
dispatcher.add_handler(ADMINLIST_HANDLER)
