import html, time
import json
import random
from datetime import datetime
from typing import Optional, List
from emoji import UNICODE_EMOJI
import requests


import natalie_bot.modules.sql.userinfo_sql as sql
from telegram import Message, Chat, Update, Bot, MessageEntity, MAX_MESSAGE_LENGTH
from googletrans import Translator, LANGUAGES
from telegram.error import BadRequest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, TelegramError
from telegram.ext import CommandHandler, run_async, Filters, CallbackContext
from telegram.utils.helpers import escape_markdown, mention_html

from natalie_bot import dispatcher, OWNER_ID, iSUDO_USERS, SUDO_USERS, SUPPORT_USERS, SUPER_ADMINS, WHITELIST_USERS, BAN_STICKER, CMD_PREFIX
from natalie_bot.__main__ import GDPR
from natalie_bot.__main__ import STATS, USER_INFO
from natalie_bot.modules.disable import DisableAbleCommandHandler, DisableAbleRegexHandler
from natalie_bot.modules.helper_funcs.chat_status import can_message
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler
from natalie_bot.modules.helper_funcs.extraction import extract_user
from natalie_bot.modules.helper_funcs.filters import CustomFilters
from natalie_bot.modules.helper_funcs.handlers import CustomCommandHandler


RUN_STRINGS = (
    "Where do you think you're going?",
    "Huh? what? did they get away?",
    "ZZzzZZzz... Huh? what? oh, just them again, nevermind.",
    "Get back here!",
    "Not so fast...",
    "Look out for the wall!",
    "Don't leave me alone with them!!",
    "You run, you die.",
    "Energy drinks makes you run faster!",
    "Stop walking and start to run",
    "Jokes on you, I'm everywhere",
    "You're gonna regret that...",
    "You could also try /kickme, I hear that's fun.",
    "Go bother someone else, no-one here cares.",
    "You can run, but you can't hide.",
    "Is that all you've got?",
    "I'm behind you...",
    "You've got company!",
    "We can do this the easy way, or the hard way.",
    "You just don't get it, do you?",
    "Yeah, you better run!",
    "Please, remind me how much I care?",
    "I'd run faster if I were you.",
    "That's definitely the droid we're looking for.",
    "May the odds be ever in your favour.",
    "Famous last words.",
    "If you disappear, don't call for help...",
    "Run for your life!",
    "And they disappeared forever, never to be seen again.",
    "\"Oh, look at me! I'm so cool, I can run from a bot!\" - this person",
    "Yeah yeah, just tap /kickme already.",
    "Here, take this ring and head to Mordor while you're at it.",
    "Legend has it, they're still running...",
    "Unlike Harry Potter, your parents can't protect you from me.",
    "Fear leads to anger. Anger leads to hate. Hate leads to suffering. If you keep running in fear, you might "
    "be the next Vader.",
    "Multiple calculations later, I have decided my interest in your shenanigans is exactly 0.",
    "Legend has it, they're still running.",
    "Keep it up, not sure we want you here anyway.",
    "You're a wiza- Oh. Wait. You're not Harry, keep moving.",
    "NO RUNNING IN THE HALLWAYS!",
    "Hasta la vista, baby.",
    "Run carelessly you might get tripped.",
    "You have done a wonderful job, Keep it up...",
    "I see an evil spirits here, Let's expel them!\n\n"
    "Exorcizamus te, omnis immunde spiritus, omni satanica potestas, omnis incursio infernalis adversarii," 
    " omnis legio, omnis congregatio et secta diabolica, in nomini et virtute Domini nostri Jesu Christi, eradicare "
    "et effugare a Dei Ecclesia, ab animabus ad imaginem Dei conditis ac pretioso divini Agni sanguini redemptis.",
    "Who let the dogs out?",
    "It's funny, because no one cares.",
    "That's cool, just hit on seppuku /banme already.",
    "Ah, what a waste. I liked that one.",
    "Frankly, my dear, I don't give a damn.",
    "My flowers brings all the girls to yard... So run faster!",
    "You can't HANDLE the truth!",
    "A long time ago, in a galaxy far far away... Someone would've cared about that. Not anymore though.",
    "Hey, look at them! They're running from the inevitable banhammer... Cute.",
    "Han shot first. So will I.",
    "What are you running after, a white rabbit?",
    "As The Doctor would say... RUN!",
)

RNUM_STRINGS = (
    "0  ",
    "1  ",
    "2  ",
    "3  ",
    "4  ",
    "5  ",
    "6  ",
    "7  ",
    "8  ",
    "9  ",
    "10 ",
    "11 ",
    "12 ",
    "13 ",
    "14 ",
    "15 ",
    "16 ",
    "17 ",
    "18 ",
    "19 ",
    "20 ",
    "21 ",
    "22 ",
    "23 ",
    "24 ",
    "25 ",
    "26 ",
    "27 ",
    "28 ",
    "29 ",
    "30 ",
    "31 ",
    "32 ",
    "33 ",
    "34 ",
    "35 ",
    "36 ",
    "37 ",
    "38 ",
    "39 ",
    "40 ",
    "41 ",
    "42 ",
    "43 ",
    "44 ",
    "45 ",
    "46 ",
    "47 ",
    "48 ",
    "49 ",
    "50 ",
    "51 ",
    "52 ",
    "53 ",
    "54 ",
    "55 ",
    "56 ",
    "57 ",
    "58 ",
    "59 ",
    "60 ",
    "61 ",
    "62 ",
    "63 ",
    "64 ",
    "65 ",
    "66 ",
    "67 ",
    "68 ",
    "69 ",
    "70 ",
    "71 ",
    "72 ",
    "73 ",
    "74 ",
    "75 ",
    "76 ",
    "77 ",
    "78 ",
    "79 ",
    "80 ",
    "81 ",
    "82 ",
    "83 ",
    "84 ",
    "85 ",
    "86 ",
    "87 ",
    "88 ",
    "89 ",
    "90 ",
    "91 ",
    "92 ",
    "93 ",
    "94 ",
    "95 ",
    "96 ",
    "97 ",
    "98 ",
    "99 ",
    "100",
)

SLAP_TEMPLATES = (
    "{user1} {hits} {user2} with a {item}.",
    "{user1} {hits} {user2} in the face with a {item}.",
    "{user1} {hits} {user2} around a bit with a {item}.",
    "{user1} {throws} a {item} at {user2}.",
    "{user1} grabs a {item} and {throws} it at {user2}'s face.",
    "{user1} launches a {item} in {user2}'s general direction.",
    "{user1} starts slapping {user2} silly with a {item}.",
    "{user1} pins {user2} down and repeatedly {hits} them with a {item}.",
    "{user1} grabs up a {item} and {hits} {user2} with it.",
    "{user1} brutally beats up {user2} with {item}.",
    "{user1} ties {user2} to a chair and {throws} a {item} at them.",
    "{user1} {hits} {user2} with a glue filled hands.",
    "{user1} slams the metal door at {user2}.",
    "{user1} thundersmacks {user2} with lightning bolt.",
    "{user1} gave a friendly push to help {user2} learn to swim in a wild ocean.",
    "{user1} {throws} {user2} into the ocean.",
    "{user1} {throws} {user2} into ice filled water.",
    "{user1} yeeted {user2}'s existence.",
    "{user1} {throws} {user2} into shark infested water.",
)

PUNCH_TEMPLATES = (
    "{user1} {punches} {user2} with a {item}.",
    "{user1} {punches} {user2} in the face with a {item}.",
    "{user1} punched {user2} into lava.",
    "{user1} {punches} {user2} repeatedly in the face.",
    "{user1} {punches} {user2} around a bit with a {item}.",
    "{user1} {punches} {user2} on their face. 👊",
)

HUG_TEMPLATES = (
    "{user1} {hug} {user2}.",
    "{user1} {hug} {user2} warmly.",
    "{user1} {hug} {user2} with a love. 💘",
    "{user1} {hug} {user2} with kindness.",
)

KISS_TEMPLATES = (
    "{user1} {kiss} {user2} warmly.",
    "{user1} {kiss} {user2}.",
    "{user1} kissed {user2} gently.",
    "{user1} kissed {user2}.",
    "With {user1} dying breath, {user2} rushes over to give {user2} a last kiss.",
    "{user1} whispers love to {user2} and {kiss} her warmly.",
    "{user1} rushes over to {user2} and brings {user2} into a warm love hug.",
    "{user1} {kiss} {user2} into a deep sleep.",
    "{user1} {kiss} {user2} using {item}.",
)

ITEMS = (
    "cast iron skillet",
    "large trout",
    "baseball bat",
    "cricket bat",
    "wooden cane",
    "spatula",
    "nail",
    "pillow",
    "printer",
    "shovel",
    "CRT monitor",
    "spoon forks",
    "bag of dog food",
    "physics textbook",
    "toaster",
    "water balloon",
    "paper plane",
    "marble ball",
    "dirty diaper",
    "phone",
    "old radio",
    "gym ball",
    "shoe box",
    "detergent",
    "dart",
    "arrow",
    "toy insect",
    "bowling ball",
    "glass of water",
    "bucket of horse shit",
    "toolbox",
    "portrait of Richard Stallman",
    "television",
    "five ton truck",
    "roll of duct tape",
    "bottle of ketchup",
    "bottle of mayonnaise",
    "bottle of mustard",
    "tire",
    "pencil",
    "wooden board",
    "book",
    "laptop",
    "old television",
    "sack of rocks",
    "shopping cart",
    "keyboard",
    "lamp",
    "spiked mace",
    "rainbow trout",
    "rubber slipper",
    "rubber chicken",
    "spiked bat",
    "fire extinguisher",
    "heavy rock",
    "chunk of dirt",
    "rotten apple pie",
    "beehive",
    "piece of rotten meat",
    "bear",
    "ton of bricks",
)

THROW = (
    "throws",
    "flings",
    "chucks",
    "hurls",
)

HIT = (
    "hits",
    "whacks",
    "slaps",
    "smacks",
    "bashes",
)

PUNCH = (
    "punch",
    "punched",
    "smack",
)

HUG = (
    "hugs",
    "hugged",
    "kissed",
    "pinches",
)

KISS = (
    "french kiss",
    "kiss",
    "kissed",
    "tongue kiss",
    "tongue kissed",
    "bitten lips",
)

GREETING = (
    "Yes?",
    "Yo!",
    "Hiya!",
    "It’s nice to meet you",
    "Sup",
    "Hi",
    "What's up?",
)

GMAPS_LOC = "https://maps.googleapis.com/maps/api/geocode/json"
GMAPS_TIME = "https://maps.googleapis.com/maps/api/timezone/json"

@run_async
def greet(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(None, 1)
    if len(args) >= 2:
        reason = args[1]
    else:
        reason = ""

    update.effective_message.reply_text(random.choice(GREETING))

@run_async
@can_message
def runs(update: Update, context: CallbackContext):
    update.effective_message.reply_text(random.choice(RUN_STRINGS))

@run_async
def rnum(update: Update, context: CallbackContext):
    result = "Result is: "
    msg = update.effective_message
    msg.reply_text(result + random.choice(RNUM_STRINGS))

@run_async
def firstmsg(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat # type: Optional[Chat]
    
    try:
        context.bot.sendMessage(msg.chat.id, "First message of {}.".format(chat.title), reply_to_message_id=1)
    except BadRequest:
        return msg.reply_text("Seems like first message of {} was deleted.".format(chat.title))    


@run_async
@can_message
def slap(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    args= update.effective_message.text.split(" ")

    # reply to correct message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # get user who sent message
    if msg.from_user.username:
        curr_user = "@" + escape_markdown(msg.from_user.username)
    else:
        curr_user = "[{}](tg://user?id={})".format(msg.from_user.first_name, msg.from_user.id)

    user_id = extract_user(update.effective_message, args)
    if user_id:
        slapped_user = context.bot.get_chat(user_id)
        user1 = curr_user
        if slapped_user.username:
            user2 = "@" + escape_markdown(slapped_user.username)
        else:
            user2 = "[{}](tg://user?id={})".format(slapped_user.first_name,
                                                   slapped_user.id)

    # if no target found, bot targets the sender
    else:
        user1 = "[{}](tg://user?id={})".format(context.bot.first_name, context.bot.id)
        user2 = curr_user

    temp = random.choice(SLAP_TEMPLATES)
    item = random.choice(ITEMS)
    hit = random.choice(HIT)
    throw = random.choice(THROW)

    repl = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw)

    reply_text(repl, parse_mode=ParseMode.MARKDOWN)

@run_async
@can_message
def punch(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(" ")

    # reply to correct message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # get user who sent message
    if msg.from_user.username:
        curr_user = "@" + escape_markdown(msg.from_user.username)
    else:
        curr_user = "[{}](tg://user?id={})".format(msg.from_user.first_name, msg.from_user.id)

    user_id = extract_user(update.effective_message, args)
    if user_id:
        punched_user = context.bot.get_chat(user_id)
        user1 = curr_user
        if punched_user.username:
            user2 = "@" + escape_markdown(punched_user.username)
        else:
            user2 = "[{}](tg://user?id={})".format(punched_user.first_name,
                                                   punched_user.id)

    # if no target found, bot targets the sender
    else:
        user1 = "[{}](tg://user?id={})".format(context.bot.first_name, context.bot.id)
        user2 = curr_user

    temp = random.choice(PUNCH_TEMPLATES)
    item = random.choice(ITEMS)
    punch = random.choice(PUNCH)

    repl = temp.format(user1=user1, user2=user2, item=item, punches=punch)

    reply_text(repl, parse_mode=ParseMode.MARKDOWN)



@run_async
@can_message
def hug(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(" ")

    # reply to correct message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # get user who sent message
    if msg.from_user.username:
        curr_user = "@" + escape_markdown(msg.from_user.username)
    else:
        curr_user = "[{}](tg://user?id={})".format(msg.from_user.first_name, msg.from_user.id)

    user_id = extract_user(update.effective_message, args)
    if user_id:
        hugged_user = context.bot.get_chat(user_id)
        user1 = curr_user
        if hugged_user.username:
            user2 = "@" + escape_markdown(hugged_user.username)
        else:
            user2 = "[{}](tg://user?id={})".format(hugged_user.first_name,
                                                   hugged_user.id)

    # if no target found, bot targets the sender
    else:
        user1 = "Awwh! [{}](tg://user?id={})".format(context.bot.first_name, context.bot.id)
        user2 = curr_user

    temp = random.choice(HUG_TEMPLATES)
    hug = random.choice(HUG)

    repl = temp.format(user1=user1, user2=user2, hug=hug)

    reply_text(repl, parse_mode=ParseMode.MARKDOWN)

@run_async
@can_message
def kiss(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(" ")

    # reply to correct message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # get user who sent message
    if msg.from_user.username:
        curr_user = "@" + escape_markdown(msg.from_user.username)
    else:
        curr_user = "[{}](tg://user?id={})".format(msg.from_user.first_name, msg.from_user.id)

    user_id = extract_user(update.effective_message, args)
    if user_id:
        kissed_user = context.bot.get_chat(user_id)
        user1 = curr_user
        if kissed_user.username:
            user2 = "@" + escape_markdown(kissed_user.username)
        else:
            user2 = "[{}](tg://user?id={})".format(kissed_user.first_name,
                                                   kissed_user.id)

    # if no target found, bot targets the sender
    else:
        user1 = "Awwh! [{}](tg://user?id={})".format(context.bot.first_name, context.bot.id)
        user2 = curr_user

    temp = random.choice(KISS_TEMPLATES)
    kiss = random.choice(KISS)
    item = random.choice(ITEMS)

    repl = temp.format(user1=user1, user2=user2, item=item, kiss=kiss)

    reply_text(repl, parse_mode=ParseMode.MARKDOWN)
 


@run_async
def get_bot_ip(update: Update, context: CallbackContext):
    """ Sends the bot's IP address, so as to be able to ssh in if necessary.
        OWNER ONLY.
    """
    res = requests.get("http://ipinfo.io/ip")
    update.message.reply_text(res.text)


@run_async
def get_id(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(" ")
    user_id = extract_user(update.effective_message, args)
    if user_id:
        if update.effective_message.reply_to_message and update.effective_message.reply_to_message.forward_from:
            user1 = update.effective_message.reply_to_message.from_user
            user2 = update.effective_message.reply_to_message.forward_from
            update.effective_message.reply_text(
                "The original sender, {}, has an ID of `{}`.\nThe forwarder, {}, has an ID of `{}`.".format(
                    escape_markdown(user2.first_name),
                    user2.id,
                    escape_markdown(user1.first_name),
                    user1.id),
                parse_mode=ParseMode.MARKDOWN)
        else:
            user = context.bot.get_chat(user_id)
            update.effective_message.reply_text("{}'s id is `{}`.".format(escape_markdown(user.first_name), user.id),
                                                parse_mode=ParseMode.MARKDOWN)
    else:
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == "private":
            update.effective_message.reply_text("Your id is `{}`.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)

        else:
            update.effective_message.reply_text("This group's id is `{}`.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)


@run_async
def info(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    args = msg.text.split(" ")
    
    user_id = extract_user(update.effective_message, args)
    
    if user_id:
        nick = sql.get_user_nick(user_id)
    else:
        nick = sql.get_user_nick(user.id)

    if user_id:
        user = context.bot.get_chat(user_id)

    elif not msg.reply_to_message and len(args) <= 1:
        user = msg.from_user

    elif len(args) >= 2:
        if not msg.reply_to_message and (not args or (
                len(args) >= 1 and not args[1].startswith("@") and not args[1].isdigit() and not msg.parse_entities(
            [MessageEntity.TEXT_MENTION]))):
            msg.reply_text("I can't extract a user from this.")
            return

    else:
        return
    text = "<b>User info</b>:" \
           "\nID: <code>{}</code>" \
           "\nFirst Name: {}".format(user.id, html.escape(user.first_name))
    
    if user.last_name:
        text += "\nLast Name: {}".format(html.escape(user.last_name))
    
    if nick:
        text += "\nNickname: {}".format(html.escape(nick))

    if user.username:
        text += "\nUsername: @{}".format(html.escape(user.username))

    text += "\nPermanent user link: {}".format(mention_html(user.id, "link"))

    if user.id == OWNER_ID:
        text += "\n\nThis person is my creator! They have total power over me."

    else:
        if user.id in SUDO_USERS:
            text += "\nThis person is one of my sudo users! " \
                    "Nearly as powerful as my creator - so watch it."

        if user.id in iSUDO_USERS:
            text += "\nThe Chronics-Nothing but a g Thang " \
                    "\nIllmatic-N.Y State of Mind."

        
        else:
            if user.id in SUPPORT_USERS:
                text += "\nThis person is one of my support users! " \
                        "Not quite a sudo user, but can still gban you off the map."

            if user.id in SUPER_ADMINS:
                text += "\nThis person is one of my super admin users! " \
                        "Not quite a sudo user, but can help ban spammers off the chat."

            if user.id in WHITELIST_USERS:
                text += "\nThis person has been whitelisted! " \
                        "That means I'm not allowed to ban/kick them."

    for mod in USER_INFO:
        mod_info = mod.__user_info__(user.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def get_time(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(" ")
    args = args.remove(args[0])
    location = " ".join(args)
    if location.lower() == context.bot.first_name.lower():
        update.effective_message.reply_text("Its always banhammer time for me!")
        context.bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    res = requests.get(GMAPS_LOC, params=dict(address=location))

    if res.status_code == 200:
        loc = json.loads(res.text)
        if loc.get('status') == 'OK':
            lat = loc['results'][0]['geometry']['location']['lat']
            long = loc['results'][0]['geometry']['location']['lng']

            country = None
            city = None

            address_parts = loc['results'][0]['address_components']
            for part in address_parts:
                if 'country' in part['types']:
                    country = part.get('long_name')
                if 'administrative_area_level_1' in part['types'] and not city:
                    city = part.get('long_name')
                if 'locality' in part['types']:
                    city = part.get('long_name')

            if city and country:
                location = "{}, {}".format(city, country)
            elif country:
                location = country

            timenow = int(datetime.utcnow().timestamp())
            res = requests.get(GMAPS_TIME, params=dict(location="{},{}".format(lat, long), timestamp=timenow))
            if res.status_code == 200:
                offset = json.loads(res.text)['dstOffset']
                timestamp = json.loads(res.text)['rawOffset']
                time_there = datetime.fromtimestamp(timenow + timestamp + offset).strftime("%I:%M:%S %p on %A %d %B")
                update.message.reply_text("It's {} in {}".format(time_there, location))

@run_async
def msg_save(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat

    try:
        if msg.reply_to_message:
            success_pm = context.bot.forward_message(
                user.id, chat.id, msg.reply_to_message.message_id)
        else:
            success_pm = context.bot.forward_message(
                user.id, chat.id, msg.message_id)
    
    except TelegramError as e:
        pass

    saved = msg.reply_text("Successfully saved message!")
    msg.delete()
    try:
       time.sleep(3)
       saved.delete()
    
    except TelegramError as e:
        if e.message == "Peer_id_invalid":
               msg.reply_text("Contact me in PM first.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                   text="Start", url=f"t.me/{context.bot.username}")]]))
        return
    
    if success_pm:
       saved
    
    else:
       msg.reply_text("Failed to save message.")

@run_async
def set_nick(update: Update, context: CallbackContext):
    message = update.effective_message  # type: Optional[Message]
    user_id = message.from_user.id
    text = message.text
    nick_n = text.split(None, 1)  # use python's maxsplit to only remove the cmd, hence keeping newlines.
    if len(nick_n) == 2:
        if len(nick_n[1]) < MAX_MESSAGE_LENGTH // 4:
            sql.set_user_nick(user_id, nick_n[1])
            message.reply_text("Updated your nickname!")
        else:
            message.reply_text(
                "Your nickname needs to be under {} characters! You have {}.".format(MAX_MESSAGE_LENGTH // 4, len(nick_n[1])))

@run_async
def get_nick(update: Update, context: CallbackContext):
    message = update.effective_message  # type: Optional[Message]
    args = message.text.split(" ")
    user_id = extract_user(message, args)

    if user_id:
        user = context.bot.get_chat(user_id)
    else:
        user = message.from_user

    nick_txt = sql.get_user_nick(user.id)

    if nick_txt:
        update.effective_message.reply_text("*{}*'s nickname:\n{}".format(user.first_name, escape_markdown(nick_txt)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = message.reply_to_message.from_user.first_name
        update.effective_message.reply_text(username + " hasn't set nickname yet!")
    else:
        update.effective_message.reply_text("You haven't set a nickname for yourself!")

@run_async
def echo(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message
    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1])
    else:
        message.reply_text(args[1], quote=False)
    message.delete()

@run_async
def translator(update: Update, context: CallbackContext):

    msg = update.effective_message
    problem_lang_code = []
    for key in LANGUAGES:
        if "-" in key:
            problem_lang_code.append(key)
    try:
        if msg.reply_to_message and msg.reply_to_message.text:
            
            args = update.effective_message.text.split(None, 1)
            text = msg.reply_to_message.text
            message = update.effective_message
            dest_lang = None

            try:
                source_lang = args[1].split(None, 1)[0]
            except:
                source_lang = "en"
            
            if source_lang.count('-') == 2:
                for lang in problem_lang_code:
                    if lang in source_lang:
                        if source_lang.startswith(lang):
                            dest_lang = source_lang.rsplit("-", 1)[1]
                            source_lang = source_lang.rsplit("-", 1)[0]
                        else:
                            dest_lang = source_lang.split("-", 1)[1]
                            source_lang = source_lang.split("-", 1)[0]
            elif source_lang.count('-') == 1:
                for lang in problem_lang_code:
                    if lang in source_lang:
                        dest_lang = source_lang
                        source_lang = None
                        break
                if dest_lang == None:
                    dest_lang = source_lang.split("-")[1]
                    source_lang = source_lang.split("-")[0]
            else:
                dest_lang = source_lang
                source_lang = None

            exclude_list = UNICODE_EMOJI.keys()
            for emoji in exclude_list:
                if emoji in text:
                    text = text.replace(emoji, '')

            trl = Translator()
            if source_lang == None:
                detection = trl.detect(text)
                tekstr = trl.translate(text, dest=dest_lang)
                return message.reply_text("Translated from `{}` to `{}`:\n`{}`".format(detection.lang, 
                                                                                       dest_lang, tekstr.text), 
                                                                                       parse_mode=ParseMode.MARKDOWN)
            else:
                tekstr = trl.translate(text, dest=dest_lang, src=source_lang)
                message.reply_text("Translated from `{}` to `{}`:\n`{}`".format(source_lang, dest_lang, tekstr.text), 
                                                                                parse_mode=ParseMode.MARKDOWN)
        else:
            args = update.effective_message.text.split(None, 2)
            message = update.effective_message
            source_lang = args[1]
            text = args[2]
            exclude_list = UNICODE_EMOJI.keys()
            for emoji in exclude_list:
                if emoji in text:
                    text = text.replace(emoji, '')
            dest_lang = None
            temp_source_lang = source_lang
            if temp_source_lang.count('-') == 2:
                for lang in problem_lang_code:
                    if lang in temp_source_lang:
                        if temp_source_lang.startswith(lang):
                            dest_lang = temp_source_lang.rsplit("-", 1)[1]
                            source_lang = temp_source_lang.rsplit("-", 1)[0]
                        else:
                            dest_lang = temp_source_lang.split("-", 1)[1]
                            source_lang = temp_source_lang.split("-", 1)[0]
            elif temp_source_lang.count('-') == 1:
                for lang in problem_lang_code:
                    if lang in temp_source_lang:
                        dest_lang = None
                        break
                    else:
                        dest_lang = temp_source_lang.split("-")[1]
                        source_lang = temp_source_lang.split("-")[0]
            trl = Translator()
            if dest_lang == None:
                detection = trl.detect(text)
                tekstr = trl.translate(text, dest=source_lang)
                return message.reply_text("Translated from `{}` to `{}`:\n`{}`".format(detection.lang, 
                                                                                       source_lang, tekstr.text), 
                                                                                       parse_mode=ParseMode.MARKDOWN)
            else:
                tekstr = trl.translate(text, dest=dest_lang, src=source_lang)
                message.reply_text("Translated from `{}` to `{}`:\n`{}`".format(source_lang, dest_lang, 
                                                                                tekstr.text), 
                                                                                parse_mode=ParseMode.MARKDOWN)

    except IndexError:
        msg.reply_text("Reply to messages or write messages from other languages ​​for translating into the "
                       "intended language\n\nExample: `/tl en ar` to translate from English to Arabic\nOr "
                       "use: `/tl ar` for automatic detection and translating it into Arabic. "
                       "\nCheck the following [list of Language Codes](https://t.me/nataliesupport/130) for the list of "
                       "arguments codes in tranlator.", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    except ValueError:
        msg.reply_text("Language in args not found!")
    else:
        return

def ping(update: Update, context: CallbackContext):
    start_time = time.time()
    requests.get('https://api.telegram.org')
    end_time = time.time()
    ping_time = float(end_time - start_time)*1000
    update.effective_message.reply_text(" Ping speed was : {}ms".format(ping_time))
    
@run_async
def gdpr(update: Update, context: CallbackContext):
    update.effective_message.reply_text("Deleting identifiable data...")
    for mod in GDPR:
        mod.__gdpr__(update.effective_user.id)

    update.effective_message.reply_text("Your personal data has been deleted.\n\nNote that this will not unban "
                                        "you from any chats, as that is telegram data, not bot's data. "
                                        "Flooding, warns, and gbans are also preserved, as of "
                                        "[this](https://ico.org.uk/for-organisations/guide-to-the-general-data-protection-regulation-gdpr/individual-rights/right-to-erasure/), "
                                        "which clearly states that the right to erasure does not apply "
                                        "\"for the performance of a task carried out in the public interest\", as is "
                                        "the case for the aforementioned pieces of data.",
                                        parse_mode=ParseMode.MARKDOWN)


MARKDOWN_HELP = """
Markdown is a very powerful formatting tool supported by telegram. {} has some enhancements, to make sure that \
saved messages are correctly parsed, and to allow you to create buttons.

- <code>_italic_</code>: wrapping text with '_' will produce italic text
- <code>*bold*</code>: wrapping text with '*' will produce bold text
- <code>`code`</code>: wrapping text with '`' will produce monospaced text, also known as 'code'
- <code>[sometext](someURL)</code>: this will create a link - the message will just show <code>sometext</code>, \
and tapping on it will open the page at <code>someURL</code>.
EG: <code>[test](example.com)</code>

- <code>[buttontext](buttonurl:someURL)</code>: this is a special enhancement to allow users to have telegram \
buttons in their markdown. <code>buttontext</code> will be what is displayed on the button, and <code>someurl</code> \
will be the url which is opened.
EG: <code>[This is a button](buttonurl:example.com)</code>

If you want multiple buttons on the same line, use :same, as such:
<code>[one](buttonurl://example.com)
[two](buttonurl://google.com:same)</code>
This will create two buttons on a single line, instead of one button per line.

Keep in mind that your message <b>MUST</b> contain some text other than just a button!
""".format(dispatcher.bot.first_name)


@run_async
def markdown_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text("Try forwarding the following message to me, and you'll see!")
    update.effective_message.reply_text("/save test This is a markdown test. _italics_, *bold*, `code`, "
                                        "[URL](example.com) [button](buttonurl:github.com) "
                                        "[button2](buttonurl://google.com:same)")


@run_async
def stats(update: Update, context: CallbackContext):
    update.effective_message.reply_text("Current stats:\n" + "\n".join([mod.__stats__() for mod in STATS]))


# /ip is for private use
__help__ = """
An "odds and ends" module for small, simple commands which don't really fit anywhere

 - /id: get the current group id. If used by replying to a message, gets that user's id.
 - /runs: reply a random string from an array of replies.
 - /rnum: generate random numbers from 0-100.
 - /tl: use as reply or translate using text from any language to English.
 - /first: scrolls to first message of chat.
 - /s: saves the message you reply to your chat with the bot.
 - /slap: slap a user, or get slapped if not a reply.
 - /hug: hug a user, or get hugged if not a reply.
 - /kiss: kiss a user, or get kissed if not a reply.
 - /punch: punch a user, or get punched if not a reply.
 - /info: get information about a user.
 - Hi {}: responds to user (to disable greet `/disable botgreet`; to enable greet `/enable botgreet`)
 - /markdownhelp: quick summary of how markdown works in telegram - can only be called in private chats.
""".format(dispatcher.bot.first_name)
__mod_name__ = "Misc"

ID_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "id", get_id)
IP_HANDLER = CustomCommandHandler(CMD_PREFIX, "ip", get_bot_ip, filters=Filters.chat(OWNER_ID))

# TIME_HANDLER = CommandHandler("time", get_time, pass_args=True)

RUNS_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "runs", runs)
FIRST_MESSAGE_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, ["first_message", "first"], firstmsg)
S_HANDLER = CustomCommandHandler(CMD_PREFIX, "s", msg_save, filters=Filters.group)
RNUM_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "rnum", rnum)
#TIME_HANDLER = CommandHandler("time", get_time)
SLAP_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "slap", slap)
PUNCH_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "punch", punch)
TRANSLATOR_HANDLER = DisableAbleCommandHandler(CMD_PREFIX,"tl", translator)
HUG_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "hug", hug)
KISS_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "kiss", kiss)
INFO_HANDLER = DisableAbleCommandHandler(CMD_PREFIX,"info", info)
PING_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "ping", ping)
GREETINGS_REGEX_HANDLER = DisableAbleRegexHandler("(?i)hi {}".format(dispatcher.bot.first_name),
                                                                     greet, friendly="botgreet")
ECHO_HANDLER = CustomCommandHandler(CMD_PREFIX, "echo", echo, filters=Filters.user(OWNER_ID) | CustomFilters.isudo_filter)
MD_HELP_HANDLER = CustomCommandHandler(CMD_PREFIX, "markdownhelp", markdown_help, filters=Filters.private)
SET_NICK_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "setnick", set_nick)
GET_NICK_HANDLER = DisableAbleCommandHandler(CMD_PREFIX, "nick", get_nick)

STATS_HANDLER = CustomCommandHandler(CMD_PREFIX, "stats", stats, filters=CustomFilters.sudo_filter)
#GDPR_HANDLER = CommandHandler("gdpr", gdpr, filters=Filters.private)

dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(PING_HANDLER)
dispatcher.add_handler(IP_HANDLER)
# dispatcher.add_handler(TIME_HANDLER)
dispatcher.add_handler(GREETINGS_REGEX_HANDLER)
dispatcher.add_handler(RUNS_HANDLER)
dispatcher.add_handler(FIRST_MESSAGE_HANDLER)
dispatcher.add_handler(S_HANDLER)
dispatcher.add_handler(RNUM_HANDLER)
dispatcher.add_handler(SLAP_HANDLER)
dispatcher.add_handler(PUNCH_HANDLER)
dispatcher.add_handler(HUG_HANDLER)
dispatcher.add_handler(KISS_HANDLER)
dispatcher.add_handler(TRANSLATOR_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)
dispatcher.add_handler(SET_NICK_HANDLER)
dispatcher.add_handler(GET_NICK_HANDLER)
# dispatcher.add_handler(GDPR_HANDLER)
