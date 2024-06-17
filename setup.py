from setuptools import setup

setup(
    name='katottglib',
    version='0.3.1',
    packages=['katottglib'],
    install_requires=[
        'pandas',
        'openpyxl',
    ],
    author='Denis Senchishen',
    author_email='dsenchishen@icloud.com',
    description='A Python lib to operate KATOTTG addresses (classified administrative division of Ukraine).',
    url='https://github.com/sen-den/katottglib',
)
