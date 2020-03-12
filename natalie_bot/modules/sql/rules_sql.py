import threading

from sqlalchemy import Column, String, UnicodeText, BigInteger, func, distinct

from natalie_bot.modules.sql import SESSION, BASE


class Rules(BASE):
    __tablename__ = "rules"
    chat_id = Column(String(14), primary_key=True)
    rules = Column(UnicodeText, default="")
    chat_rules = Column(BigInteger)

    def __init__(self, chat_id):
        self.chat_id = chat_id

    def __repr__(self):
        return "<Chat {} rules: {}>".format(self.chat_id, self.rules)


Rules.__table__.create(checkfirst=True)

INSERTION_LOCK = threading.RLock()


def set_rules(chat_id, rules_text):
    with INSERTION_LOCK:
        rules = SESSION.query(Rules).get(str(chat_id))
        if not rules:
            rules = Rules(str(chat_id))
        rules.rules = rules_text

        SESSION.add(rules)
        SESSION.commit()


def get_rules(chat_id):
    rules = SESSION.query(Rules).get(str(chat_id))
    ret = ""
    if rules:
        ret = rules.rules

    SESSION.close()
    return ret

def set_chat_rules(chat_id, chat_rules):
    with INSERTION_LOCK:
        curr = SESSION.query(Rules).get(str(chat_id))
        if not curr:
            curr = Rules(str(chat_id))

        curr.chat_rules = int(chat_rules)

        SESSION.add(curr)
        SESSION.commit()

def get_chat_rules_pref(chat_id):
    curr = SESSION.query(Rules).get(str(chat_id))
    SESSION.close()

    if curr:
        return curr.chat_rules

    return False

def num_chats():
    try:
        return SESSION.query(func.count(distinct(Rules.chat_id))).scalar()
    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with INSERTION_LOCK:
        chat = SESSION.query(Rules).get(str(old_chat_id))
        if chat:
            chat.chat_id = str(new_chat_id)
        SESSION.commit()
