import re
from setuptools import setup
import sys


sys.path.append("./piexif")
sys.path.append("./tests")

with open("README.rst", "r") as f:
    description = f.read()

with open("piexif/__init__.py", "r") as f:
    version_match = re.search(r'^VERSION = "([^"]+)"$', f.read(), re.MULTILINE)
if version_match is None:
    raise RuntimeError("Could not find package version.")

setup(
    name="piexif-fork",
    version=version_match.group(1),
    author="hMatoba",
    author_email="hiroaki.mtb@outlook.com",
    description="To simplify exif manipulations with python. "
    + "Writing, reading, and more...",
    long_description=description,
    license="MIT",
    keywords=["exif", "jpeg"],
    url="https://github.com/Dobatymo/Piexif",
    packages=["piexif"],
    package_data={"piexif": ["*.pyi", "py.typed"]},
    install_requires=["typing; python_version < '3.5'"],
    test_suite="s_test.suite",
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: IronPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "License :: OSI Approved :: MIT License",
        "Topic :: Multimedia",
        "Topic :: Printing",
    ],
)
