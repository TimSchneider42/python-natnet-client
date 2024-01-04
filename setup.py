import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="natnet-client",
    version="0.1.1",
    author="Tim Schneider",
    author_email="schneider@ias.informatik.tu-darmstadt.de",
    description="Python client for Optitrack NatNet streams.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TimSchneider42/python-natnet-client",
    project_urls={
        "Bug Tracker": "https://github.com/TimSchneider42/python-natnet-client/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=["natnet_client"],
    python_requires=">=3.6",
)