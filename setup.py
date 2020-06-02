from setuptools import setup


if __name__ == '__main__':
    setup(
        name='KGlobal',
        version='1.3.3',
        author='Kevin Russell',
        packages=['KGlobal', 'KGlobal.data', 'KGlobal.sql'],
        # py_modules=['KGlobal'],
        url='https://github.com/KLRussell/Python_KGlobal_Package',
        description='SQL Handling, Object Shelving, Data Encryption, XML Parsing/Writing, E-mail Parsing, Logging',
        install_requires=[
            'pandas',
            'future',
            'sqlalchemy',
            'pyodbc',
            'portalocker',
            'cryptography',
            'independentsoft.msg',
            'exchangelib',
            'bs4',
            'six',
        ],
        package_data={
            "": ["*.txt", "*.md"],
        },
        entry_points={
            'console_scripts': [
                'KGlobal = KGlobal.main:main',
            ]
        },
        zip_safe=False,
    )
