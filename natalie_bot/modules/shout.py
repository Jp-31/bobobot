from telegram import Update, Bot
from telegram.ext import CallbackContext, CommandHandler, run_async

from natalie_bot.modules.disable import DisableAbleCommandHandler
from natalie_bot import dispatcher, CMD_PREFIX, LOGGER

@run_async
def shout(update: Update, context: CallbackContext):
    message = update.effective_message
    args = message.text.split(" ")
    args.remove(args[0])
    msg = "```"
    text = " "
    if len(args) == 0 and not message.reply_to_message:
        message.reply_text("Give me an args to shout or reply to a text!")
        return

    if not args and message.reply_to_message and message.reply_to_message.sticker == (False or None):
        args = message.reply_to_message.text.split(" ")
        text = " ".join(args)
    else:
        text = " ".join(args)

    if len(text) > 40:
        message.reply_text("Text is longer than 40 characters.")
    else:
        result = []
        result.append(' '.join([s for s in text]))
        for pos, symbol in enumerate(text[1:]):
            result.append(symbol + ' ' + '  ' * pos + symbol)
        result = list("\n".join(result))
        try:
            result[0] = text[0]
            result = "".join(result)
            msg = "```\n" + result + "```"
            return message.reply_text(msg, parse_mode="MARKDOWN")
        except:
            LOGGER.log(2, "No argument given for shout or not enough permissions.")
    
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
