# Web APIs to connect with chatvoice

These APIs can be called from chatvoice to perform a specific task

## Install

Create enviroment in _env_ directory (change given your preference)

    python3 -m venv env

## Install libraries

Install most of the necessary libraries

    pip install -r requirements.txt

Most of the APIs use [_transformer
library_](https://huggingface.co/docs/transformers/index) which can use
[_pytorch_](https://pytorch.org/get-started/locally/),
[_tensorflor_](https://www.tensorflow.org/install/pip) or
[_flax_](https://flax.readthedocs.io/en/latest/), install your favorite. In particular,
most of the test were done with _pytorch_  


## Execution

Go into the directory of the API and type run the following command

    uvicorn api:app

If want to use a particular configuration check _env_ files and run with this
option (replace, ENV.FILE for right file)

    uvicorn api:app --env-file ENV.FILE

# Available APIs

demo            A demo API that mirrows mesages
classification  Performs classification from a model of the _transformer_
library, check options
[here](https://huggingface.co/models?pipeline_tag=text-classification&sort=downloads)
for Spanish ones
[here](https://huggingface.co/models?language=es&pipeline_tag=text-classification&sort=downloads)


