# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.

# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


import os
import glob
import argparse
import hashlib
import json

from typing import Optional
from multiprocessing import Pool
from tqdm import tqdm


SHA256S_FILE = os.path.join(os.path.dirname(__file__), "co3d_sha256.json")
BLOCKSIZE = 65536


def main(download_folder: str, dump: bool = False, n_sha256_workers: int = 4):
    zipfiles = sorted(glob.glob(os.path.join(download_folder, "*.zip")))
    print(f"Extracting SHA256 hashes for {len(zipfiles)} files in {download_folder}.")
    extracted_sha256s_list = []
    with Pool(processes=n_sha256_workers) as download_pool:
        for extracted_hash in tqdm(
            download_pool.imap(sha256_file, zipfiles),
            total=len(zipfiles),
        ):
            extracted_sha256s_list.append(extracted_hash)
            pass

    # dict {zipname: sha256}
    extracted_sha256s = dict(
        zip([os.path.split(z)[-1] for z in zipfiles], extracted_sha256s_list)
    )

    if dump:
        print(extracted_sha256s)
        with open(SHA256S_FILE, "w") as f:
            json.dump(extracted_sha256s, f, indent=2)

    expected_sha256s = get_expected_sha256s()

    missing_keys, invalid_keys = [], []
    for k in expected_sha256s.keys():
        if k not in extracted_sha256s:
            print(f"{k} missing!")
            missing_keys.append(k)
        elif expected_sha256s[k] != extracted_sha256s[k]:
            print(
                f"'{k}' does not match!"
                + f" ({expected_sha256s[k]} != {extracted_sha256s[k]})"
            )
            invalid_keys.append(k)
    if len(invalid_keys) + len(missing_keys) > 0:
        raise ValueError(
            f"Checksum checker failed!"
            + f" Non-matching checksums: {str(invalid_keys)};"
            + f" missing files: {str(missing_keys)}."
        )


def get_expected_sha256s(single_sequence_subset: bool = False):
    with open(SHA256S_FILE, "r") as f:
        expected_sha256s = json.load(f)
    if single_sequence_subset:
        return expected_sha256s["singlesequence"]
    else:
        return expected_sha256s["full"]


def check_co3d_sha256(
    path: str,
    expected_sha256s: Optional[dict] = None,
    single_sequence_subset: bool = False,
):
    zipname = os.path.split(path)[-1]
    if expected_sha256s is None:
        expected_sha256s = get_expected_sha256s(single_sequence_subset)
    extracted_hash = sha256_file(path)
    assert (
        extracted_hash == expected_sha256s[zipname]
    ), f"{extracted_hash} != {expected_sha256s[zipname]}"


def sha256_file(path: str):
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        file_buffer = f.read(BLOCKSIZE)
        while len(file_buffer) > 0:
            sha256_hash.update(file_buffer)
            file_buffer = f.read(BLOCKSIZE)
    digest_ = sha256_hash.hexdigest()
    # print(f"{digest_} {path}")
    return digest_


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check SHA256 hashes of the CO3D dataset."
    )
    parser.add_argument(
        "--download_folder",
        type=str,
        help="A local target folder for downloading the the dataset files.",
    )
    parser.add_argument(
        "--num_workers",
        type=int,
        default=4,
        help="The number of sha256 extraction workers.",
    )
    parser.add_argument(
        "--dump_sha256s",
        action="store_true",
        help="Store sha256s hashes.",
    )
    args = parser.parse_args()
    main(
        str(args.download_folder),
        dump=bool(args.dump_sha256s),
        n_sha256_workers=int(args.num_workers),
    )
