from __future__ import unicode_literals

from tkinter import filedialog, ttk
from tkinter.messagebox import showerror
from tkinter import *

import os


class SG(Tk):
    __pointer = None

    def __init__(self, local_db_dir, main_db_path=None, salt_key_path=None, pointer=None):
        Tk.__init__(self)

        from .data import DataConfig
        if not isinstance(pointer, (DataConfig, type(None))):
            raise ValueError("'pointer' %r is not an instance of DataConfig" % pointer)
        if not isinstance(local_db_dir, str):
            raise ValueError("'local_db_dir' %r is not an instance of String" % local_db_dir)
        if not isinstance(main_db_path, (str, type(None))):
            raise ValueError("'main_db_path' %r is not an instance of String" % main_db_path)
        if not isinstance(salt_key_path, (str, type(None))):
            raise ValueError("'salt_key_path' %r is not an instance of String" % salt_key_path)
        if not os.path.isdir(local_db_dir):
            raise ValueError("'local_db_dir' %r is not a valid directory" % local_db_dir)
        if main_db_path and not os.path.exists(main_db_path):
            main_db_path = os.path.dirname(main_db_path)
        if salt_key_path and not os.path.exists(salt_key_path):
            salt_key_path = os.path.dirname(salt_key_path)

        self.__pointer = pointer
        self.__local_db_dir = local_db_dir
        self.__salt_key_path = StringVar()
        self.__main_db_path = StringVar()
        self.__salt_key_dir = StringVar()
        self.__main_db_dir = StringVar()

        if salt_key_path:
            self.__salt_key_path.set(salt_key_path)

        if main_db_path:
            self.__main_db_path.set(main_db_path)

        self.__build()

    @property
    def pointer(self):
        """
        :return: Returns Pointer DataConfig object
        """

        return self.__pointer

    def __build(self):
        header = ['Welcome to new settings file setup!', 'Please fill out the below fields to setup']
        header2 = ['Welcome to existing settings file setup!', 'Please fill out the below fields to setup']

        # Set GUI Geometry and GUI Title
        self.geometry('280x215+550+150')
        self.title('Settings Setup')
        self.resizable(False, False)

        # Set GUI Frames
        t = ttk.Notebook(self)
        new_tab = ttk.Frame(t)
        existing_tab = ttk.Frame(t)
        t.add(new_tab, text='New Setup')
        t.add(existing_tab, text='Existing')

        new_header_frame = Frame(new_tab)
        new_salt_frame = LabelFrame(new_tab, text='Salt Key', width=508, height=70)
        new_settings_frame = LabelFrame(new_tab, text='Main DB', width=508, height=70)
        new_buttons_frame = Frame(new_tab)
        existing_header_frame = Frame(existing_tab)
        existing_salt_frame = LabelFrame(existing_tab, text='Salt Key', width=508, height=70)
        existing_main_frame = LabelFrame(existing_tab, text='Main DB', width=508, height=70)
        existing_buttons_frame = Frame(existing_tab)

        # Apply Frames into GUI
        t.pack(fill="both")
        new_header_frame.pack(fill="both")
        new_salt_frame.pack(fill="both")
        new_settings_frame.pack(fill="both")
        new_buttons_frame.pack(fill="both")
        existing_header_frame.pack(fill="both")
        existing_salt_frame.pack(fill="both")
        existing_main_frame.pack(fill="both")
        existing_buttons_frame.pack(fill="both")

        # Apply Header text to Header_Frame that describes purpose of GUI
        header = Message(self, text='\n'.join(header), width=500, justify=CENTER)
        header.pack(in_=new_header_frame)
        header2 = Message(self, text='\n'.join(header2), width=500, justify=CENTER)
        header2.pack(in_=existing_header_frame)

        # Apply Widgets to new_salt_frame
        #   Apply Salt Directory Entry Box Widget
        salt_dir_label = Label(new_salt_frame, text='Directory:')
        salt_dir_entry = Entry(new_salt_frame, textvariable=self.__salt_key_dir)
        salt_dir_label.grid(row=0, column=0, padx=4, pady=5)
        salt_dir_entry.grid(row=0, column=1, padx=4, pady=5)

        #   Apply Salt Directory Finder Button Widget
        find_salt_dir_button = Button(new_salt_frame, text='...', width=8, command=self.__salt_dir_gui)
        find_salt_dir_button.grid(row=0, column=2, padx=4, pady=5)

        # Apply Widgets to new_settings_frame
        #    Apply Settings Directory Entry Box Widget
        settings_dir_label = Label(new_settings_frame, text='Directory:')
        settings_dir_entry = Entry(new_settings_frame, textvariable=self.__main_db_dir)
        settings_dir_label.grid(row=0, column=0, padx=4, pady=5)
        settings_dir_entry.grid(row=0, column=1, padx=4, pady=5)

        #   Apply Settings Directory Finder Button Widget
        find_settings_dir_button = Button(new_settings_frame, text='...', width=8, command=self.__main_dir_gui)
        find_settings_dir_button.grid(row=0, column=2, padx=4, pady=5)

        # Apply Buttons to the new_buttons_frame
        #     Generate button
        generate_button = Button(self, text='Generate', width=15, command=self.__generate)
        generate_button.pack(in_=new_buttons_frame, side=LEFT, padx=7, pady=7)

        #     Cancel button
        cancel_button = Button(self, text='Cancel', width=15, command=self.__destroy)
        cancel_button.pack(in_=new_buttons_frame, side=RIGHT, padx=7, pady=7)

        # Apply Widgets to existing_frame
        #   Apply Salt Directory Entry Box Widget
        salt_fp_label = Label(existing_salt_frame, text='Filepath:')
        salt_fp_entry = Entry(existing_salt_frame, textvariable=self.__salt_key_path)
        salt_fp_label.grid(row=0, column=0, padx=4, pady=5)
        salt_fp_entry.grid(row=0, column=1, padx=4, pady=5)

        #   Apply Salt File Name Finder Button Widget
        find_salt_name_button = Button(existing_salt_frame, text='...', width=8, command=self.__salt_file_gui)
        find_salt_name_button.grid(row=0, column=2, padx=4, pady=5)

        #   Apply Main Filepath Entry Box Widget
        settings_fp_label = Label(existing_main_frame, text='Filepath:')
        settings_fp_entry = Entry(existing_main_frame, textvariable=self.__main_db_path)
        settings_fp_label.grid(row=1, column=0, padx=4, pady=5)
        settings_fp_entry.grid(row=1, column=1, padx=4, pady=5)

        #   Apply Main Filepath Finder Button Widget
        find_settings_name_button = Button(existing_main_frame, text='...', width=3, command=self.__main_file_gui)
        find_settings_name_button.grid(row=1, column=2, padx=4, pady=5)

        #   Apply Main File Directory Finder Button Widget
        find_settings_name_button = Button(existing_main_frame, text='Dir', width=3, command=self.__main_dir_gui2)
        find_settings_name_button.grid(row=1, column=3, padx=4, pady=5)

        # Apply Buttons to the existing_buttons_frame
        #     Generate button
        generate_button = Button(self, text='Generate', width=15, command=self.__generate2)
        generate_button.pack(in_=existing_buttons_frame, side=LEFT, padx=7, pady=7)

        #     Cancel button
        cancel_button = Button(self, text='Cancel', width=15, command=self.__destroy)
        cancel_button.pack(in_=existing_buttons_frame, side=RIGHT, padx=7, pady=7)

    def __destroy(self):
        self.__pointer = None
        self.destroy()

    def __salt_dir_gui(self):
        if self.__salt_key_dir.get() and os.path.exists(self.__salt_key_dir.get()):
            init_dir = self.__salt_key_dir.get()
        else:
            init_dir = self.__local_db_dir

        salt_dir = filedialog.askdirectory(initialdir=init_dir, title='Select Salt Directory', parent=self)

        if salt_dir:
            self.__salt_key_dir.set(salt_dir)

    def __salt_file_gui(self):
        if self.__salt_key_path.get() and os.path.exists(self.__salt_key_path.get()):
            init_dir = os.path.dirname(self.__salt_key_path.get())
            init_file = os.path.basename(self.__salt_key_path.get())
        else:
            init_dir = self.__local_db_dir
            init_file = ''

        file_path = filedialog.askopenfile(initialdir=init_dir, initialfile=init_file, title='Select Salt Key',
                                           filetypes=[("key files", "*.key")], parent=self)

        if file_path:
            self.__salt_key_path.set(file_path.name)
            file_path.close()

    def __main_dir_gui(self):
        if self.__main_db_dir.get() and os.path.exists(self.__main_db_dir.get()):
            init_dir = self.__main_db_dir.get()
        else:
            init_dir = self.__local_db_dir

        settings_dir = filedialog.askdirectory(initialdir=init_dir, title='Select Main DB Directory', parent=self)

        if settings_dir:
            self.__main_db_dir.set(settings_dir)

    def __main_dir_gui2(self):
        if self.__main_db_path.get() and os.path.exists(self.__main_db_path.get()):
            init_dir = self.__main_db_path.get()
        else:
            init_dir = self.__local_db_dir

        settings_dir = filedialog.askdirectory(initialdir=init_dir, title='Select Main DB Directory', parent=self)

        if settings_dir:
            self.__main_db_path.set(settings_dir)

    def __main_file_gui(self):
        if self.__main_db_path.get() and os.path.exists(self.__main_db_path.get()):
            init_dir = os.path.dirname(self.__main_db_path.get())
            init_file = os.path.basename(self.__main_db_path.get())
        else:
            init_dir = self.__local_db_dir
            init_file = ''

        settings_name = filedialog.askopenfile(initialdir=init_dir, initialfile=init_file,
                                               title='Select Main DB', filetypes=[("db files", "*.db")],
                                               parent=self)

        if settings_name:
            self.__main_db_path.set(settings_name.name)
            settings_name.close()

    def __generate2(self):
        if not self.__salt_key_path:
            showerror('Field Empty Error!', 'No value has been inputed for Salt Key Path', parent=self)
        elif not self.__main_db_path:
            showerror('Field Empty Error!', 'No value has been inputed for Main DB Path', parent=self)
        elif not os.path.isfile(self.__salt_key_path.get()):
            showerror('Invalid Path Error!', 'Salt Key Path is not a file!', parent=self)
        elif not os.path.isfile(self.__main_db_path.get()) and not os.path.isdir(self.__main_db_path.get()):
            showerror('Invalid Path Error!', 'Main DB Path is not a file or directory!', parent=self)
        elif not os.path.exists(self.__salt_key_path.get()):
            showerror('Path Exist Error!', 'Salt Key Path does not exist!', parent=self)
        elif not os.path.exists(self.__main_db_path.get()):
            showerror('Path Exist Error!', 'Main DB Path does not exist!', parent=self)
        else:
            if not self.__pointer:
                from .data import DataConfig
                from . import master_salt_filepath

                self.__pointer = DataConfig(file_dir=self.__local_db_dir,
                                            file_name_prefix='Script_Pointer', file_ext='ptr',
                                            salt_key_fp=master_salt_filepath(), new_salt_key=False, encrypt=True)

            self.__pointer.setcrypt(key='Key_Path', val=self.__salt_key_path.get(), private=True)
            self.__pointer.setcrypt(key='Local_DB_Path', val=os.path.join(self.__local_db_dir, 'Local_Settings.db'),
                                    private=True)
            if os.path.isfile(self.__main_db_path.get()):
                self.__pointer.setcrypt(key='Main_DB_Path', val=self.__main_db_path.get(), private=True)
            else:
                self.__pointer.setcrypt(key='Main_DB_Path', val=os.path.join(self.__main_db_path.get(),
                                                                             'Main_Settings.db'), private=True)
            self.__pointer.sync()
            self.destroy()

    def __generate(self):
        if not self.__salt_key_dir:
            showerror('Field Empty Error!', 'No value has been inputed for Salt Key Directory', parent=self)
        elif not self.__main_db_dir:
            showerror('Field Empty Error!', 'No value has been inputed for Main DB Directory', parent=self)
        elif not os.path.isdir(self.__salt_key_dir.get()):
            showerror('Invalid Directory!', 'Salt Key Directory is an invalid directory', parent=self)
        elif not os.path.isdir(self.__main_db_dir.get()):
            showerror('Invalid Directory!', 'Main DB Directory is an invalid directory', parent=self)
        elif not os.path.exists(self.__salt_key_dir.get()):
            showerror('Directory Not Exist!', 'Salt Key Directory does not exist', parent=self)
        elif not os.path.exists(self.__main_db_dir.get()):
            showerror('Directory Not Exist!', 'Main DB Directory does not exist', parent=self)
        else:
            if not self.__pointer:
                from .data import DataConfig
                from . import master_salt_filepath

                self.__pointer = DataConfig(file_dir=self.__local_db_dir,
                                            file_name_prefix='Script_Pointer', file_ext='ptr',
                                            salt_key_fp=master_salt_filepath(), new_salt_key=False, encrypt=True)

            salt_path = os.path.join(self.__salt_key_dir.get(), 'Salt_Key.key')

            if not os.path.exists(salt_path):
                from .data import create_salt
                create_salt(self.__salt_key_dir.get(), 'Salt_Key.key')

            self.__pointer.setcrypt(key='Key_Path', val=salt_path, private=True)
            self.__pointer.setcrypt(key='Local_DB_Path', val=os.path.join(self.__local_db_dir, 'Local_Settings.db'),
                                    private=True)
            self.__pointer.setcrypt(key='Main_DB_Path', val=os.path.join(self.__main_db_dir.get(), 'Main_Settings.db'),
                                    private=True)
            self.__pointer.sync()
            self.destroy()


class SetupGUI(SG):
    """
    Setup GUI for Salt Key, Main DB, Local DB, and Pointer files
    """

    def __init__(self, local_db_dir, main_db_path=None, salt_key_path=None, pointer=None):
        """
        :param local_db_dir:  Local DB directory (aka local script directory)
        :param main_db_path: (Optional) Main DB filepath
        :param salt_key_path: (Optional) Salt Key filepath
        :param pointer: (Optional) Pointer .ptr DataConfig instance class
        """

        SG.__init__(self, local_db_dir, main_db_path, salt_key_path, pointer)
        self.mainloop()


class CG(Tk):
    def __init__(self, cred=None, user_name=None, user_pass=None):
        Tk.__init__(self)

        from .credentials import Credentials
        from .data import CryptHandle

        if not isinstance(cred, (Credentials, type(None))):
            raise ValueError("'cred' %r is not an instance of Credentials" % cred)
        if not isinstance(user_name, (str, type(None))):
            raise ValueError("'user_name' %r is not a String" % user_name)
        if not isinstance(user_pass, (str, type(None))):
            raise ValueError("'user_pass' %r is not a String" % user_pass)

        self.__cred = cred
        self.__user_name = StringVar()
        self.__user_pass = StringVar()

        if cred:
            self.__user_name = self.__cred.username
            self.__user_pass = self.__cred.password
            self.__user_name.set(self.__user_name_obj.peak())
            self.__user_pass.set(self.__user_pass_obj.peak())
        else:
            self.__user_name_obj = CryptHandle(private=False)
            self.__user_pass_obj = CryptHandle(private=True)

            if user_name:
                self.__user_name_obj.encrypt(user_name)
                self.__user_name.set(self.__user_name_obj.peak())

            if user_pass:
                self.__user_pass_obj.encrypt(user_pass)
                self.__user_pass.set(self.__user_pass_obj.peak())

        self.__build()

    @property
    def credentials(self):
        """
        :return: Returns Credentials instance class, which holds username & password in CryptHandle objects
        """

        return self.__cred

    def __build(self):
        header = ['Welcome to Credential Creating', 'Please fill out the fields below']

        # Set GUI Geometry and GUI Title
        self.geometry('217x160+650+280')
        self.title('Credentials Setup')
        self.resizable(False, False)

        # Set GUI Frames
        header_frame = Frame(self)
        cred_frame = LabelFrame(self, text='Credentials', width=508, height=70)
        buttons_frame = Frame(self)

        # Apply Frames into GUI
        header_frame.pack(fill="both")
        cred_frame.pack(fill="both")
        buttons_frame.pack(fill="both")

        # Apply Header text to Header_Frame that describes purpose of GUI
        header = Message(self, text='\n'.join(header), width=500, justify=CENTER)
        header.pack(in_=header_frame)

        # Apply Widgets to Cred Frame
        #   Apply User Name Entry Box Widget
        user_name_label = Label(cred_frame, text='User Name:')
        user_name_entry = Entry(cred_frame, textvariable=self.__user_name)
        user_name_label.grid(row=0, column=0, padx=4, pady=5)
        user_name_entry.grid(row=0, column=1, padx=4, pady=5)

        #   Apply User Pass Entry Box Widget
        user_pass_label = Label(cred_frame, text='User Pass:')
        user_pass_entry = Entry(cred_frame, textvariable=self.__user_pass)
        user_pass_label.grid(row=1, column=0, padx=4, pady=5)
        user_pass_entry.grid(row=1, column=1, padx=4, pady=5)
        user_pass_entry.bind('<KeyRelease>', self.__hide_pass)

        # Apply Buttons to the Buttons Frame
        #     Save button
        save_button = Button(self, text='Save', width=13, command=self.__save)
        save_button.pack(in_=buttons_frame, side=LEFT, padx=7, pady=7)

        #     Cancel button
        cancel_button = Button(self, text='Cancel', width=13, command=self.destroy)
        cancel_button.pack(in_=buttons_frame, side=RIGHT, padx=7, pady=7)

    def __hide_pass(self, event):
        new_pass = self.__user_pass.get()
        curr_pass = self.__user_pass_obj.decrypt()

        if not curr_pass:
            curr_pass = ''

        curr_pass_len = len(curr_pass)

        if len(new_pass) > 0:
            curr_pass = self.__adjust_pass(new_pass, curr_pass)

            if curr_pass_len > len(new_pass):
                curr_pass = curr_pass[:len(new_pass)]
        else:
            curr_pass = new_pass

        self.__user_pass_obj.encrypt(curr_pass)
        self.__user_pass.set(self.__user_pass_obj.peak())

    @staticmethod
    def __adjust_pass(new_pass, curr_pass):
        curr_pass_len = len(curr_pass)

        for pos, letter in enumerate(new_pass):
            if letter != '*':
                if pos > curr_pass_len - 1:
                    curr_pass += letter
                else:
                    my_text = list(curr_pass)
                    my_text.insert(pos, letter)
                    curr_pass = ''.join(my_text)

        return curr_pass

    def __save(self):
        if not self.__user_name:
            showerror('Field Empty Error!', 'No value has been inputed for User Name', parent=self)
        elif not self.__user_pass:
            showerror('Field Empty Error!', 'No value has been inputed for User Pass', parent=self)
        else:
            from . import Credentials

            self.__user_name_obj.encrypt(self.__user_name.get())
            self.__cred = Credentials(user_name=self.__user_name_obj, user_pass=self.__user_pass_obj)
            self.destroy()


class CredentialsGUI(CG):
    """
    Credentials GUI for gathering Username and Password, and storing this information in encrypted objects within
    the Credentials instance class
    """

    def __init__(self, cred=None, user_name=None, user_pass=None):
        """

        :param cred: (Optional) Credentials instance class object
        :param user_name: (Optional) Username in String
        :param user_pass: (Optional) Userpass in String
        """

        CG.__init__(self, cred=cred, user_name=user_name, user_pass=user_pass)
        self.mainloop()


class EG(Tk):
    def __init__(self, server=None, email_addr=None):
        Tk.__init__(self)

        if not isinstance(server, (str, type(None))):
            raise ValueError("'server' %r is not a String" % server)
        if not isinstance(email_addr, (str, type(None))):
            raise ValueError("'email_addr' %r is not a String" % email_addr)

        from .data import CryptHandle

        self.__server_obj = CryptHandle()
        self.__email_addr_obj = CryptHandle()
        self.__server = StringVar()
        self.__email_addr = StringVar()

        if server:
            self.__server.set(server)

        if email_addr:
            self.__email_addr.set(email_addr)

        self.__build()

    @property
    def server(self):
        return self.__server_obj

    @property
    def email_addr(self):
        return self.__email_addr_obj

    def __build(self):
        header = ['Welcome to Email Settings!', 'Please fill out the fields below:']

        # Set GUI Geometry and GUI Title
        self.geometry('217x160+650+280')
        self.title('Credentials Setup')
        self.resizable(False, False)

        # Set GUI Frames
        header_frame = Frame(self)
        esettings_frame = LabelFrame(self, text='Email Settings', width=508, height=70)
        buttons_frame = Frame(self)

        # Apply Frames into GUI
        header_frame.pack(fill="both")
        esettings_frame.pack(fill="both")
        buttons_frame.pack(fill="both")

        # Apply Header text to Header_Frame that describes purpose of GUI
        header = Message(self, text='\n'.join(header), width=500, justify=CENTER)
        header.pack(in_=header_frame)

        # Apply Widgets to Cred Frame
        #   Apply User Name Entry Box Widget
        server_label = Label(esettings_frame, text='Server:')
        server_entry = Entry(esettings_frame, textvariable=self.__server)
        server_label.grid(row=0, column=0, padx=4, pady=5)
        server_entry.grid(row=0, column=1, padx=4, pady=5)

        #   Apply User Pass Entry Box Widget
        email_addr_label = Label(esettings_frame, text='Email Addr:')
        email_addr_entry = Entry(esettings_frame, textvariable=self.__email_addr)
        email_addr_label.grid(row=1, column=0, padx=4, pady=5)
        email_addr_entry.grid(row=1, column=1, padx=4, pady=5)

        # Apply Buttons to the Buttons Frame
        #     Save button
        save_button = Button(self, text='Save', width=13, command=self.__save)
        save_button.pack(in_=buttons_frame, side=LEFT, padx=7, pady=7)

        #     Cancel button
        cancel_button = Button(self, text='Cancel', width=13, command=self.destroy)
        cancel_button.pack(in_=buttons_frame, side=RIGHT, padx=7, pady=7)

    def __save(self):
        if not self.__server:
            showerror('Field Empty Error!', 'No value has been inputed for Server', parent=self)
        elif not self.__email_addr:
            showerror('Field Empty Error!', 'No value has been inputed for Email Addr', parent=self)
        elif not self.__email_addr.get().find('@'):
            showerror('Field Bad Result Error!', 'Email Addr does not have an @ in it')
        else:
            self.__server_obj.encrypt(self.__server.get())
            self.__email_addr_obj.encrypt(self.__email_addr.get())
            self.destroy()


class EmailGUI(EG):
    """
    Email GUI to find Server Address and Email address for email exchange connections
    """

    def __init__(self, server=None, email_addr=None):
        """

        :param server: (Optional) Server address in string format
        :param email_addr: (Optional) Email address in string format
        """
        EG.__init__(self, server=server, email_addr=email_addr)
        self.mainloop()


class SSG(Tk):
    def __init__(self, server=None, database=None):
        Tk.__init__(self)
        from .data import CryptHandle
        
        if not isinstance(server, (str, type(None))):
            raise ValueError("'server' %r is not a String" % server)
        if not isinstance(database, (str, type(None))):
            raise ValueError("'database' %r is not a String" % database)
        
        self.__server = StringVar()
        self.__database = StringVar()
        self.__server_obj = CryptHandle()
        self.__database_obj = CryptHandle()
        
        if server:
            self.__server.set(server)
        if database:
            self.__database.set(database)
        
        self.__build()

    @property
    def server(self):
        """
        :return: Returns CryptHandle object of server
        """

        return self.__server_obj

    @property
    def database(self):
        """
        :return: Returns CryptHandle object of database
        """

        return self.__database_obj
        
    def __build(self):
        header = ['Welcome to SQL Server Settings!', 'Please fill out the fields below:']

        # Set GUI Geometry and GUI Title
        self.geometry('217x160+650+280')
        self.title('SQL Server Setup')
        self.resizable(False, False)

        # Set GUI Frames
        header_frame = Frame(self)
        ssettings_frame = LabelFrame(self, text='SQL Settings', width=508, height=70)
        buttons_frame = Frame(self)

        # Apply Frames into GUI
        header_frame.pack(fill="both")
        ssettings_frame.pack(fill="both")
        buttons_frame.pack(fill="both")

        # Apply Header text to Header_Frame that describes purpose of GUI
        header = Message(self, text='\n'.join(header), width=500, justify=CENTER)
        header.pack(in_=header_frame)

        # Apply Widgets to Cred Frame
        #   Apply User Name Entry Box Widget
        server_label = Label(ssettings_frame, text='Server:')
        server_entry = Entry(ssettings_frame, textvariable=self.__server)
        server_label.grid(row=0, column=0, padx=4, pady=5)
        server_entry.grid(row=0, column=1, padx=4, pady=5)

        #   Apply User Pass Entry Box Widget
        database_label = Label(ssettings_frame, text='Database:')
        database_entry = Entry(ssettings_frame, textvariable=self.__database)
        database_label.grid(row=1, column=0, padx=4, pady=5)
        database_entry.grid(row=1, column=1, padx=4, pady=5)

        # Apply Buttons to the Buttons Frame
        #     Save button
        save_button = Button(self, text='Save', width=13, command=self.__save)
        save_button.pack(in_=buttons_frame, side=LEFT, padx=7, pady=7)

        #     Cancel button
        cancel_button = Button(self, text='Cancel', width=13, command=self.destroy)
        cancel_button.pack(in_=buttons_frame, side=RIGHT, padx=7, pady=7)
        
    def __save(self):
        if not self.__server:
            showerror('Field Empty Error!', 'No value has been inputed for Server', parent=self)
        elif not self.__database:
            showerror('Field Empty Error!', 'No value has been inputed for Database', parent=self)
        else:
            from . import Credentials

            self.__server_obj.encrypt(self.__server.get())
            self.__database_obj.encrypt(self.__database.get())
            self.destroy()


class SQLServerGUI(SSG):
    """
    SQL Server GUI that gathers Server & Database for basic SQL connections
    """

    def __init__(self, server=None, database=None):
        """
        :param server: Server in string format
        :param database: Database in string format
        """

        SSG.__init__(self, server=server, database=database)
        self.mainloop()
