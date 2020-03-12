import html

from telegram import Bot, ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, MessageHandler, run_async, CallbackContext
from typing import Optional, List

import tldextract
from natalie_bot import LOGGER, dispatcher, CMD_PREFIX
from natalie_bot.modules.disable import DisableAbleCommandHandler
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from telegram.utils.helpers import mention_html
from natalie_bot.modules.helper_funcs.chat_status import user_admin, user_not_admin
from natalie_bot.modules.sql import urlwhitelist_sql as sql
from natalie_bot.modules.log_channel import loggable
from natalie_bot.modules.helper_funcs.misc import split_message


@run_async
@user_admin
@loggable
def add_whitelist_url(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user
    words = msg.text.split(None, 1)
    if len(words) > 1:
        text = words[1]
        to_whitelist = list(set(domain.strip() for domain in text.split("\n") if domain.strip()))
        
        log = "<b>{}:</b>" \
          "\n#WHITELISTS" \
          "\n<b>• Action:</b> added" \
          "\n<b>• Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, 
                                                                  user.first_name))
        
        for domain in to_whitelist:
            sql.add_to_whitelist(chat.id, domain)

        if len(to_whitelist) == 1:
            msg.reply_text("Added <code>{}</code> to the whitelist!".format(html.escape(to_whitelist[0])),
                           parse_mode=ParseMode.HTML)
            log += "\n<b>• Domain:</b>\n"
            for domain in to_whitelist:
               log += "   <code>{}</code>\n".format(domain)

        else:
            msg.reply_text(
                "Added <code>{}</code> domain(s) to the whitelist.".format(len(to_whitelist)), parse_mode=ParseMode.HTML)
            num = 1
            log += "\n<b>• Domains:</b>\n"
            for domain in to_whitelist:
               log += "   {}. <code>{}</code>\n".format(num, domain)
               num += 1            
        
        return log

    else:
        msg.reply_text("Tell me which domain(s) you would like to add to the whitelist.")


@run_async
@user_admin
@loggable
def rm_whitelist_url(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    user = update.effective_user # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    words = msg.text.split(None, 1)
    if len(words) > 1:
        text = words[1]
        to_unwhitelist = list(set(domain.strip() for domain in text.split("\n") if domain.strip()))
        successful = 0
        log = "<b>{}:</b>" \
          "\n#WHITELISTS" \
          "\n<b>• Action:</b> cleared" \
          "\n<b>• Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, 
                                                                  user.first_name))
        
        for domain in to_unwhitelist:
            success = sql.rm_url_from_whitelist(chat.id, domain)
            if success:
                successful += 1

        if len(to_unwhitelist) == 1:
            if successful:
                msg.reply_text("Removed <code>{}</code> from the whitelist!".format(html.escape(to_unwhitelist[0])),
                               parse_mode=ParseMode.HTML)
                log += "\n<b>• Domain:</b>\n"
                for domain in to_unwhitelist:
                    log += "   <code>{}</code>\n".format(domain)
            else:
                msg.reply_text("This isn't a whitelisted domain...!")

        elif successful == len(to_unwhitelist):
            msg.reply_text(
                "Removed <code>{}</code> domains from the whitelist.".format(
                    successful), parse_mode=ParseMode.HTML)
            num = 1
            log += "\n<b>• Domains:</b>\n"
            for domain in to_unwhitelist:
               log += "   {}. <code>{}</code>\n".format(num, domain)
               num += 1

        elif not successful:
            msg.reply_text(
                "None of these domains exist, so they weren't removed.".format(
                    successful, len(to_unwhitelist) - successful), parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "Removed <code>{}</code> domains from the whitelist. {} did not exist, "
                "so were not removed.".format(successful, len(to_unwhitelist) - successful),
                parse_mode=ParseMode.HTML)
        
        return log
    else:
        msg.reply_text("Tell me which domain(s) you would like to remove from the whitelist.")

@run_async
def get_whitelisted_urls(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    chat_name = chat.title or chat.first or chat.username
    all_whitelisted = sql.get_whitelisted_urls(chat.id)
    args = msg.text.split(" ")
    
    BASE_WHITELIST_STRING = "The following domain(s) are currently allowed in {}:\n".format(chat.title)
    filter_list = BASE_WHITELIST_STRING

    if len(args) > 0 and args[1].lower() == 'copy':
        for domain in all_whitelisted:
            filter_list += "<code>{}</code>\n".format(html.escape(domain))
    else:
        for domain in all_whitelisted:
            filter_list += " • <code>{}</code>\n".format(html.escape(domain))

    split_text = split_message(filter_list)
    for text in split_text:
        if text == BASE_WHITELIST_STRING:
            msg.reply_text("There are no whitelisted domains here!")
            return
        msg.reply_text(text.format(chat_name), parse_mode=ParseMode.HTML)

ADD_URL_WHITELIST_HANDLER = CustomCommandHandler(CMD_PREFIX, "addwhitelist", add_whitelist_url, filters=Filters.group)
RM_WHITELIST_URL_HANDLER = CustomCommandHandler(CMD_PREFIX, ["unwhitelist", "rmwhitelist"], rm_whitelist_url, filters=Filters.group)
GET_WHITELISTED_URLS = DisableAbleCommandHandler(CMD_PREFIX, "whitelist", get_whitelisted_urls, filters=Filters.group, admin_ok=True)


__mod_name__ = "Domain whitelists"


dispatcher.add_handler(ADD_URL_WHITELIST_HANDLER)
dispatcher.add_handler(RM_WHITELIST_URL_HANDLER)
dispatcher.add_handler(GET_WHITELISTED_URLS)

