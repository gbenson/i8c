from setuptools import setup

setup(
    name="i8c",
    version="0.0.1",
    description="GNU Infinity note compiler",
    #XXX long_description
    #XXX see https://github.com/pypa/sampleproject/blob/master/setup.py
    license="GPLv3+",
    author="Gary Benson",
    author_email="gbenson@redhat.com",
    url="https://github.com/gbenson/i8c",
    classifiers=[
        # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved" +
            " :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Compilers",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
    ],
    packages=["i8c"],
    entry_points={"console_scripts": ["i8c = i8c.compiler:main"]},
    tests_require=["nose"],
    test_suite="nose.collector")
