from telegram import Update, Bot
from telegram.ext import CallbackContext, CommandHandler, run_async

from natalie_bot.modules.disable import DisableAbleCommandHandler
from natalie_bot import dispatcher, CMD_PREFIX

from requests import get

@run_async
def ud(update: Update, context: CallbackContext):
  message = update.effective_message
  text = message.text[len('/ud '):]
  results = get(f'http://api.urbandictionary.com/v0/define?term={text}').json()
  reply_text = f'Word: {text}\nDefinition: {results["list"][0]["definition"]}'
  message.reply_text(reply_text)

__help__ = """
Urban Dictionary is made for fun; Urban Dictionary is a crowdsourced online dictionary for slang words and phrases. \
Search for any definition of words. {} sends you results of top most voted definition from Urban Dictionary.

 - /ud <keyword>: search for dictionary.
 
""".format(dispatcher.bot.first_name)

__mod_name__ = "Urban dictionary"

ud_handle = DisableAbleCommandHandler(CMD_PREFIX, "ud", ud)

dispatcher.add_handler(ud_handle)
