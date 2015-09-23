from setuptools import setup

setup(
    name="i8c",
    version="0.0.1",
    packages=["i8c"],
    entry_points={"console_scripts": ["i8c = i8c:run_compiler"]})
