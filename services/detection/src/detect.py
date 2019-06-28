"""
Detect objects over pages
"""

import pymongo
from pymongo import MongoClient
import os
import logging
import datetime
logging.basicConfig(format='%(levelname)s :: %(asctime)s :: %(message)s', level=logging.DEBUG)
import time
import io
from preprocess import pad_image
from typing import Mapping, TypeVar, Callable
import base64
from infer import run_inference

T = TypeVar('T')

def detect() -> None:
    """
    On event trigger, run the proposals script
    """
    logging.info('Starting detection over papers')
    start_time = time.time()
    client = MongoClient(os.environ["DBCONNECT"])
    logging.info(f'Connected to client: {client}. Setting watch on cc_pdfs collection')
    db = client.pdfs
    # Open a cursor that will watch for inserts on cc_pdfs
    try:
        with db.cc_pdfs.watch([{'$match': {'operationType': 'insert'}}]) as stream:
            for doc in stream:
                full = doc['fullDocument']
                process_doc(full, mongo_insert_fn, client)
    except pymongo.errors.PyMongoError as err:
        logging.error("Error in pymongo:")
        logging.error(err)

    end_time = time.time()
    logging.info(f'Exiting proposal generation. Time up: {end_time - start_time}')

def get_page_bytes(client, pdf_id, page_num):
    """
    TODO: Docstring for get_page_bytes.

    Args:
        pdf_id (TODO): TODO
        page_no (TODO): TODO

    Returns: TODO

    """
    db = client.pdfs
    pages = db.pages
    result = pages.find_one({"pdf_id" : pdf_id, "page_num" : page_num})
    bytesio = io.BytesIO(result['resize_bytes'])
    return bytesio

def process_doc(full: Mapping[T, T], db_insert_fn: Callable[[Mapping[T, T], T], None], client: T, config_pth: str = 'model_config.yaml', weights_pth: str = 'model_weights.pth') -> Mapping[T, T]:
    logging.info('Document found and added to queue')

    page_data = full['page_data']
    # loop over pages once to prep them for inference
    for page in page_data:
        bytesio = get_page_bytes(client, full["_id"], page["page_num"])
        img = pad_image(bytesio)
        padded_bytes_stream = io.BytesIO()
        img.save(padded_bytes_stream, format='PNG')
        padded_bytes = padded_bytes_stream.getvalue()
        page['padded_bytes'] = padded_bytes
    print('test running inference')
    detected_objs = run_inference(page_data, config_pth, weights_pth, os.environ["DEVICE"], pdf_name=full['pdf_name'])
    # loop over pages again to map detected objects back into the pages to be written.
    for page in page_data:
        page_num = page['page_num']
        page_num = str(page_num)
        if page_num not in detected_objs:
            logging.info(f"No detected objects for {full['pdf_name']} on page {page_num}")
            page['detected_objs'] = []
            continue
        objs = detected_objs[page_num]
        page['detected_objs'] = objs
        del page["padded_bytes"]

    full['event_stream'].append('detection')
    db_insert_fn(full, client)
    return full


def mongo_insert_fn(obj: Mapping[T, T], client: T) -> None:
    db = client.pdfs
    detect_pdfs = db.detect_pdfs
    result = detect_pdfs.insert_one(obj)
    logging.info(f"Inserted result: {result}")


if __name__ == '__main__':
    detect()


