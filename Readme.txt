# chatvoice

A language for chatbots, uses ASR and TTS technology.

## Installation

### Requierements systems

The system uses pyaudio which needs: portaudio, libsound and mpg321, to install do the following:

`sudo apt-get install libasound-dev portaudio19-dev libportaudio2`
`sudo apt install mpg321`

### Instalation

Using pipenv

`pipenv install --ignore-pipfile`

## Usage

Activate the shell

`pipenv shell`


### Only therminal 

`python chatvoice.py conversations/hello_name.yaml`

### Using ASR and TTS

``

### Obtaining help

`python chatvoice.py conversations/hello_name.yaml --help`
