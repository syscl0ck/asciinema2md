#!/usr/bin/env python3
"""Setup script for asciinema2md."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="asciinema2md",
    version="0.1.0",
    author="",
    description="Convert asciinema cast files to Markdown format",
    long_description=long_description,
    long_description_content_type="text/markdown",
    py_modules=["asciinema2md"],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "asciinema2md=asciinema2md:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

