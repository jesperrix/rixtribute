from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="rixtribute",
    version="0.0.1",

    description="orchestra distribution of long running tasks",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Jesper Rix",
    author_email="rixjesper@gmail.com",

    classifiers=[  # Optional
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Utilities',

        # Pick your license as you wish
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        # These classifiers are *not* checked by 'pip install'. See instead
        # 'python_requires' below.
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],

    packages=find_packages(include=["rixtribute", "rixtribute.*"], exclude=[]),
    # packages=["rixtribute"],

    install_requires=[open("requirements.txt").read().strip().split("\n")],

    python_requires=">=3.6",

    entry_points = {
        "console_scripts": ['rxtb = rixtribute.cli:main']
    }
)
