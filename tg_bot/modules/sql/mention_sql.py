import threading
import array as arr
import datetime

from sqlalchemy import Integer, Column, String, UnicodeText, func, distinct, Boolean, DateTime
from sqlalchemy.dialects import postgresql

from tg_bot.modules.sql import SESSION, BASE


class Mention(BASE):
    __tablename__ = "mention"

    user_id = Column(Integer, primary_key=True)
    chat_id = Column(String(14), primary_key=True)

    def __init__(self, user_id, chat_id):
        self.user_id = user_id
        self.chat_id = str(chat_id)

    def __repr__(self):
        return "<User {} subscribed to Pinger in {}.>".format(self.user_id, self.chat_id)

class MentionMembers(BASE):
    __tablename__ = "mention"

    user_id = Column(Integer, primary_key=True)
    chat_id = Column(String(14), primary_key=True)

    def __init__(self, user_id, chat_id):
        self.chat_id = chat_id
        self.user_id = user_id

    def __repr__(self):
        return "<Chat user {} ({}) in chat {} ({})>".format(self.user_id, self.user_id,
                                                            self.chat_id, self.chat_id)

    def to_dict(self):
        return { "user": self.user_id,
                "chat": self.chat_id }

class RemoveMentions(BASE):
    __tablename__ = "mention"

    user_id = Column(Integer, primary_key=True)
    chat_id = Column(String(14), primary_key=True)

    def __init__(self, user_id, chat_id):
        self.chat_id = chat_id
        self.user_id = user_id

    def __repr__(self):
        return "Removed all users from ping list in chat {}".format(self.chat_id)

class LastExecution(BASE):
    __tablename__ = "mention_time"

    chat_id = Column(String(14), primary_key=True)
    date_time = Column(DateTime(timezone=False))

    def __init__(self, chat_id, date_time="%"):
        self.chat_id = chat_id
        self.date_time = date_time

    def __repr__(self):
        return "Checked last command execution"

    def to_dict(self):
        return { "chat": self.chat_id,
                "date": self.date_time }

Mention.__table__.create(checkfirst=True)
LastExecution.__table__.create(checkfirst=True)

MENTION_INSERTION_LOCK = threading.RLock()

def add_mention(user_id, chat_id):
    with MENTION_INSERTION_LOCK:
        mention_user = SESSION.query(Mention).get((user_id, str(chat_id)))
        if not mention_user:
            mention_user = Mention(user_id, str(chat_id))
            SESSION.add(mention_user)
            SESSION.commit()
            SESSION.close()
            return True

        SESSION.close()
        return False


def remove_mention(user_id, chat_id):
    with MENTION_INSERTION_LOCK:
        mention_user = SESSION.query(Mention).get((user_id, str(chat_id)))
        if mention_user:
            SESSION.delete(mention_user)
            SESSION.commit()
            SESSION.close()
            return True

        SESSION.close()
        return False


def reset_all_mentions(user_id, chat_id):
    try:
        reset_mentions = SESSION.query(RemoveMentions).filter(RemoveMentions.chat_id == str(chat_id)).all()
        print(str(reset_mentions))
        if reset_mentions:
            SESSION.query(RemoveMentions).filter(RemoveMentions.chat_id == str(chat_id)).delete()
            SESSION.commit()
            SESSION.close()
            return True
        else:
            return False
    except:
        SESSION.close()
        return False
    finally:
        SESSION.close()


def get_ping_list(user_id, chat_id):
    try:
        return [x.to_dict() for x in SESSION.query(MentionMembers).filter(MentionMembers.chat_id == str(chat_id)).limit(200).all()]
    except:
        SESSION.close()
    finally:
        SESSION.close()

def last_execution(chat_id, date_time, time=10):
    with MENTION_INSERTION_LOCK:
        last_execution = SESSION.query(LastExecution).get(str(chat_id))
        if not last_execution:
            last_execution = LastExecution(str(chat_id), date_time)
            SESSION.add(last_execution)
            SESSION.commit()
            SESSION.close()
            return False

        last_exec = [x.to_dict() for x in SESSION.query(LastExecution).filter(LastExecution.chat_id == str(chat_id))]
        for i in last_exec:
            duration = datetime.datetime.utcnow() - i["date"]
            duration_in_s = duration.total_seconds()
            if divmod(duration_in_s, 60)[0] >= time:
                last_execution = LastExecution(str(chat_id), datetime.datetime.utcnow())
                SESSION.merge(last_execution)
                SESSION.commit()
                SESSION.close()
                return True

        return False
