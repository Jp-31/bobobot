import threading

from sqlalchemy import Column, UnicodeText, Integer, String, Boolean

from natalie_bot.modules.sql import BASE, SESSION


class GloballyMutedUsers(BASE):
    __tablename__ = "gmutes"
    user_id = Column(Integer, primary_key=True)
    name = Column(UnicodeText, nullable=False)
    reason = Column(UnicodeText)

    def __init__(self, user_id, name, reason=None):
        self.user_id = user_id
        self.name = name
        self.reason = reason

    def __repr__(self):
        return "<GMuted User {} ({})>".format(self.name, self.user_id)

    def to_dict(self):
        return {"user_id": self.user_id,
                "name": self.name,
                "reason": self.reason}


class GmuteSettings(BASE):
    __tablename__ = "gmute_settings"
    chat_id = Column(String(14), primary_key=True)
    setting = Column(Boolean, default=True, nullable=False)
    gmute_alert = Column(Boolean, default=True, nullable=False)

    def __init__(self, chat_id, enabled, gmute_alert=True):
        self.chat_id = str(chat_id)
        self.setting = enabled
        self.gmute_alert = gmute_alert

    def __repr__(self):
        return "<Gmute setting {} ({})>".format(self.chat_id, self.setting)
        return "<Gmute alert {} ({})>".format(self.chat_id, self.gmute_alert)


GloballyMutedUsers.__table__.create(checkfirst=True)
GmuteSettings.__table__.create(checkfirst=True)

GMUTED_USERS_LOCK = threading.RLock()
GMUTE_SETTING_LOCK = threading.RLock()
GMUTED_LIST = set()
GMUTESTAT_LIST = set()
GMUTEALERT_LIST = set()


def gmute_user(user_id, name, reason=None):
    with GMUTED_USERS_LOCK:
        user = SESSION.query(GloballyMutedUsers).get(user_id)
        if not user:
            user = GloballyMutedUsers(user_id, name, reason)
        else:
            user.name = name
            user.reason = reason

        SESSION.merge(user)
        SESSION.commit()
        __load_gmuted_userid_list()


def update_gmute_reason(user_id, name, reason=None):
    with GMUTED_USERS_LOCK:
        user = SESSION.query(GloballyMutedUsers).get(user_id)
        if not user:
            return None
        old_reason = user.reason
        user.name = name
        user.reason = reason

        SESSION.merge(user)
        SESSION.commit()
        return old_reason


def ungmute_user(user_id):
    with GMUTED_USERS_LOCK:
        user = SESSION.query(GloballyMutedUsers).get(user_id)
        if user:
            SESSION.delete(user)

        SESSION.commit()
        __load_gmuted_userid_list()


def is_user_gmuted(user_id):
    return user_id in GMUTED_LIST


def get_gmuted_user(user_id):
    try:
        return SESSION.query(GloballyMutedUsers).get(user_id)
    finally:
        SESSION.close()

def get_gmute_reason(user_id):
    with GMUTED_USERS_LOCK:
        reason =  SESSION.query(GloballyMutedUsers).get(user_id)
        if not reason:
            SESSION.close()
            return None
        SESSION.close()
        return reason.reason


def get_gmute_list():
    try:
        return [x.to_dict() for x in SESSION.query(GloballyMutedUsers).all()]
    finally:
        SESSION.close()

def enable_alert(chat_id):
    with GMUTE_SETTING_LOCK:
        loud = SESSION.query(GmuteSettings).get(str(chat_id))
        if not loud:
            loud = GmuteSettings(chat_id, True)

        loud.gmute_alert = True
        SESSION.add(loud)
        SESSION.commit()
        if str(chat_id) in GMUTEALERT_LIST:
            GMUTEALERT_LIST.remove(str(chat_id))


def disable_alert(chat_id):
    with GMUTE_SETTING_LOCK:
        quiet = SESSION.query(GmuteSettings).get(str(chat_id))
        if not quiet:
            quiet = GmuteSettings(chat_id, False)

        quiet.gmute_alert = False
        SESSION.add(quiet)
        SESSION.commit()
        GMUTEALERT_LIST.add(str(chat_id))
        
def get_gmute_alert(chat_id):
    with GMUTE_SETTING_LOCK:
        gmute_alert =  SESSION.query(GmuteSettings).get(str(chat_id))
        if not gmute_alert:
            SESSION.close()
            return None
        SESSION.close()
        return gmute_alert.gmute_alert
        

def enable_gmutes(chat_id):
    with GMUTE_SETTING_LOCK:
        chat = SESSION.query(GmuteSettings).get(str(chat_id))
        if not chat:
            chat = GmuteSettings(chat_id, True)

        chat.setting = True
        SESSION.add(chat)
        SESSION.commit()
        if str(chat_id) in GMUTESTAT_LIST:
            GMUTESTAT_LIST.remove(str(chat_id))


def disable_gmutes(chat_id):
    with GMUTE_SETTING_LOCK:
        chat = SESSION.query(GmuteSettings).get(str(chat_id))
        if not chat:
            chat = GmuteSettings(chat_id, False)

        chat.setting = False
        SESSION.add(chat)
        SESSION.commit()
        GMUTESTAT_LIST.add(str(chat_id))

def does_chat_gmute(chat_id):
    return str(chat_id) not in GMUTESTAT_LIST

def does_chat_alert(chat_id):
    return str(chat_id) not in GMUTEALERT_LIST

def num_gmuted_users():
    return len(GMUTED_LIST)


def __load_gmuted_userid_list():
    global GMUTED_LIST
    try:
        GMUTED_LIST = {x.user_id for x in SESSION.query(GloballyMutedUsers).all()}
    finally:
        SESSION.close()


def __load_gmute_stat_list():
    global GMUTESTAT_LIST
    try:
        GMUTESTAT_LIST = {x.chat_id for x in SESSION.query(GmuteSettings).all() if not x.setting}
    finally:
        SESSION.close()

def __load_gmute_alert_list():
    global GMUTEALERT_LIST
    try:
        GMUTEALERT_LIST = {x.chat_id for x in SESSION.query(GmuteSettings).all() if not x.gmute_alert}
    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with GMUTE_SETTING_LOCK:
        chat = SESSION.query(GmuteSettings).get(str(old_chat_id))
        if chat:
            chat.chat_id = new_chat_id
            SESSION.add(chat)

        SESSION.commit()


# Create in memory userid to avoid disk access
__load_gmuted_userid_list()
__load_gmute_stat_list()
__load_gmute_alert_list()
