from typing import Union, List, Optional

from future.utils import string_types
from telegram import ParseMode, Update, Bot, Chat, User
from telegram.ext import CommandHandler, RegexHandler, Filters, MessageHandler, PrefixHandler, CallbackContext
from telegram.utils.helpers import escape_markdown, mention_html
from telegram.error import BadRequest

from natalie_bot import dispatcher, LOGGER, CMD_PREFIX
from natalie_bot.modules.helper_funcs.misc import is_module_loaded
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.log_channel import loggable
import html

FILENAME = __name__.rsplit(".", 1)[-1]

# If module is due to be loaded, then setup all the magical handlers
if is_module_loaded(FILENAME):
    from natalie_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin, can_delete
    from telegram.ext.dispatcher import run_async

    from natalie_bot.modules.sql import disable_sql as sql

    DISABLE_CMDS = []
    DISABLE_OTHER = []
    ADMIN_CMDS = []

    class DisableAbleCommandHandler(CustomCommandHandler):
        def __init__(self, prefix, command, callback, admin_ok=False, **kwargs):
            super().__init__(prefix, command, callback, **kwargs)
            self.admin_ok = admin_ok
            if isinstance(command, string_types):
                DISABLE_CMDS.append(command)
                if admin_ok:
                    ADMIN_CMDS.append(command)
            else:
                DISABLE_CMDS.extend(command)
                if admin_ok:
                    ADMIN_CMDS.extend(command)


        def check_update(self, update: Update):
            chat = update.effective_chat  # type: Optional[Chat]
            user = update.effective_user  # type: Optional[User]
            
            if super().check_update(update):
                # Should be safe since check_update passed.
                command = update.effective_message.text_html.split(None, 1)[0][1:].split('@')[0]

                # disabled, admincmd, user admin
                if sql.is_command_disabled(chat.id, command.lower()):
                    return command in ADMIN_CMDS and is_user_admin(chat, user.id)

                # not disabled
                else:
                    return True

            return False

        def collect_additional_context(self, context, update, dispatcher, check_result):
            if check_result != True and check_result != False and check_result is not None:
                context.args = check_result[0]
                if isinstance(check_result[1], dict):
                    context.update(check_result[1])
        


    class DisableAbleRegexHandler(MessageHandler):
        def __init__(self, pattern, callback, friendly="", **kwargs):
            super().__init__(Filters.regex(pattern), callback, **kwargs)
            DISABLE_OTHER.append(friendly or pattern)
            self.friendly = friendly or pattern

        def check_update(self, update):
            chat = update.effective_chat
            return super().check_update(update) and not sql.is_command_disabled(chat.id, self.friendly)


    @run_async
    @user_admin
    def disable(update: Update, context: CallbackContext):
        chat = update.effective_chat  # type: Optional[Chat]
        if len(context.args) >= 1:
            disable_cmd = context.args[0]

            if disable_cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                sql.disable_command(chat.id, disable_cmd)
                update.effective_message.reply_text("Disabled the use of `{}`".format(disable_cmd),
                                                    parse_mode=ParseMode.MARKDOWN)
            else:
                update.effective_message.reply_text("That command can't be disabled")

        else:
            update.effective_message.reply_text("What should I disable?")


    @run_async
    @user_admin
    def enable(update: Update, context: CallbackContext):
        chat = update.effective_chat  # type: Optional[Chat]
        if len(context.args) >= 1:
            enable_cmd = context.args[0]
            if enable_cmd.startswith(CMD_PREFIX):
                enable_cmd = enable_cmd[1:]

            if sql.enable_command(chat.id, enable_cmd):
                update.effective_message.reply_text("Enabled the use of `{}`".format(enable_cmd),
                                                    parse_mode=ParseMode.MARKDOWN)
            else:
                update.effective_message.reply_text("Is that even disabled?")

        else:
            update.effective_message.reply_text("What should I enable?")
    
#     @run_async
#     def del_cmds(update: Update, context: CallbackContext):
#         chat = update.effective_chat  # type: Optional[Chat]
#         msg = update.effective_message
#         is_disabled = sql.is_command_disabled(chat.id)
#         disabled = sql.get_cmd_pref(chat.id)
#     
#         for cmd in is_disabled:
#             if disabled:
#                 try:
#                   msg.delete()
#                 except BadRequest as excp:
#                     if excp.message == "Message to delete not found":
#                         pass
#                     else:
#                         LOGGER.exception("Error while deleting disabled messages.")
#                 break
       
    
    @run_async
    @user_admin
    @loggable
    def disable_del(update: Update, context: CallbackContext) -> str:
        chat = update.effective_chat  # type: Optional[Chat]
        user = update.effective_user  # type: Optional[User]

        if not context.args:
            del_pref = sql.get_cmd_pref(chat.id)
            if del_pref:
                update.effective_message.reply_text("All disabled command messages will be currently deleted.")
            else:
                update.effective_message.reply_text("All enabled command messages will not be deleted.")
            return ""
        
        if context.args[0].lower() in ("on", "yes"):
            sql.set_disabledel(str(chat.id), True)
            update.effective_message.reply_text("Disabled messages will now be deleted.")
            return "<b>{}:</b>" \
                   "\n#DISABLED" \
                   "\n<b>• Admin:</b> {}" \
                   "\nHas toggled disabled messages deletion to <code>ON</code>.".format(html.escape(chat.title),
                                                                             mention_html(user.id, user.first_name))
        elif context.args[0].lower() in ("off", "no"):
            sql.set_disabledel(str(chat.id), False)
            update.effective_message.reply_text("Disabled messages will no longer be deleted.")
            return "<b>{}:</b>" \
                   "\n#DISABLED" \
                   "\n<b>• Admin:</b> {}" \
                   "\nHas toggled disabled messages deletion to <code>OFF</code>.".format(html.escape(chat.title),
                                                                              mention_html(user.id, user.first_name))
        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("I understand 'on/yes' or 'off/no' only!")
            return ""


    @run_async
    @user_admin
    def list_cmds(update: Update, context: CallbackContext):
        if DISABLE_CMDS + DISABLE_OTHER:
            result = ""
            for cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                result += " - `{}`\n".format(escape_markdown(cmd))
            update.effective_message.reply_text("The following commands can be disabled:\n{}".format(result),
                                                parse_mode=ParseMode.MARKDOWN)
        else:
            update.effective_message.reply_text("No commands can be disabled.")


    # do not async
    def build_curr_disabled(chat_id: Union[str, int]) -> str:
        disabled = sql.get_all_disabled(chat_id)
        if not disabled:
            return "No commands are disabled!"

        result = ""
        for cmd in disabled:
            result += " • `{}`\n".format(escape_markdown(cmd))
        return "The following commands are disabled in this chat:\n{}".format(result)


    @run_async
    def commands(update: Update, context: CallbackContext):
        chat = update.effective_chat
        msg = update.effective_message  # type: Optional[Message]
        msg.reply_text(build_curr_disabled(chat.id), parse_mode=ParseMode.MARKDOWN)


    def __stats__():
        return "{} disabled items, across {} chats.".format(sql.num_disabled(), sql.num_chats())


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(chat_id, user_id):
        return build_curr_disabled(chat_id)


    __mod_name__ = "Disabling"

    __help__ = """
Not everyone wants every feature that the {} offers. Some commands are best \
left unused; to avoid spam and abuse.

This allows you to disable some commonly used commands, so noone can use them. \
It'll also allow you to auto-delete them, stopping people from blue-texting.

 - /disabled: check the current status of disabled commands

*Admin only:*
 - /disable <commandname>: stop users from using the "commandname" command in this group.
 - /enable <commandname>: allow users to use the "commandname" command in this group again.
 - /disableable: list all disableable commands.
 - /disabledel <on/off/yes/no>: delete disabled commands when used by non-admins.
    """.format(dispatcher.bot.first_name)

    DISABLE_HANDLER = CustomCommandHandler(CMD_PREFIX, "disable", disable, filters=Filters.group)
    ENABLE_HANDLER = CustomCommandHandler(CMD_PREFIX, "enable", enable, filters=Filters.group)
#    DISABLEDEL_HANDLER = CommandHandler("disabledel", disable_del, pass_args=True, filters=Filters.group)
    COMMANDS_HANDLER = CustomCommandHandler(CMD_PREFIX, ["cmds", "disabled"], commands, filters=Filters.group)
    TOGGLE_HANDLER = CustomCommandHandler(CMD_PREFIX, ["disableable", "listcmds"], list_cmds, filters=Filters.group)
#    DISABLEDEL = MessageHandler(Filters.command & Filters.group, del_cmds)

    dispatcher.add_handler(DISABLE_HANDLER)
    dispatcher.add_handler(ENABLE_HANDLER)
    dispatcher.add_handler(COMMANDS_HANDLER)
    dispatcher.add_handler(TOGGLE_HANDLER)
#    dispatcher.add_handler(DISABLEDEL)
#    dispatcher.add_handler(DISABLEDEL_HANDLER)

else:
    DisableAbleCommandHandler = CustomCommandHandler
    DisableAbleRegexHandler = RegexHandler
