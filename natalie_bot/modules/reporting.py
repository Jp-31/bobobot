import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, ParseMode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, RegexHandler, run_async, Filters, CallbackContext, MessageHandler
from telegram.utils.helpers import mention_html

from natalie_bot import dispatcher, LOGGER, CMD_PREFIX
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import user_not_admin, user_admin
from natalie_bot.modules.log_channel import loggable
from natalie_bot.modules.sql import reporting_sql as sql

REPORT_GROUP = 5


@run_async
@user_admin
def report_setting(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(" ")

    if chat.type == chat.PRIVATE:
        if len(args) >= 1:
            if args[1] in ("yes", "on"):
                sql.set_user_setting(chat.id, True)
                msg.reply_text("Turned on reporting! You'll be notified whenever anyone reports something.")

            elif args[1] in ("no", "off"):
                sql.set_user_setting(chat.id, False)
                msg.reply_text("Turned off reporting! You wont get any reports.")
        else:
            msg.reply_text("Your current report preference is: `{}`".format(sql.user_should_report(chat.id)),
                           parse_mode=ParseMode.MARKDOWN)

    else:
        if len(args) >= 1:
            if args[1] in ("yes", "on"):
                sql.set_chat_setting(chat.id, True)
                msg.reply_text("Turned on reporting! Admins who have turned on reports will be notified when /report "
                               "or @admin are called.")

            elif args[1] in ("no", "off"):
                sql.set_chat_setting(chat.id, False)
                msg.reply_text("Turned off reporting! No admins will be notified on /report or @admin.")
        else:
            msg.reply_text("This chat's current setting is: `{}`".format(sql.chat_should_report(chat.id)),
                           parse_mode=ParseMode.MARKDOWN)


@run_async
@user_not_admin
@loggable
def report(update: Update, context: CallbackContext) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if chat and message.reply_to_message and sql.chat_should_report(chat.id):
        reported_user = message.reply_to_message.from_user  # type: Optional[User]
        chat_name = chat.title or chat.first or chat.username
        admin_list = chat.get_administrators()
        messages = update.effective_message  # type: Optional[Message]
        if chat.username and chat.type == Chat.SUPERGROUP:
            
            reported = "Reported {} to admins. I've notified the admins!".format(mention_html(reported_user.id,
                                                                                       reported_user.first_name))
            msg = "<b>{}:</b>" \
                  "\n#REPORTED" \
                  "\n<b>• Reported user:</b> {} (<code>{}</code>)" \
                  "\n<b>• Reported by:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                                      mention_html(
                                                                          reported_user.id,
                                                                          reported_user.first_name),
                                                                      reported_user.id,
                                                                      mention_html(user.id,
                                                                                   user.first_name),
                                                                      user.id)
            link = "\n<b>• Link:</b> " \
                   "<a href=\"http://telegram.me/{}/{}\">click here</a>".format(chat.username, message.message_id)
            
            
            should_forward = False
            
            messages.reply_text(reported, parse_mode=ParseMode.HTML)
        else:
            reported = "Reported {} to admins. I've notified the admins!".format(mention_html(reported_user.id,
                                                                                       reported_user.first_name))
            msg = "{} is calling for admins in \"{}\"!".format(mention_html(user.id, user.first_name),
                                                               html.escape(chat_name))
            link = ""
            should_forward = True
            
            messages.reply_text(reported, parse_mode=ParseMode.HTML)
        for admin in admin_list:
            if admin.user.is_bot:  # can't message bots
                continue

            if sql.user_should_report(admin.user.id):
                try:
                    context.bot.send_message(admin.user.id, msg + link, parse_mode=ParseMode.HTML)
                    if should_forward:
                        message.reply_to_message.forward(admin.user.id)

                        if len(message.text.split()) > 1:  # If user is giving a reason, send his message too
                            message.forward(admin.user.id)

                except Unauthorized:
                    pass
                except BadRequest as excp:  # TODO: cleanup exceptions
                    LOGGER.exception("Exception while reporting user")
        return msg

    return ""


@run_async
@user_admin
@loggable
def report_solve(update: Update, context: CallbackContext) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if chat and message.reply_to_message:
        reported_user = message.reply_to_message.from_user  # type: Optional[User]
        chat_name = chat.title or chat.first or chat.username
        admin_list = chat.get_administrators()
        messages = update.effective_message  # type: Optional[Message]
        admin = update.effective_user  # type: Optional[User]
        if chat.username and chat.type == Chat.SUPERGROUP:
            
            report_solved = "Admin {} has solved {}'s report!".format(mention_html(admin.id,
                                                                              admin.first_name),
                                                                              mention_html(reported_user.id,
                                                                              reported_user.first_name))
            msg = "<b>{}:</b>" \
                  "\n#REPORT" \
                  "\n<b>• Action:</b> solved" \
                  "\n<b>• Admin:</b> {}" \
                  "\nhas solved {}'s report".format(html.escape(chat.title), mention_html(admin.id,
                                                                          admin.first_name),
                                                                          mention_html(reported_user.id,
                                                                          reported_user.first_name))            
            
            should_forward = True
            
            messages.reply_text(report_solved, parse_mode=ParseMode.HTML)        
        else:
            report_solved = "Admin {} has solved {}'s report!".format(mention_html(user.id,
                                                                              user.first_name),
                                                                              mention_html(reported_user.id,
                                                                              reported_user.first_name))
            msg = "<b>{}:</b>" \
                  "\n#REPORT" \
                  "\n<b>• Action:</b> solved" \
                  "\n<b>• Admin:</b> {}" \
                  "\nhas solved {}'s report".format(html.escape(chat.title), mention_html(user.id,
                                                                          user.first_name),
                                                                          mention_html(reported_user.id,
                                                                          reported_user.first_name))

            should_forward = True
            
            messages.reply_text(report_solved, parse_mode=ParseMode.HTML)
        for admin in admin_list:
            if admin.user.is_bot:  # can't message bots
                continue

            if sql.user_should_report(admin.user.id):
                try:
                    context.bot.send_message(admin.user.id, msg, parse_mode=ParseMode.HTML)
                    if should_forward:
                        message.reply_to_message.forward(admin.user.id)

                        if len(message.text.split()) > 1:  # If user is giving a reason, send his message too
                            message.forward(admin.user.id)

                except Unauthorized:
                    pass
                except BadRequest as excp:  # TODO: cleanup exceptions
                    LOGGER.exception("Exception while solving user's report")
        return msg

    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "This chat is setup to send user reports to admins, via /report and @admin: `{}`".format(
        sql.chat_should_report(chat_id))


def __user_settings__(user_id):
    return "You receive reports from chats you're admin in: `{}`.\nToggle this with /reports in PM.".format(
        sql.user_should_report(user_id))


__mod_name__ = "Reporting"

__help__ = """
We're all busy people who don't have time to monitor our groups 24/7. But how do you \
react if someone in your group is spamming?

Presenting reports; if someone in your group thinks someone needs reporting, they now have \
an easy way to call all admins.

 - /report <reason>: reply to a message to report it to admins.
 - @admin: reply to a message to report it to admins.

*Admin only:*
 - /reports <on/off>: change report setting, or view current status.
   - If done in pm, toggles your status.
   - If in chat, toggles that chat's status.
 - /solve <reason>: reply to a message to solve the report.
 - /solved: same as /solve.

To report a user, simply reply to his message with @admin or /report; \
{} will then reply with a message stating that admins have been notified.
You MUST reply to a message to report a user; you can't just use @admin to tag admins for no reason!

Note that the report commands do not work when admins use them; or when used to report an admin. {} assumes that \
admins don't need to report, or be reported!
""".format(dispatcher.bot.first_name, dispatcher.bot.first_name)

REPORT_HANDLER = CustomCommandHandler(CMD_PREFIX, "report", report, filters=Filters.group)
SOLVE_HANDLER = CustomCommandHandler(CMD_PREFIX, ["solve", "solved"], report_solve, filters=Filters.group)
SETTING_HANDLER = CustomCommandHandler(CMD_PREFIX, "reports", report_setting)
ADMIN_REPORT_HANDLER = MessageHandler(Filters.regex("(?i)@admin(s)?"), report)

dispatcher.add_handler(REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(SOLVE_HANDLER, REPORT_GROUP)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(SETTING_HANDLER)
