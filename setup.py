from setuptools import find_packages, setup

setup(
    name='themylog',
    version='0.0.0',
    author='themylogin',
    author_email='themylogin@gmail.com',
    packages=find_packages(exclude=["tests"]),
    scripts=[],
    test_suite="nose.collector",
    url='http://github.com/themylogin/themylog',
    description='Human-readable logging facility',
    long_description=open('README.md').read(),
    install_requires=[
        "celery",
        "isodate",
        "python-dateutil",
        "pyyaml",
        "themyutils",
        "threadpool",
        "werkzeug",
        "zope.interface >= 4.0.5",

        "mock",
        "nose>=1.0",
        "requests",
        "sqlalchemy",
        "testfixtures",
        "tl.testing",
        "websocket-client",
    ],
    dependency_links=[
        "https://github.com/themylogin/themyutils/archive/master.zip#egg=themyutils",
    ],
)
