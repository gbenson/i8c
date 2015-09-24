from setuptools import setup

setup(
    name="i8c",
    version="0.0.1",
    description="GNU Infinity note compiler",
    #XXX long_description
    #XXX and classifiers
    #XXX see https://github.com/pypa/sampleproject/blob/master/setup.py
    license="GPLv3+",
    author="Gary Benson",
    author_email="gbenson@redhat.com",
    url="https://github.com/gbenson/i8c",
    packages=["i8c"],
    entry_points={"console_scripts": ["i8c = i8c:run_compiler"]})
