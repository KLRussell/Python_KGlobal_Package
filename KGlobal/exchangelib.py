from __future__ import unicode_literals

from independentsoft.msg import Message as Msg
from independentsoft.msg import Recipient, ObjectType, DisplayType, AttachmentMethod, RecipientType, MessageFlag,\
    Attachment, Importance
from exchangelib import FileAttachment, ItemAttachment
from exchangelib import Message as Msg2, Account
from bs4 import BeautifulSoup
from os.path import exists, dirname
from logging import getLogger, WARNING

getLogger("exchangelib").setLevel(WARNING)


class ExchangeToMsg(object):
    def __init__(self, ex_lib_item):
        if not isinstance(ex_lib_item, Msg2):
            ValueError('Exchangelib object is not an item class from Exchangelib library')

        self.ex_lib_item = ex_lib_item
        self.subject = self.ex_lib_item.subject

        if self.ex_lib_item.datetime_received:
            self.received_time = self.ex_lib_item.datetime_received.replace(tzinfo=None)
        elif self.ex_lib_item.datetime_created:
            self.received_time = self.ex_lib_item.datetime_created.replace(tzinfo=None)
        else:
            self.received_time = None

        self.message = Msg()
        self.__msg_attachs = []

        self.__mail_attr()
        self.__rec_proc(self.ex_lib_item.to_recipients, RecipientType.TO)
        self.__rec_proc(self.ex_lib_item.cc_recipients, RecipientType.CC)
        self.__mail_attach()
        self.__attach_mail_objs()

    def __mail_attr(self):
        self.message.object_type = ObjectType.MESSAGE

        if self.ex_lib_item.importance == 'Normal':
            self.message.importance = Importance.NORMAL
        elif self.ex_lib_item.importance == 'High':
            self.message.importance = Importance.HIGH
        elif self.ex_lib_item.importance == 'Low':
            self.message.importance = Importance.LOW
        else:
            self.message.importance = Importance.NONE

        if self.received_time:
            self.message.client_submit_time = self.received_time
            self.message.message_delivery_time = self.received_time

        if self.ex_lib_item.sender:
            self.message.reply_to = self.ex_lib_item.sender.email_address
            self.message.in_reply_to = self.ex_lib_item.sender.email_address
            self.message.sender_address_type = self.ex_lib_item.sender.routing_type
            self.message.sender_name = self.ex_lib_item.sender.name
            self.message.sender_search_key = '{0}:{1}\x00'.format(self.ex_lib_item.sender.routing_type,
                                                                  self.ex_lib_item.sender.email_address).encode()
            self.message.sender_smtp_address = self.ex_lib_item.sender.email_address
            self.message.sender_email_address = self.ex_lib_item.sender.email_address
            self.message.sent_address_type = self.ex_lib_item.sender.routing_type
            self.message.sent_name = self.ex_lib_item.sender.name
            self.message.sent_search_key = '{0}:{1}\x00'.format(self.ex_lib_item.sender.routing_type,
                                                                self.ex_lib_item.sender.email_address).encode()
            self.message.sent_smtp_address = self.ex_lib_item.sender.email_address
            self.message.sent_email_address = self.ex_lib_item.sender.email_address

        if self.ex_lib_item.display_to:
            self.message.display_to = self.ex_lib_item.display_to

        if self.ex_lib_item.display_cc:
            self.message.display_cc = self.ex_lib_item.display_cc

        if self.ex_lib_item.has_attachments:
            self.message.has_attachment = self.ex_lib_item.has_attachments

        self.message.subject = self.subject
        self.message.message_flags.append(MessageFlag.HAS_ATTACHMENT)
        self.message.message_flags.append(MessageFlag.READ)

        if self.ex_lib_item.text_body:
            self.message.body_html_text = self.ex_lib_item.text_body
        elif self.ex_lib_item.body:
            if bool(BeautifulSoup(self.ex_lib_item.body, 'html.parser').find()):
                self.message.body_html_text = self.ex_lib_item.body
            else:
                self.message.body_html_text = self.ex_lib_item.body
        else:
            self.message.body_html_text = None

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
        self.message.recipients.append(rec)

    def __mail_attach(self):
        if self.ex_lib_item.attachments:
            for attach in self.ex_lib_item.attachments:
                if isinstance(attach, FileAttachment):
                    with attach.fp as fp:
                        buffer = fp.read()

                    sub_attach = Attachment(buffer=buffer)
                    sub_attach.file_name = attach.name

                    if attach.is_inline:
                        sub_attach.content_id = attach.content_id
                        sub_attach.method = AttachmentMethod.EMBEDDED_MESSAGE

                    self.message.attachments.append(sub_attach)
                elif isinstance(attach, ItemAttachment) and isinstance(attach.item, Msg2):
                    self.__msg_attachs.append(ExchangeToMsg(attach.item))

    def __attach_mail_objs(self):
        if self.__msg_attachs:
            for msg in self.__msg_attachs:
                message, subject, received_time = msg.grab_objs()

                # This attaches the message as an embedded message, but it is missing a sequence somewhere
                '''
                sub_attach = Attachment()
                message.message_flags.append(MessageFlag.HAS_ATTACHMENT)
                message.message_flags.append(MessageFlag.READ)
                message.is_embedded = False
                sub_attach.embedded_message = message
                sub_attach.display_name = subject
                sub_attach.file_name = subject
                sub_attach.method = AttachmentMethod.EMBEDDED_MESSAGE
                sub_attach.flags = AttachmentFlags.NONE
                sub_attach.object_type = ObjectType.ATTACHMENT
                sub_attach.creation_time = datetime.datetime.now()
                sub_attach.last_modification_time = received_time
                '''
                sub_attach = Attachment(buffer=message.to_bytes())
                sub_attach.file_name = '%s.msg' % subject

                self.message.attachments.append(sub_attach)

    def grab_objs(self):
        return [self.message, self.subject, self.received_time]

    def save(self, file_path):
        if file_path and exists(dirname(file_path)):
            self.message.save(file_path)


class Exchange(Account):
    __auto_renew = None
    __auto_renew_thread = None

    """
    Lets make this a child class of Exchangelib's Account so that we can add renew_session()
    """

    def __init__(self, primary_smtp_address, fullname=None, access_type=None, autodiscover=False, credentials=None,
                 config=None, locale=None, default_timezone=None, auto_renew=False):
        Account.__init__(self, primary_smtp_address=primary_smtp_address, fullname=fullname, access_type=access_type,
                         autodiscover=autodiscover, credentials=credentials, config=config, locale=locale,
                         default_timezone=default_timezone)

        if auto_renew:
            self.start_auto_renew()

    def __auto_renew_session(self):
        from time import sleep
        self.__auto_renew = True
        counter = 0

        while self.__auto_renew:
            if counter > 70:
                counter = 0
                self.renew_session()

            sleep(1)
            counter += 1

    def start_auto_renew(self):
        if not self.__auto_renew_thread or not self.__auto_renew_thread.is_alive():
            from threading import Thread
            self.__auto_renew_thread = Thread(target=self.__auto_renew_session)
            self.__auto_renew_thread.daemon = True
            self.__auto_renew_thread.start()

    def stop_auto_renew(self):
        self.__auto_renew = False

        if self.__auto_renew_thread and self.__auto_renew_thread.is_alive():
            self.__auto_renew_thread.join()

        self.__auto_renew_thread = None

    def renew_session(self):
        """
        Renew e-mail session by retiring old session and starting new session. Great way to keep the connection live
        """

        session = self.protocol.get_session()

        if session:
            self.protocol.retire_session(session)

    __del__ = stop_auto_renew
