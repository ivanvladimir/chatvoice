from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

model=None

def init_transformer(model_name,tokenizer=None):
    global model

    if tokenizer is None:
        tokenizer=model_name

    tokenizer = AutoTokenizer.from_pretrained(tokenizer)
    model__ = AutoModelForSequenceClassification.from_pretrained(model_name)

    labeler=pipeline('text-classification', model=model__, tokenizer=tokenizer)
    model=labeler
    return model


def pre_process(text, use_lower=True):
    # If transform to lower
    if use_lower:
        text=text.lower()

    return text

def classify_transformer(
        text, 
        **args):
    global model

    text_=pre_process(text,**args)
    res=model(text_)[0]
    return res, text_
