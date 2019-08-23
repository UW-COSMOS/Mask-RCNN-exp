"""
Aggregate text blobs into coherent sections
"""

import logging
import time
import os
logging.basicConfig(format='%(levelname)s :: %(asctime)s :: %(message)s', level=logging.DEBUG)
import pymongo
from pymongo import MongoClient
from collections import defaultdict
from joblib import Parallel, delayed
import click

MIN_SECTION_LEN = 30


def load_pages(db, buffer_size):
    current_docs = []
    for doc in db.raw_pdfs.find(no_cursor_timeout=True):
        # Find all objects
        pdf_name = doc['pdf_name']
        obj_list = []
        for obj in db.ocr_objs.find({'pdf_name': pdf_name}, no_cursor_timeout=True):
            del obj['bytes']
            obj_list.append(obj)
        current_docs.append(obj_list)
        if len(current_docs) == buffer_size:
            yield current_docs
            current_docs = []
    yield current_docs


def groups(pobjs):
    groups = []
    for p in pobjs:
        bb = p['bounding_box']
        x1, y1, x2, y2 = bb
        inserted = False
        for group in groups:
            gx1 = group[0]
            if gx1-50 <= x1 <= gx1+50:
                group[1].append(p)
                inserted = True
                break
        if not inserted:
            groups.append([x1, [p]])
    for g in groups:
        # sort internally by y
        g[1].sort(key=lambda x: x['bounding_box'][1])
    # Sort bins by x
    groups.sort(key=lambda x: x[0])
    return groups


def aggregate_sections(objs):
    def filter_fn(obj):
        return obj['class'] in ['Body Text', 'Section Header']

    fobjs = [o for o in objs if filter_fn(o)]
    pages = defaultdict(list)
    for obj in fobjs:
        pages[obj['page_num']].append(obj)
    keys = pages.keys()
    if len(keys) == 0:
        # Probably should log something here
        return []
    max_len = max(keys)
    sections = []
    for i in range(max_len):
        if i not in pages:
            continue
        page_objs = pages[i]
        grouped = groups(page_objs)
        current_section = None
        for group in grouped:
            for obj in group[1]:
                if obj['class'] == 'Section Header':
                    current_section = obj
                    sections.append([obj, []])
                    continue
                if current_section is None:
                    if len(sections) == 0:
                        sections.append([None, [obj]])
                        continue
                sections[-1][1].append(obj)
    aggregated = []
    final_objs = []
    for section in sections:
        header, objs = section
        aggregated_context = ''
        pdf_name = ''
        if header is not None:
            aggregated_context = f'{header["content"]}\n'
            pdf_name = header['pdf_name']
        else:
            pdf_name = objs[0]['pdf_name']
        for obj in objs:
            aggregated_context += f'\n{obj["content"]}\n'
        if aggregated_context.strip() == '' or len(aggregated_context.strip()) < MIN_SECTION_LEN:
            continue
        objs = [{'_id': obj['_id']} for obj in objs]
        final_obj = {'header': header,
                     'objects': objs,
                     'content': aggregated_context,
                     'class': 'Section'
                     'pdf_name': pdf_name}
        final_objs.append(final_obj)
    return final_objs


def section_scan(db_insert_fn, num_processes):
    logging.info('Starting section extraction over objects')
    start_time = time.time()
    client = MongoClient(os.environ['DBCONNECT'])
    logging.info(f'Connected to client: {client}')
    db = client.pdfs
    for batch in load_pages(db, num_processes):
        logging.info('Batch constructed. Running section aggregation')
        objs = Parallel(n_jobs=num_processes)(delayed(aggregate_sections)(o) for o in batch)
        objs = [o for p in objs for o in p]
        if len(objs) == 0:
            continue
        db_insert_fn(objs, client)


def mongo_insert_fn(objs, client):
    db = client.pdfs
    for obj in objs:
        print(obj['content'])
        print('-----------------------------------------')
    result = db.sections.insert_many(objs)
    logging.info(f'Inserted result: {result}')


@click.command()
@click.argument('num_processes')
def run(num_processes):
    section_scan(mongo_insert_fn, int(num_processes))


if __name__ == '__main__':
    run()


