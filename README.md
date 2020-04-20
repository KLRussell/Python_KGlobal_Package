Welcome to KGlobal, This is a combination tool that combines object shelving, SHA256 encryption, SQL queuing & threading, Exchangelib quick connect, and Exchangelib to .MSG parsing
Please feel free to edit or modify the code if it can help provide a better package.

Please see help(KGlobal) after importing KGlobal. Uses....

KGlobal:
	* Toolbox (script_path) - Creates a DataConfig instance for Main Settings and Local Settings plus is created as a child class of SQLQueue & LogHandle instances
		- This class will allow you to multi-thread sql alchemy or pyodbc connections on the for the same connection string

	* Credentials - Simple class instance to store username & password that is encrypted with CryptHandle

	* ExchangeToMsg - Converts an Exchangelib's item message to an independentsoft.msg object, which you can save as an .MSG file

	* XML - Simple class to read & write XML into a dataframe

 
KGlobal.data:

	* DataConfig - Creates an dict like object that syncs to file format whenever user manually calls sync() function. Data saved to file format is double encrypted

	* CryptHandle - Instance to store an encrypted object, string, or numeric value

	* SaltHandle - Instance to generate or store a salt key

KGlobal.sql

	* SQLConfig - Configuration class that allows you to generate a sql connection string or allow a custom sql connection string to be used

	* SQLQueue - SQL Queue class that allows you to queue multiple SQLEngineClasses. Caching is involved with this class

	* SQLEngineClass - SQL Engine class that is used to multi-thread multiple connections for a singular connection string. Results, Errors, and command /w params stored in a class

To Install:

1) Type 'pip install KGlobal' in powershell

2) Type 'KGlobal -c' to install Master Salt Key

3) Enjoy!

