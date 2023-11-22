import setuptools

# Reads the content of your README.md into a variable to be used in the setup below
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name='chatvoice',                           # should match the package folder
    packages=['chatvoice'],                     # should match the package folder
    version='0.2,0',                                # important for updates
    license='GPL3',                                  # should match your chosen license
    description='Chatbot package',
    long_description=long_description,              # loads your README.md
    long_description_content_type="text/markdown",  # README.md is of type 'markdown'
    author='Ivan Vladimir Meza Ruiz',
    author_email='ivanvladimir@gmail.com',
    url='https://github.com/ivnvladimir/chatvoice', 
    project_urls = {                                # Optional
        "Bug Tracker": "https://github.com/ivanvladimir/chatvoice/issues"
    },
    install_requires=[
        'requests',
        'pyyaml',
        'tinydb',
        'arrow',
        'sqlalchemy',
        'rich',
        'click',
        'rich-click',
        'click-option-group',
        'pyttsx3',
        'numpy',
        'hypercorn[trio]',
        'uvicorn',
        'fastapi',
        'python-multipart',
        'qdrant-client',
        'pysqlite3',
        'jinja2',
        'aiofiles',
        'websockets',
        'websocket-client'
        ],                  # list all packages that your package uses
    keywords=["chatbot"], #descriptive meta-data
    classifiers=[                                   # https://pypi.org/classifiers
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Documentation',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
    entry_points='''
        [console_scripts]
        chatvoice=chatvoice.chatvoice:chatvoice
    ''',
    download_url="https://github.com/ivanvladimir/chatvoice/archive/refs/tags/0.2.0.tar.gz",
)
