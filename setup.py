from setuptools import setup

setup(
    name='katottglib',
    version='0.2.5',
    packages=['katottglib'],
    install_requires=[
        'pandas~=2.0.0',
        'openpyxl~=3.1.0',
    ],
    author='Denis Senchishen',
    author_email='dsenchishen@icloud.com',
    description='A Python lib to operate KATOTTG addresses (classified administrative division of Ukraine).',
    url='https://github.com/sen-den/katottglib',
)
