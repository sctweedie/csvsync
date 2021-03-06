import setuptools
import fastentrypoints

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="csvsync",
    version="0.1",
    author="Stephen Tweedie",
    author_email="sct@redhat.com",
    description="CSV-to-google-sheet 3-way sync utility",
    long_description=long_description,
    long_description_content_type="text/markdown",
#   url="https://github.com/pypa/example-project",
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'csvsync = csvsync:cli.cli_entrypoint'
        ],
    },
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
