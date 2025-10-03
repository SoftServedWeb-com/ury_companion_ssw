from setuptools import setup, find_packages
from ury_companion_ssw import __version__ as version

with open("requirements.txt") as f:
	install_requires = f.read().strip().splitlines()

setup(
    name="ury_companion_ssw",
    description="Adds more functions to ury",
    author="Soft Served Web",
    author_email="aswin@softservedweb.com",
    version=version,
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)