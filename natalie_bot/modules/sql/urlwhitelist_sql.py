import threading

from sqlalchemy import Column, String, UnicodeText

from natalie_bot.modules.sql import BASE, SESSION


class URLWHITELISTFilters(BASE):
    __tablename__ = "url_whitelist"
    chat_id = Column(String(14), primary_key=True)
    domain = Column(UnicodeText, primary_key=True, nullable=False)

    def __init__(self, chat_id, domain):
        self.chat_id = str(chat_id)
        self.domain = str(domain)


URLWHITELISTFilters.__table__.create(checkfirst=True)

URL_WHITELIST_FILTER_INSERTION_LOCK = threading.RLock()

CHAT_URL_WHITELISTS = {}


def add_to_whitelist(chat_id, domain):
    with URL_WHITELIST_FILTER_INSERTION_LOCK:
        domain_filt = URLWHITELISTFilters(str(chat_id), domain)

        SESSION.merge(domain_filt)
        SESSION.commit()
        CHAT_URL_WHITELISTS.setdefault(str(chat_id), set()).add(domain)


def rm_url_from_whitelist(chat_id, domain):
    with URL_WHITELIST_FILTER_INSERTION_LOCK:
        domain_filt = SESSION.query(
            URLWHITELISTFilters).get((str(chat_id), domain))
        if domain_filt:
            if domain in CHAT_URL_WHITELISTS.get(str(chat_id), set()):
                CHAT_URL_WHITELISTS.get(str(chat_id), set()).remove(domain)
            SESSION.delete(domain_filt)
            SESSION.commit()
            return True

        SESSION.close()
        return False


def get_whitelisted_urls(chat_id):
    return CHAT_URL_WHITELISTS.get(str(chat_id), set())


def _load_chat_whitelist():
    global CHAT_URL_WHITELISTS
    try:
        chats = SESSION.query(URLWHITELISTFilters.chat_id).distinct().all()
        for (chat_id,) in chats:
            CHAT_URL_WHITELISTS[chat_id] = []

        all_urls = SESSION.query(URLWHITELISTFilters).all()
        for url in all_urls:
            CHAT_URL_WHITELISTS[url.chat_id] += [url.domain]
        CHAT_URL_WHITELISTS = {
            k: set(v) for k,
            v in CHAT_URL_WHITELISTS.items()}
    finally:
        SESSION.close()


_load_chat_whitelist()
