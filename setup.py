from setuptools import setup


if __name__ == '__main__':
    setup(
        name='KGlobal',
        version='1.6.3.2',
        author='Kevin Russell',
        packages=['KGlobal', 'KGlobal.data', 'KGlobal.sql', 'KGlobal.reader'],
        # py_modules=['KGlobal'],
        url='https://github.com/KLRussell/Python_KGlobal_Package',
        description='SQL Handling, Object Shelving, Data Encryption, ETL File Handler, E-mail Parsing, Logging',
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
            'xlrd',
            'XlsxWriter',
            'Xlwt',
            'Openpyxl',
            'django',
            'openpyxl',
            'odfpy',
            'pyxlsb'
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
