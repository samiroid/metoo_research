from argparse import ArgumentParser
from itertools import product
import logging

import nltk
nltk.download("punkt", quiet = True)

from nltk.tokenize import word_tokenize
from sklearn.model_selection import train_test_split

from gensim.models.ldamulticore import LdaMulticore
from gensim import corpora
from gensim.utils import simple_preprocess
import numpy as np
import pandas as pd

from component_utils.general import create_artifact_folder

logger = logging.getLogger()

gridsearch_params = {
    "num_topics": np.arange(25, 200, 25),
    "decay": np.arange(0.5, 0.9, 0.1)
}

def go(args):
    artifact_path = create_artifact_folder(__file__)

    logger.info("Reading data...")
    data = pd.read_csv(args.input_path, sep = "\t", usecols = ["Full Text"])

    logger.info("Tokenizing data...")
    tokenized_data = [simple_preprocess(text) for text in data["Full Text"]]

    dictionary = corpora.Dictionary(tokenized_data)
    dictionary.filter_extremes(no_below = args.no_below, keep_n = args.vocab_size)

    logger.info("Creating corpus...")
    corpus = [dictionary.doc2bow(doc, allow_update=False) for doc in tokenized_data]

    logger.info("Splitting train/test corpus...")
    X_train, X_test = train_test_split(
        corpus, 
        random_state = args.random_state, 
        train_size = args.train_size
    )

    best_model, best_params, best_perp = None, None, np.inf

    for grid_params in dict(zip(gridsearch_params.keys(), product(*gridsearch_params.values()))):
        logger.info(f"Training model with params {grid_params}...")
        model = LdaMulticore(
            corpus = X_train, 
            id2word = dictionary, 
            random_state = args.random_state,
            **grid_params
        )
        
        model_perp = model.log_perplexity(X_test)
        if model_perp < best_perp:
            best_perp = model_perp
            best_params = grid_params
            best_model = model
    
    logger.info(f"Saving best model ({best_params}) to file...")
    best_model.save(artifact_path / "lda_model.model")
        
   

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("mode", type = str, help = "Run mode (local or remote)")
    parser.add_argument("input_path", type = str, help = "Path to input artifact")
    parser.add_argument("train_size", type = float, help = "Portion of data to use for training")
    parser.add_argument("random_state", type = int, help = "Seed for setting random state")   
    parser.add_argument("vocab_size", type = int, help = "Max # of tokens to include in corpus")
    parser.add_argument("no_below", type = int, help = "Min # of occurrences to include in corpus")  
    args = parser.parse_args()

    go(args)