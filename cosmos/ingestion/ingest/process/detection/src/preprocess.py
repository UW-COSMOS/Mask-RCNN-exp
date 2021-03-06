"""
Preprocessing for torch model
"""
from PIL import ImageOps, Image
from io import BytesIO
import logging
logger = logging.getLogger(__name__)


def pad_image(bstring, size: int = 1920):
    """
    Pad the image to the desired size
    :param bstring: Byte stream
    :param size: size to pad to
    :return: path to image, padded PIL image
    """
    if isinstance(bstring, BytesIO):
        im = Image.open(bstring)
    else:
        im = bstring
    w, h = im.size
    d_w = size - w
    d_h = size - h
    if d_h < 0 or d_w < 0:
        logger.error(f'w: {w}, h: {h}')
        raise ValueError(f"One side of the image is greater than {size} pixels")
    padding = (0,0,d_w, d_h)
    im_2 = ImageOps.expand(im, padding, fill="#fff")
    return im_2


