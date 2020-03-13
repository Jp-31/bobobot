import threading

from sqlalchemy import Column, Integer, UnicodeText

from natalie_bot.modules.sql import SESSION, BASE


class UserInfo(BASE):
    __tablename__ = "userinfo"
    user_id = Column(Integer, primary_key=True)
    info = Column(UnicodeText)
    nick_n = Column(UnicodeText)

    def __init__(self, user_id, info, nick_n):
        self.user_id = user_id
        self.info = info
        self.nick_n = nick_n

    def __repr__(self):
        return "<User info %d>" % self.user_id


class UserBio(BASE):
    __tablename__ = "userbio"
    user_id = Column(Integer, primary_key=True)
    bio = Column(UnicodeText)

    def __init__(self, user_id, bio):
        self.user_id = user_id
        self.bio = bio

    def __repr__(self):
        return "<User info %d>" % self.user_id


UserInfo.__table__.create(checkfirst=True)
UserBio.__table__.create(checkfirst=True)

INSERTION_LOCK = threading.RLock()

def get_user_nick(user_id):
    userinfo = SESSION.query(UserInfo).get(user_id)
    SESSION.close()
    if userinfo:
        return userinfo.nick_n
    return None


def set_user_nick(user_id, nick_n):
    with INSERTION_LOCK:
        usernick = SESSION.query(UserInfo).get(user_id)
        if usernick:
            usernick.nick_n = nick_n
        else:
            usernick = UserInfo(user_id, nick_n)
        SESSION.add(usernick)
        SESSION.commit()

def get_user_me_info(user_id):
    userinfo = SESSION.query(UserInfo).get(user_id)
    SESSION.close()
    if userinfo:
        return userinfo.info
    return None


def set_user_me_info(user_id, info):
    with INSERTION_LOCK:
        userinfo = SESSION.query(UserInfo).get(user_id)
        if userinfo:
            userinfo.info = info
        else:
            userinfo = UserInfo(user_id, info)
        SESSION.add(userinfo)
        SESSION.commit()


def get_user_bio(user_id):
    userbio = SESSION.query(UserBio).get(user_id)
    SESSION.close()
    if userbio:
        return userbio.bio
    return None


def set_user_bio(user_id, bio):
    with INSERTION_LOCK:
        userbio = SESSION.query(UserBio).get(user_id)
        if userbio:
            userbio.bio = bio
        else:
            userbio = UserBio(user_id, bio)

        SESSION.add(userbio)
        SESSION.commit()


def clear_user_info(user_id):
    with INSERTION_LOCK:
        curr = SESSION.query(UserInfo).get(user_id)
        if curr:
            SESSION.delete(curr)
            SESSION.commit()
            return True

        SESSION.close()
    return False


def clear_user_bio(user_id):
    with INSERTION_LOCK:
        curr = SESSION.query(UserBio).get(user_id)
        if curr:
            SESSION.delete(curr)
            SESSION.commit()
            return True

        SESSION.close()
    return False
