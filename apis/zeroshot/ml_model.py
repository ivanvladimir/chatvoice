from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

model = None

def init_transformer(model_name, tokenizer=None):
    global model

    if tokenizer is None:
        tokenizer = model_name

    tokenizer = AutoTokenizer.from_pretrained(tokenizer)
    model__ = AutoModelForSequenceClassification.from_pretrained(model_name)

    labeler = pipeline("zero-shot-classification", model=model__, tokenizer=tokenizer)
    model = labeler
    return model


def pre_process(text, candidate_labels, hypothesis_template, use_lower=True):
    # If transform to lower
    if use_lower:
        text = text.lower()
        candidate_labels = [l.lower() for l in candidate_labels]
        hypothesis_template = hypothesis_template

    return text, candidate_labels, hypothesis_template


def classify_transformer(text, candidate_labels, hypothesis_template, **args):
    global model

    text_, candidate_labels_, hypothesis_template_ = pre_process(text, 
            candidate_labels, 
            hypothesis_template,
            **args)
    res = model(text_,
            candidate_labels=candidate_labels_,
            hypothesis_template=hypothesis_template_
            )
    return res, (text_, candidate_labels_, hypothesis_template)

def labelling_transformer(text, candidate_texts, candidate_labels, **args):
    global model

    text_, candidate_texts_, hypothesis_template_ = pre_process(text, 
            candidate_texts, 
            '{}',
            **args)
    res = model(text_,
            candidate_labels=candidate_texts_,
            hypothesis_template=hypothesis_template_
            )

    results=dict(zip(candidate_texts_,candidate_labels))
    return results[res['labels'][0]], (text_, candidate_texts_, candidate_labels)
