import hashlib
import os
import struct
from typing import Dict

block_size = 2 ** 16
min_file_size = block_size * 2
longlong_format = '<q'  # little-endian long long
longlong_size = struct.calcsize(longlong_format)
longlong_per_block = int(block_size / longlong_size)
block_mask = 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number


def read_longlong(file_handle):
    buf = file_handle.read(longlong_size)
    (l_value,) = struct.unpack(longlong_format, buf)
    return l_value


def hash_block(file_handle, current_hash):
    for _ in range(longlong_per_block):
        current_hash += read_longlong(file_handle)
        current_hash &= block_mask
    return current_hash


def hash_file(file_path):
    """
    Create a hash of movie title (file name)
    See: https://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes
    :param file_path: The URI of the movie file
    :return: tuple (hash, size)
    """
    file_size = os.path.getsize(file_path)

    if file_size < min_file_size:
        raise Exception("Hash: file must be larger than two blocks (%s)" % min_file_size)

    file_hash = file_size
    last_block = max(0, file_size - block_size)

    with open(file_path, "rb") as f:
        for hash_place in [0, last_block]:
            f.seek(hash_place, os.SEEK_SET)
            if f.tell() != hash_place:
                raise Exception("Hash: Failed to seek to %s" % hash_place)
            file_hash = hash_block(f, file_hash)

    returned_hash = "%016x" % file_hash
    return returned_hash, file_size


def hash_query(query_data: Dict[str, str]):
    m = hashlib.sha256()
    for k in sorted(query_data):
        m.update(k.encode('utf8'))
        m.update(query_data[k].encode('utf8'))
    return m.hexdigest()
