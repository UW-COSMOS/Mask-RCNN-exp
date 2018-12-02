from mrcnn import utils
import os
from voc_utils import load_from_file
import numpy as np

class PageDataset(utils.Dataset):

    def __init__(self, split, path, collapse):
        super()
        self.split = split
        self.path = path
        self.collapse = collapse

    def load_page(self, test_dir='VOC_test', train_dir='VOC', classes='default'):
        if classes == 'default':
            classes = ["figureRegion", "formulaRegion", "tableRegion"]
        if self.split == "test":
            self.path = self.path.format(test_dir)
        else:
            self.path = self.path.format(train_dir)
        for idx, cls in enumerate(classes):
            self.add_class("page", idx, cls)
        # now load identifiers
        images_list_f = os.path.join(self.path, self.split)
        images_list_f = '{}.txt'.format(images_list_f)
        try:
            with open(images_list_f) as fh:
                cnt = 0
                for line in fh:
                    cnt += 1
                    image_id = line.strip()
                    self.add_image("page", image_id=image_id, str_id=image_id, path=self.image_path(image_id))
                print("loaded {} images\n".format(cnt))
        except EnvironmentError:
            print('Something went wrong with loading the file list at: {}\n'
                  'Does the file exist?'.format(images_list_f))

    def image_path(self, image_id):
        image_path = "images/{}.jpg".format(image_id)
        return os.path.join(self.path, image_path)

    def load_mask(self,image_id):
        str_id = self.image_info[image_id]["str_id"]
        anno_path = "annotations/{}.xml".format(str_id)
        anno_path = os.path.join(self.path, anno_path)
        annotation = load_from_file(anno_path)
        if self.collapse:
            annotation.collapse_classes_icdar()
        w,h = annotation.size
        objs = annotation.objects
        mask = np.zeros([w, h, len(objs)])
        for i, obj in enumerate(objs):
            coords = obj[1]
            mask[coords[1]:coords[3], coords[0]:coords[2], i] = 1

        clsids = np.array([self.class_names.index(obj[0]) for obj in objs])
        return mask.astype(np.bool), clsids.astype(np.int32)


