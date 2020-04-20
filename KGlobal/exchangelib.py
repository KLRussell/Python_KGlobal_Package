from __future__ import unicode_literals

from independentsoft.msg import Message as Msg
from independentsoft.msg import Recipient, ObjectType, DisplayType, AttachmentMethod, RecipientType, MessageFlag,\
    Attachment, Importance
from exchangelib import FileAttachment, ItemAttachment
from exchangelib import Message as Msg2, Account
from bs4 import BeautifulSoup


class E2M(Msg):
    def __init__(self, ex_lib_item):
        """
        Lets create a .MSG object!

        :param ex_lib_item: Exchangelib message item
        """

        if not isinstance(ex_lib_item, Msg2):
            ValueError("'ex_lib_item' %r is not an instance of ExchangeLib's Message" % ex_lib_item)

        self.__ex_lib_item = ex_lib_item
        self.__msg_attachs = []
        self.__mail_attr()
        self.__rec_proc(self.__ex_lib_item.to_recipients, RecipientType.TO)
        self.__rec_proc(self.__ex_lib_item.cc_recipients, RecipientType.CC)
        self.__mail_attach()
        self.__attach_mail_objs()

        super().__init__()

    def __mail_attr(self):
        self.object_type = ObjectType.MESSAGE
        importance = self.__ex_lib_item.importance
        received_time = self.__ex_lib_item.datetime_received

        if not received_time:
            received_time = self.__ex_lib_item.datetime_created

        if importance == 'Normal':
            self.importance = Importance.NORMAL
        elif importance == 'High':
            self.importance = Importance.HIGH
        elif importance == 'Low':
            self.importance = Importance.LOW
        else:
            self.importance = Importance.NONE

        if received_time:
            received_time = received_time.replace(tzinfo=None)
            self.client_submit_time = received_time
            self.message_delivery_time = received_time

        with self.__ex_lib_item.sender as sender:
            if sender:
                self.reply_to = sender.email_address
                self.in_reply_to = sender.email_address
                self.sender_address_type = sender.routing_type
                self.sender_name = sender.name
                self.sender_search_key = '{0}:{1}\x00'.format(sender.routing_type, sender.email_address).encode()
                self.sender_smtp_address = sender.email_address
                self.sender_email_address = sender.email_address
                self.sent_address_type = sender.routing_type
                self.sent_name = sender.name
                self.sent_search_key = '{0}:{1}\x00'.format(sender.routing_type, sender.email_address).encode()
                self.sent_smtp_address = sender.email_address
                self.sent_email_address = sender.email_address

        if self.__ex_lib_item.display_to:
            self.display_to = self.__ex_lib_item.display_to

        if self.__ex_lib_item.display_cc:
            self.display_cc = self.__ex_lib_item.display_cc

        if self.__ex_lib_item.has_attachments:
            self.has_attachment = self.__ex_lib_item.has_attachments

        self.subject = self.subject
        self.message_flags.append(MessageFlag.HAS_ATTACHMENT)
        self.message_flags.append(MessageFlag.READ)

        if self.__ex_lib_item.text_body:
            self.body_html_text = self.__ex_lib_item.text_body
        elif self.__ex_lib_item.body:
            if bool(BeautifulSoup(self.__ex_lib_item.body, 'html.parser').find()):
                self.body_html_text = self.__ex_lib_item.body
            else:
                self.body_html_text = self.__ex_lib_item.body
        else:
            self.body_html_text = None

    def __rec_proc(self, recs, rec_type):
        if recs:
            for rec in recs:
                self.__pack_rec(rec_type, rec.routing_type, rec.name, rec.email_address)

    def __pack_rec(self, rec_type, rout_type, rec_name, rec_email):
        rec = Recipient()
        rec.address_type = rout_type
        rec.display_type = DisplayType.MAIL_USER
        rec.object_type = ObjectType.MAIL_USER
        rec.display_name = rec_name
        rec.email_address = rec_email
        rec.smtp_address = rec_email
        rec.recipient_type = rec_type
        self.recipients.append(rec)

    def __mail_attach(self):
        if self.__ex_lib_item.attachments:
            for attach in self.__ex_lib_item.attachments:
                if isinstance(attach, FileAttachment):
                    with attach.fp as fp:
                        buffer = fp.read()

                    sub_attach = Attachment(buffer=buffer)
                    sub_attach.file_name = attach.name

                    if attach.is_inline:
                        sub_attach.content_id = attach.content_id
                        sub_attach.method = AttachmentMethod.EMBEDDED_MESSAGE

                    self.attachments.append(sub_attach)
                elif isinstance(attach, ItemAttachment) and isinstance(attach.item, Msg2):
                    self.__msg_attachs.append(ExchangeToMsg(attach.item))

    def __attach_mail_objs(self):
        if self.__msg_attachs:
            for msg in self.__msg_attachs:
                message, subject, received_time = msg.grab_objs()
                sub_attach = Attachment(buffer=message.to_bytes())
                sub_attach.file_name = '%s.msg' % subject
                self.attachments.append(sub_attach)


class ExchangeToMsg(E2M):
    """
    Convert Exchangelib Mail items into .MSG files. Use .save() to save message to filepath
    """
    def __init__(self, ex_lib_item):
        E2M.__init__(self, ex_lib_item)


class Exchange(Account):
    """
    Lets make this a child class of Exchangelib's Account so that we can add renew_session()
    """
    def __init__(self, primary_smtp_address, fullname=None, access_type=None, autodiscover=False, credentials=None,
                 config=None, locale=None, default_timezone=None):
        Account.__init__(self, primary_smtp_address=primary_smtp_address, fullname=fullname, access_type=access_type,
                         autodiscover=autodiscover, credentials=credentials, config=config, locale=locale,
                         default_timezone=default_timezone)

    def renew_session(self):
        """
        Renew e-mail session by retiring old session and starting new session. Great way to keep the connection live
        """

        session = self.protocol.get_session()

        if session:
            self.protocol.retire_session(session)
