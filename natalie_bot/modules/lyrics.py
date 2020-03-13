from PyLyrics import *
from telegram import Update, Bot
from telegram.ext import CallbackContext, CommandHandler, run_async
from typing import Optional, List

from natalie_bot.modules.disable import DisableAbleCommandHandler
from natalie_bot.modules.helper_funcs.chat_status import can_message
from natalie_bot import dispatcher, CMD_PREFIX, LOGGER

from requests import get

LYRICSINFO = "\n[Full Lyrics](http://lyrics.wikia.com/wiki/%s:%s)"

@run_async
@can_message
def lyrics(update: Update, context: CallbackContext):
    message = update.effective_message
    text = message.text[len('/lyrics '):]
    args = message.text.split(" ")
    args = args[1:]
    
    if args and len(args) != 0:
        song = " ".join(args).split("- ")
    else:
        song = ""
        LOGGER.log(2, "No arguments given.")

    reply_text = f'Looks up for lyrics'
    
    if len(song) == 2:
        song[0].strip()
        song[1].strip()
        try:
            lyrics = "\n".join(PyLyrics.getLyrics(
                song[0], song[1]).split("\n")[:20])
        except ValueError as e:
            return update.effective_message.reply_text("Song %s not found!" % song[1], failed=True)
        else:
            lyricstext = LYRICSINFO % (song[0].replace(
                " ", "_"), song[1].replace(" ", "_"))
            return update.effective_message.reply_text(lyrics + lyricstext, parse_mode="MARKDOWN")
    else:
        return update.effective_message.reply_text("Invalid args- try Artist - Title!", failed=True)


__help__ = """
Do you simply want to find the lyrics of your favourite songs? This command grabs you chunk of \
paragraphs for lyrics.

 - /lyrics <keyword> Find your favourite songs' lyrics

An example of using lyrics:
`/lyrics Ariana Grande - God is a woman`; this sends you the lyrics.

`/lyrics Artist - Song title`.
"""

__mod_name__ = "Lyrics"

LYRICS_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "lyrics", lyrics)

dispatcher.add_handler(LYRICS_HANDLER)
