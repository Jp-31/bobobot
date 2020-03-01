from telegram import Update, Bot
from telegram.ext import CallbackContext, CommandHandler, run_async

from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot import dispatcher, CMD_PREFIX, LOGGER

@run_async
def shout(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(" ")
    args.remove(args[0])
    msg = "```"
    text = " ".join(args)
    text
    result = []
    result.append(' '.join([s for s in text]))
    for pos, symbol in enumerate(text[1:]):
        result.append(symbol + ' ' + '  ' * pos + symbol)
    result = list("\n".join(result))
    try:
        result[0] = text[0]
        result = "".join(result)
        msg = "```\n" + result + "```"
    except:
        msg = "Send me a word to use for shout."
        LOGGER.log(2, "No argument given for shout.")
    
    return update.effective_message.reply_text(msg, parse_mode="MARKDOWN")
    
__help__ = """
 A little piece of fun wording! Give a loud shout out in the chatroom.
 
 i.e /shout HELP, {} replies with huge coded HELP letters within the square. 
 
 - /shout <keyword>: write anything you want to give loud shout.
    ```
    t e s t
    e e
    s   s
    t     t
    ```
""".format(dispatcher.bot.first_name)

__mod_name__ = "Shout"

SHOUT_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "shout", shout)

dispatcher.add_handler(SHOUT_HANDLER)
