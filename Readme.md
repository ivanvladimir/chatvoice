 Modificado por Alejandro
# chatvoice

A language for chatbots, uses ASR and TTS technology.


## Installation

### Requierements systems

The system uses pyaudio which needs: portaudio, libsound and mpg321, to install do the following:

    sudo apt-get install libasound-dev portaudio19-dev libportaudio2
    sudo apt install mpg321

### Instalation

Using pipenv

    pipenv install --ignore-pipfile

## Usage

Activate the shell

    pipenv shell


### Only terminal 

    python chatvoice.py conversations/hello_name.yaml

### Using ASR and TTS

    python  chatvoice.py conversations/hello_name.yaml --rec_voice --google_tts

Resulting in this:

    HAL: buen día
    HAL: ¿cúal es tu nombre?
    USER: Jesús
    HAL: mucho gusto en conocerte
    HAL: adios Jesús
    Summary values:
    name Jesús

### Obtaining help

    python chatvoice.py conversations/hello_name.yaml --help
