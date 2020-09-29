
# Chatvoice

A language for chatbots, uses Text-To-Speech (TTS) y Automatic Speech Recognition (ASR)  technology.

## Requierements systems

[Anaconda or Miniconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/download.html#hash-verification)

## Installation

Once the repository is cloned, open Anaconda Prompt and go to the cloned repository path.

Open the environment.yml file and delete the lines:

- cpuonly=1.0
- pytorch=1.6.0
- torchvision=0.7.0

we will create the environment

    $ conda env create -f environment.yml

If everything goes well in the creation of the environment, a message like this should appear:

```
To activate this environment, use

     $ conda activate cv

To deactivate an active environment, use

     $ conda deactivate
```

To verify that the environment was created, verify the list of conda environments with the command:

     $ conda info --envs

Should show:

```
conda environments:

base */home/user/anaconda3
cv /home/user/anaconda3/envs/cv
```

Where can we locate the created cv environment which we are going to activate

    $ conda activate cv

let's update the environment 

    $ conda env update -f environment.yml

## Usage

- **Without audio**

```
python src/chatvoice.py conversations hello_name/main.yaml
```

- **With google synthesis**

You have to install mpg321

```
sudo apt install mpg321
```

Run

```
python src/chatvoice.py conversations/hello_name/main.yaml --google_tts
```

Resulting in this:

    ROBOT: hola
    ROBOT: ¿cúal es tu nombre?
    USER: Jorge
    ROBOT: mucho gusto en conocerte
    ROBOT: ¿como estás hoy Jorge?
    USER: Bien!
    ROBOT: Hay algunas cosas que se
    ROBOT: hecho benito juarez nacio en un 21 marzo
    ROBOT: adios Jorge

### Obtaining help

    python src/chatvoice.py conversations/hello_name.yaml --help
