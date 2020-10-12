from __future__ import unicode_literals

from datetime import datetime
from tkinter.messagebox import showerror, askokcancel
from multiprocessing import Pipe
from tkinter import *
from threading import Lock, Thread

import os
import logging
import sys
import string


class LogHandle(object):
    __file_dir = None
    __base_name = None
    __gui_console = None
    __write_pipe = None
    __read_pipe = None
    __pipe_thread = None

    """
    Logging that becomes easier and more uniformed
    """

    def __init__(self, file_dir=None, base_name=None):
        """
        Logging settings not forgotten!

        :param file_dir: File directory of where log files will be saved
        :param base_name: A base filename that log files will be saved as
        """

        self.file_dir = file_dir
        self.base_name = base_name
        self.__printable = set(string.printable)

    @property
    def write_pipe(self):
        if not self.__write_pipe:
            if self.__read_pipe:
                self.__read_pipe.close()

            self.__write_pipe, self.__read_pipe = Pipe()

        if not self.__pipe_thread:
            self.__pipe_thread = Thread(target=self.__pipe_listen)
            self.__pipe_thread.daemon = True
            self.__pipe_thread.start()

        return self.__write_pipe

    @property
    def file_dir(self):
        return self.__file_dir

    @file_dir.setter
    def file_dir(self, file_dir):
        if not isinstance(file_dir, (str, type(None))):
            raise Exception("'file_dir' is missing")
        if file_dir and not os.path.exists(file_dir):
            raise Exception("'file_dir' does not exist")

        self.__file_dir = file_dir

    @property
    def base_name(self):
        return self.__base_name

    @base_name.setter
    def base_name(self, base_name):
        if not isinstance(base_name, (str, type(None))):
            raise Exception("'base_name' is missing")

        self.__base_name = base_name

    @property
    def gc(self):
        return self.__gui_console

    @gc.setter
    def gc(self, gc):
        self.__gui_console = gc

    @staticmethod
    def __clean_handlers():
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

    def __pipe_listen(self):
        while True:
            args = self.__read_pipe.recv()

            if isinstance(args, dict) and 'command' in args.keys():
                command = args['command']
                del args['command']

                if command == 'gui_console':
                    self.__gui_console_set(**args)
                elif command == 'write_to_log':
                    self.__write_to_log(**args)
            elif isinstance(args, list) and len(args) > 1:
                command = args[0]
                args.remove(args[0])

                if command == 'gui_console':
                    self.__gui_console_set(*args)
                elif command == 'write_to_log':
                    self.__write_to_log(*args)

    def gui_console(self, title=None, destroy=False, turn_off=False, gui_obj=None):
        if gui_obj and hasattr(gui_obj, "print_gui") and hasattr(gui_obj, "log_setup"):
            self.__gui_console = gui_obj
            self.__gui_console.log_setup(log_class=self)
        else:
            self.__gui_console_set(title=title, destroy=destroy, turn_off=turn_off)

    def write_to_log(self, message, action='info', print_only=False):
        self.__write_to_log(message=message, action=action, print_only=print_only)

    def __gui_console_set(self, title=None, destroy=False, turn_off=False, *args, **kwargs):
        if self.__gui_console and destroy:
            self.__gui_console.destroy()
            self.__gui_console = None
        elif self.__gui_console and turn_off:
            self.__gui_console = None
        else:
            self.__gui_console = GUIConsole(parent=self, title=title)

    def __write_to_log(self, message, action='info', print_only=False, *args, **kwargs):
        """
        Logging becomes more organized!

        :param message: Message that you would like to write to log
        :param action: What kind of action would you like the entry to be marked as?
            (debug, info, warning, error, critical)
        :param print_only: (True/False) print line only and not log into file
        """

        if not print_only and self.__base_name and self.__file_dir:
            if not message:
                raise Exception("'message' is missing")

            self.__clean_handlers()
            filepath = os.path.join(self.__file_dir,
                                    "{0}_{1}_Log.txt".format(datetime.now().__format__("%Y%m%d"), self.__base_name))

            logging.basicConfig(filename=filepath,
                                level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')

        message = ''.join(filter(lambda x: x in self.__printable, message))

        if self.__gui_console:
            self.__gui_console.print_gui('{0} - {1} - {2}'.format(datetime.now().__format__("%Y%m%d %I:%M:%S %p"),
                                                                  action.upper(), message))
        else:
            print('{0} - {1} - {2}'.format(datetime.now(), action.upper(), message))

        if not print_only and self.__base_name and self.__file_dir:
            if action.lower() == 'debug':
                logging.debug(message)
            elif action.lower() == 'info':
                logging.info(message)
            elif action.lower() == 'warning':
                logging.warning(message)
            elif action.lower() == 'error':
                logging.error(message)
            elif action.lower() == 'critical':
                logging.critical(message)

    def __del__(self):
        logging.shutdown()


class GUIConsole(Toplevel):
    __print_lock = Lock()
    __print_queue = list()
    __console_text = None

    """
        Class to show logging in a GUI window by using Toplevel in tkinter
    """

    def __init__(self, parent, title):
        Toplevel.__init__(self)
        self.__parent = parent
        self.bind('<Destroy>', self.__cleanup)

        if title is None:
            self.title("GUI Log")
        else:
            self.title(title)

        self.__build()
        self.__start_idle()

    def __cleanup(self, event):
        self.__parent.gc = None

    def __start_idle(self):
        self.after(5, self.__on_idle)

    def print_gui(self, msg, sep='\n'):
        with self.__print_lock:
            self.__print_queue.append(str(msg) + sep)

    def __build(self):
        my_frame = Frame(self)
        my_frame.pack()

        xbar = Scrollbar(my_frame, orient='horizontal')
        ybar = Scrollbar(my_frame, orient='vertical')
        self.__console_text = Text(my_frame, bg="black", fg="white", wrap="none", yscrollcommand=ybar,
                                   xscrollcommand=xbar)
        xbar.config(command=self.__console_text.xview)
        ybar.config(command=self.__console_text.yview)
        self.__console_text.grid(row=0, column=0)
        xbar.grid(row=1, column=0, sticky=W + E)
        ybar.grid(row=0, column=1, sticky=N + S)

    def __on_idle(self):
        with self.__print_lock:
            for msg in self.__print_queue:
                self.__console_text.insert(END, msg)
                self.__console_text.see(END)

            self.__print_queue = []

        self.after(5, self.__on_idle)
