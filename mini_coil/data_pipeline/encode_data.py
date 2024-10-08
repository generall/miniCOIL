"""
This script takes raw training data and applies initial embeddings to it.

The output of the process, for each abstract:

* List of token ids
* List of per-token embeddings
* Aggregate embedding of the abstract

This script can potentially generate huge amounts of data, so
it will write directly to disk.

"""

import os
from typing import Iterable
import argparse

import numpy as np
import tqdm
from npy_append_array import NpyAppendArray

from mini_coil.data_pipeline.pre_encoder import PreEncoder
from mini_coil.settings import DATA_DIR
from mini_coil.data_pipeline.vocab_resolver import VocabResolver


def read_texts(path: str) -> Iterable[str]:
    with open(path, "r") as f:
        for line in tqdm.tqdm(f):
            line = line.strip()
            if len(line) > 0:
                yield line


def iter_batch(iterable, size):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if len(batch) > 0:
        yield batch


def main():
    input_file = "bat.txt"

    default_input_data_path = os.path.join(DATA_DIR, "test", input_file)
    default_output_dir = os.path.join(DATA_DIR, "test")
    default_vocab_path = os.path.join(DATA_DIR, "test", "vocab.txt")

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", type=str, default=default_input_data_path)
    parser.add_argument("--output-dir", type=str, default=default_output_dir)
    parser.add_argument('--vocab-path', type=str, default=default_vocab_path)
    args = parser.parse_args()

    model_repository = "sentence-transformers/all-MiniLM-L6-v2"
    model_save_path = os.path.join(DATA_DIR, "all_miniLM_L6_v2.onnx")

    vocab_path = args.vocab_path

    batch_size = 32

    pre_encoder = PreEncoder(model_repository, model_save_path)

    vocab_resolver = VocabResolver(model_repository)
    vocab_resolver.load_vocab(vocab_path)

    total_token_emb_offset = 0
    offsets = [0]

    output_dir = args.output_dir

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    token_np_emb_file = NpyAppendArray(
        os.path.join(output_dir, "token_embeddings.npy"),
        delete_if_exists=True
    )
    text_np_emb_file = NpyAppendArray(
        os.path.join(output_dir, "text_embeddings.npy"),
        delete_if_exists=True
    )
    tokens_np_file = NpyAppendArray(
        os.path.join(output_dir, "tokens.npy"),
        delete_if_exists=True
    )
    offsets_file = os.path.join(output_dir, "offsets.npy")

    for batch in iter_batch(read_texts(args.input_file), batch_size):
        batch_output = pre_encoder.encode(batch)

        batch_offsets, flattened_vocab_ids, flattened_token_embeddings = vocab_resolver.filter(
            batch_output["token_ids"],
            batch_output["token_embeddings"]
        )

        tokens_np_file.append(flattened_vocab_ids)
        token_np_emb_file.append(flattened_token_embeddings)
        text_np_emb_file.append(batch_output["text_embeddings"])

        for row_id, offset in enumerate(batch_offsets):
            global_offset = total_token_emb_offset + offset
            offsets.append(global_offset)
            total_token_emb_offset = global_offset

    offsets = np.array(offsets)

    np.save(offsets_file, offsets)

    token_np_emb_file.close()
    text_np_emb_file.close()
    tokens_np_file.close()

    print(total_token_emb_offset)


if __name__ == "__main__":
    main()
