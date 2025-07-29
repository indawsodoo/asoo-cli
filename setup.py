# setup.py
from setuptools import setup, find_packages

setup(
    name='incloud-cli',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
        'PyYAML>=6.0',
        'colorlog>=6.7.0',
        'python-dotenv>=1.0.0',
        'GitPython>=3.1.45',
    ],
    entry_points={
        'console_scripts': [
            'incloud = asoo_cli:asoo_cli',
        ],
    },
    author='David Gómez',
    author_email='david.gomez@indaws.es',
    description='A modular CLI tool for inDAWs Cloud projects.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/incloud/cli',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Version Control :: Git',
        'Topic :: System :: Systems Administration',
    ],
    python_requires='>=3.8',
)
