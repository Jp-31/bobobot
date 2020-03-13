import telegram.ext as tg
from telegram import Update
from telegram.ext import CallbackContext

from natalie_bot import CMD_PREFIX


class CustomCommandHandler(tg.PrefixHandler):
    def __init__(self, prefix, command, callback, **kwargs):
        if "admin_ok" in kwargs:
            del kwargs["admin_ok"]
        super().__init__(prefix, command, callback, **kwargs)

    def check_update(self, update: Update):
        if isinstance(update, Update) and update.effective_message:
            message = update.effective_message

            if message.text:
                text_list = message.text.split()
                if text_list[0].split("@")[0].lower() in self.command and len(text_list[0].split("@")) > 1 and text_list[0].split("@")[1] == message.bot.username:
                    filter_result = self.filters(update)
                    if filter_result:
                        return text_list[1:], filter_result
                    else:
                        return False
                else: 
                    if text_list[0].lower() not in self.command:
                        return None
                    filter_result = self.filters(update)
                    if filter_result:
                        return text_list[1:], filter_result
                    else:
                        return False

    def collect_additional_context(self, context, update, dispatcher, check_result):
        if check_result != True and check_result != False and check_result is not None:
            context.args = check_result[0]
            if isinstance(check_result[1], dict):
                context.update(check_result[1])
