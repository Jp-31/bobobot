import threading

from sqlalchemy import Column, UnicodeText, Integer, String, Boolean

from natalie_bot.modules.sql import BASE, SESSION


class GloballyBannedUsers(BASE):
    __tablename__ = "gbans"
    user_id = Column(Integer, primary_key=True)
    name = Column(UnicodeText, nullable=False)
    reason = Column(UnicodeText)

    def __init__(self, user_id, name, reason=None):
        self.user_id = user_id
        self.name = name
        self.reason = reason

    def __repr__(self):
        return "<GBanned User {} ({})>".format(self.name, self.user_id)

    def to_dict(self):
        return {"user_id": self.user_id,
                "name": self.name,
                "reason": self.reason}

class SpamWatchUsers(BASE):
    __tablename__ = "spamwatch"
    user_id = Column(Integer, primary_key=True)
    name = Column(UnicodeText, nullable=False)

    def __init__(self, user_id, name):
        self.user_id = user_id
        self.name = name

    def __repr__(self):
        return "<SpamWatch User whitelisted {} ({})>".format(self.name, self.user_id)

    def to_dict(self):
        return {"user_id": self.user_id,
                "name": self.name}

class GbanSettings(BASE):
    __tablename__ = "gban_settings"
    chat_id = Column(String(14), primary_key=True)
    setting = Column(Boolean, default=True, nullable=False)
    gban_alert = Column(Boolean, default=True, nullable=False)
    spamwatch = Column(Boolean, default=True, nullable=False)

    def __init__(self, chat_id, enabled, gban_alert=True, spamwatch=True):
        self.chat_id = str(chat_id)
        self.setting = enabled
        self.gban_alert = gban_alert
        self.spamwatch = spamwatch

    def __repr__(self):
        return "<Gban setting {} ({})>".format(self.chat_id, self.setting)
        return "<Gban alert {} ({})>".format(self.chat_id, self.gban_alert)
        return "<SpamWatch setting {} ({})>".format(self.chat_id, self.spamwatch)



GloballyBannedUsers.__table__.create(checkfirst=True)
SpamWatchUsers.__table__.create(checkfirst=True)
GbanSettings.__table__.create(checkfirst=True)

GBANNED_USERS_LOCK = threading.RLock()
SPAMWATCH_WHITELIST = threading.RLock()
GBAN_SETTING_LOCK = threading.RLock()
GBANNED_LIST = set()
GBANSTAT_LIST = set()
GBANALERT_LIST = set()
SPAMWATCH_USERS_LIST = set()
SPAMWATCH_LIST = set()


def gban_user(user_id, name, reason=None):
    with GBANNED_USERS_LOCK:
        user = SESSION.query(GloballyBannedUsers).get(user_id)
        if not user:
            user = GloballyBannedUsers(user_id, name, reason)
        else:
            user.name = name
            user.reason = reason

        SESSION.merge(user)
        SESSION.commit()
        __load_gbanned_userid_list()


def update_gban_reason(user_id, name, reason=None):
    with GBANNED_USERS_LOCK:
        user = SESSION.query(GloballyBannedUsers).get(user_id)
        if not user:
            return None
        old_reason = user.reason
        user.name = name
        user.reason = reason

        SESSION.merge(user)
        SESSION.commit()
        return old_reason


def ungban_user(user_id):
    with GBANNED_USERS_LOCK:
        user = SESSION.query(GloballyBannedUsers).get(user_id)
        if user:
            SESSION.delete(user)

        SESSION.commit()
        __load_gbanned_userid_list()


def is_user_gbanned(user_id):
    return user_id in GBANNED_LIST


def get_gbanned_user(user_id):
    try:
        return SESSION.query(GloballyBannedUsers).get(user_id)
    finally:
        SESSION.close()

def get_gban_reason(user_id):
    with GBANNED_USERS_LOCK:
        reason =  SESSION.query(GloballyBannedUsers).get(user_id)
        if not reason:
            SESSION.close()
            return None
        SESSION.close()
        return reason.reason


def get_gban_list():
    try:
        return [x.to_dict() for x in SESSION.query(GloballyBannedUsers).all()]
    finally:
        SESSION.close()

def enable_alert(chat_id):
    with GBAN_SETTING_LOCK:
        loud = SESSION.query(GbanSettings).get(str(chat_id))
        if not loud:
            loud = GbanSettings(chat_id, True)

        loud.gban_alert = True
        SESSION.add(loud)
        SESSION.commit()
        if str(chat_id) in GBANALERT_LIST:
            GBANALERT_LIST.remove(str(chat_id))


def disable_alert(chat_id):
    with GBAN_SETTING_LOCK:
        quiet = SESSION.query(GbanSettings).get(str(chat_id))
        if not quiet:
            quiet = GbanSettings(chat_id, False)

        quiet.gban_alert = False
        SESSION.add(quiet)
        SESSION.commit()
        GBANALERT_LIST.add(str(chat_id))
        
def get_gban_alert(chat_id):
    with GBAN_SETTING_LOCK:
        gban_alert =  SESSION.query(GbanSettings).get(str(chat_id))
        if not gban_alert:
            SESSION.close()
            return None
        SESSION.close()
        return gban_alert.gban_alert
        

def enable_gbans(chat_id):
    with GBAN_SETTING_LOCK:
        chat = SESSION.query(GbanSettings).get(str(chat_id))
        if not chat:
            chat = GbanSettings(chat_id, True)

        chat.setting = True
        SESSION.add(chat)
        SESSION.commit()
        if str(chat_id) in GBANSTAT_LIST:
            GBANSTAT_LIST.remove(str(chat_id))


def disable_gbans(chat_id):
    with GBAN_SETTING_LOCK:
        chat = SESSION.query(GbanSettings).get(str(chat_id))
        if not chat:
            chat = GbanSettings(chat_id, False)

        chat.setting = False
        SESSION.add(chat)
        SESSION.commit()
        GBANSTAT_LIST.add(str(chat_id))

def enable_spamw(chat_id):
    with GBAN_SETTING_LOCK:
        chat = SESSION.query(GbanSettings).get(str(chat_id))
        if not chat:
            chat = GbanSettings(chat_id, True)

        chat.spamwatch = True
        SESSION.add(chat)
        SESSION.commit()
        if str(chat_id) in SPAMWATCH_LIST:
            SPAMWATCH_LIST.remove(str(chat_id))


def disable_spamw(chat_id):
    with GBAN_SETTING_LOCK:
        chat = SESSION.query(GbanSettings).get(str(chat_id))
        if not chat:
            chat = GbanSettings(chat_id, False)

        chat.spamwatch = False
        SESSION.add(chat)
        SESSION.commit()
        SPAMWATCH_LIST.add(str(chat_id))

def spam_whitelist(user_id, name):
    with SPAMWATCH_WHITELIST:
        user = SESSION.query(SpamWatchUsers).get(user_id)
        if not user:
            user = SpamWatchUsers(user_id, name)
        else:
            user.name = name

        SESSION.merge(user)
        SESSION.commit()
        __load_spamwatch_userid_list()

def spam_unwhitelist(user_id):
    with SPAMWATCH_WHITELIST:
        user = SESSION.query(SpamWatchUsers).get(user_id)
        if user:
            SESSION.delete(user)

        SESSION.commit()
        __load_spamwatch_userid_list()

def whitelist_users(user_id):
    try:
        return SESSION.query(SpamWatchUsers).get(user_id)
    finally:
        SESSION.close()

def spamwatch_whitelisted(user_id):
    return str(user_id) not in SPAMWATCH_USERS_LIST

def get_spamwatch_list():
    try:
        return [x.to_dict() for x in SESSION.query(SpamWatchUsers).all()]
    finally:
        SESSION.close()

def does_chat_gban(chat_id):
    return str(chat_id) not in GBANSTAT_LIST

def does_chat_alert(chat_id):
    return str(chat_id) not in GBANALERT_LIST

def does_chat_spamwatch(chat_id):
    return str(chat_id) not in SPAMWATCH_LIST

def num_gbanned_users():
    return len(GBANNED_LIST)


def __load_gbanned_userid_list():
    global GBANNED_LIST
    try:
        GBANNED_LIST = {x.user_id for x in SESSION.query(GloballyBannedUsers).all()}
    finally:
        SESSION.close()

def __load_spamwatch_userid_list():
    global SPAMWATCH_USERS_LIST
    try:
        SPAMWATCH_USERS_LIST = {x.user_id for x in SESSION.query(SpamWatchUsers).all()}
    finally:
        SESSION.close()


def __load_gban_stat_list():
    global GBANSTAT_LIST
    try:
        GBANSTAT_LIST = {x.chat_id for x in SESSION.query(GbanSettings).all() if not x.setting}
    finally:
        SESSION.close()

def __load_gban_alert_list():
    global GBANALERT_LIST
    try:
        GBANALERT_LIST = {x.chat_id for x in SESSION.query(GbanSettings).all() if not x.gban_alert}
    finally:
        SESSION.close()

def __load_spamwatch_list():
    global SPAMWATCH_LIST
    try:
        SPAMWATCH_LIST = {x.chat_id for x in SESSION.query(
            GbanSettings).all() if not x.spamwatch}
    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with GBAN_SETTING_LOCK:
        chat = SESSION.query(GbanSettings).get(str(old_chat_id))
        if chat:
            chat.chat_id = new_chat_id
            SESSION.add(chat)

        SESSION.commit()


# Create in memory userid to avoid disk access
__load_gbanned_userid_list()
__load_spamwatch_userid_list()
__load_gban_stat_list()
__load_gban_alert_list()
__load_spamwatch_list()
