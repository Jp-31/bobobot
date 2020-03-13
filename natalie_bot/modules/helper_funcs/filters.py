from telegram import Message
from telegram.ext import BaseFilter

from natalie_bot import SUPPORT_USERS, iSUDO_USERS, SUDO_USERS, SUPER_ADMINS


class CustomFilters(object):
    class _Supporters(BaseFilter):
        def filter(self, message: Message):
            return bool(message.from_user and message.from_user.id in SUPPORT_USERS)

    support_filter = _Supporters()

    class _Sudoers(BaseFilter):
        def filter(self, message: Message):
            return bool(message.from_user and message.from_user.id in SUDO_USERS)

    sudo_filter = _Sudoers()
    
    class _iSudoers(BaseFilter):
        def filter(self, message: Message):
            return bool(message.from_user and message.from_user.id in iSUDO_USERS)

    isudo_filter = _iSudoers()
    
    class _SuperAdminers(BaseFilter):
        def filter(self, message: Message):
            return bool(message.from_user and message.from_user.id in SUPER_ADMINS)

    super_admins_filter = _SuperAdminers()

    class _MimeType(BaseFilter):
        def __init__(self, mimetype):
            self.mime_type = mimetype
            self.name = "CustomFilters.mime_type({})".format(self.mime_type)

        def filter(self, message: Message):
            return bool(message.document and message.document.mime_type == self.mime_type)

    mime_type = _MimeType

    class _HasText(BaseFilter):
        def filter(self, message: Message):
            return bool(message.text or message.sticker or message.photo or message.document or message.video)

    has_text = _HasText()

    class _AnimatedSticker(BaseFilter):
        def filter(self, message: Message):
            if message.sticker:
                return bool(message.sticker.is_animated)

    animated_sticker = _AnimatedSticker()