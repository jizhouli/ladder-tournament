#! -*- coding:utf-8 -*-
"""
Zaih core
-------------

zaih 通用代码
"""
from setuptools import setup


setup(
    name='zaih-core',
    version='2017.10.20.00',
    url='http://git.iguokr.com/zaih/zaih-core',
    license='BSD',
    author='goodspeed',
    author_email='chengzongxiao@zaih.com',
    description='zaih 通用代码',
    long_description=__doc__,
    # py_modules=['zaih_core'],
    # if you would be using a package instead use packages instead
    # of py_modules:
    packages=['zaih_core'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'six',
        'Flask',
        'redis',
        'qrcode',
        'mockredispy==2.9.3',
        'pymemcache==1.3.3',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
