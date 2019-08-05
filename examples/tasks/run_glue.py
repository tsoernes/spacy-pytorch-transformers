import plac
import random
import torch
import spacy
import spacy.util
import tqdm 
import numpy
from spacy.gold import GoldParse

from collections import Counter
from pathlib import Path
from spacy.util import minibatch

from spacy_pytorch_transformers.util import warmup_linear_rates
from spacy_pytorch_transformers._extra.hyper_params import get_hyper_params
from spacy_pytorch_transformers._extra.glue_tasks import read_train_data, read_dev_data
from spacy_pytorch_transformers._extra.glue_tasks import describe_task
from spacy_pytorch_transformers._extra.metrics import compute_metrics


def create_model(model_name, *, task_type, task_name, labels):
    nlp = spacy.load(model_name)
    textcat = nlp.create_pipe("pytt_textcat", config={
        "architecture": HP.textcat_arch})
    for label in labels:
        textcat.add_label(label)
    nlp.add_pipe(textcat)
    optimizer = nlp.resume_training()
    optimizer.alpha = HP.learning_rate
    optimizer.max_grad_norm = HP.max_grad_norm
    optimizer.eps = HP.adam_epsilon
    return nlp, optimizer


def train_epoch(nlp, optimizer, train_data):
    # This isn't the recommended code -- but it's the easiest way to do the
    # experiment for now.
    global HP
    random.shuffle(train_data)
    batches = minibatch(train_data, size=HP.batch_size)
    tok2vec = nlp.get_pipe("pytt_tok2vec")
    textcat = nlp.get_pipe("pytt_textcat")
    for batch in batches:
        docs, golds = zip(*batch)
        tokvecs, backprop_tok2vec = tok2vec.begin_update(docs, drop=HP.dropout)
        losses = {}
        tok2vec.set_annotations(docs, tokvecs)
        textcat.update(docs, golds, sgd=optimizer, losses=losses)
        backprop_tok2vec(docs, sgd=optimizer)
        yield batch, losses
        for doc in docs:
            free_tensors(doc)


def evaluate(nlp, task, docs_golds):
    tok2vec = nlp.get_pipe("pytt_tok2vec")
    textcat = nlp.get_pipe("pytt_textcat")
    right = 0
    total = 0
    guesses = []
    truths = []
    labels = textcat.labels
    for batch in minibatch(docs_golds, size=HP.eval_batch_size):
        docs, golds = zip(*batch)
        docs = list(textcat.pipe(tok2vec.pipe(docs)))
        for doc, gold in zip(docs, golds):
            guess, _ = max(doc.cats.items(), key=lambda it: it[1])
            truth, _ = max(gold.cats.items(), key=lambda it: it[1])
            guesses.append(labels.index(guess))
            truths.append(labels.index(truth))
            right += guess == truth
            total += 1
            free_tensors(doc)
    metrics = compute_metrics(
        task, numpy.array(guesses), numpy.array(truths))
    metrics["accuracy"] = right / total
    metrics["right"] = right
    metrics["total"] = total
    return metrics


def process_data(nlp, task, examples):
    """Set-up Doc and GoldParse objects from the examples. This makes it easier
    to set up text-pair tasks, and also easy to handle datasets with non-real
    tokenization."""
    wordpiecer = nlp.get_pipe("pytt_wordpiecer")
    textcat = nlp.get_pipe("pytt_textcat")
    docs = []
    golds = []
    for eg in examples:
        assert "\n" not in eg.text_a
        assert "\n" not in eg.text_b
        doc = nlp.make_doc(eg.text_a + "\n" + eg.text_b)
        # Set "sentence boundary"
        for token in doc:
            if token.text == "\n":
                token.is_sent_start = True
        doc = wordpiecer(doc)
        for token in doc[1:]:
            token.is_sent_start = False
        cats = {label: 0.0 for label in textcat.labels}
        cats[eg.label] = 1.0
        gold = GoldParse(doc, cats=cats)
        docs.append(doc)
        golds.append(gold)
    return list(zip(docs, golds))


def free_tensors(doc):
    doc.tensor = None
    doc._.pytt_last_hidden_state = None
    doc._.pytt_pooler_output = None
    doc._.pytt_all_hidden_states = []
    doc._.pytt_all_attentions = []
    doc._.pytt_d_last_hidden_state = None
    doc._.pytt_d_pooler_output = None
    doc._.pytt_d_all_hidden_states = []
    doc._.pytt_d_all_attentions = []


def print_progress(losses, scores):
    print("Losses", losses)
    print("Scores", scores)


def main(
    model_name: ("Model package", "positional", None, str),
    task: ("Task name", "positional", None, str),
    data_dir: ("Path to data directory", "positional", None, Path),
    output_dir: ("Path to output directory", "positional", None, Path),
    hyper_params: ("Path to hyper params file", "positional", None, Path) = None,
    dont_gpu: ("Dont use GPU, even if available", "flag", "G") = False,
):
    global HP
    HP = get_hyper_params(hyper_params)

    spacy.util.fix_random_seed(HP.seed)
    torch.manual_seed(HP.seed)
    if not dont_gpu:
        is_using_gpu = spacy.prefer_gpu()
        print("Use gpu?", is_using_gpu)
        if is_using_gpu:
            torch.set_default_tensor_type("torch.cuda.FloatTensor")

    print("Procress training data")
    raw_train_data = read_train_data(data_dir, task)
    raw_dev_data = read_dev_data(data_dir, task)
    nlp, optimizer = create_model(model_name, **describe_task(task))
    train_data = process_data(nlp, task, raw_train_data)
    dev_data = process_data(nlp, task, raw_dev_data)

    nr_batch = len(train_data) // HP.batch_size
    nr_step = nr_batch * HP.num_train_epochs
    learn_rates = warmup_linear_rates(HP.learning_rate, HP.warmup_steps, nr_step)
    optimizer.alpha = next(learn_rates)
    progress_bar = lambda func: tqdm.tqdm(func, total=nr_batch)
    print("Training. Initial learn rate:", optimizer.alpha)
    for i in range(HP.num_train_epochs):
        # Train and evaluate
        losses = Counter()
        for batch, loss in progress_bar(train_epoch(nlp, optimizer, train_data)):
            losses.update(loss)
            optimizer.alpha = next(learn_rates)
        accuracies = evaluate(nlp, task, dev_data)
        print_progress(losses, accuracies)


if __name__ == "__main__":
    plac.call(main)