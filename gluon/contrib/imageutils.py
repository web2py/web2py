# -*- coding: utf-8 -*-

#######################################################################
#
# Put this file in yourapp/modules/images.py
#
# Given the model
#
# db.define_table("table_name", Field("picture", "upload"),
#                 Field("thumbnail", "upload"))
#
# to resize the picture on upload
#
# from images import RESIZE
#
# db.table_name.picture.requires = RESIZE(200, 200)
#
# to store original image in picture and create a thumbnail
# in 'thumbnail' field
#
# from images import THUMB
# db.table_name.thumbnail.compute = lambda row: THUMB(row.picture, 200, 200)

#########################################################################
from gluon import current


class RESIZE(object):

    def __init__(self, nx=160, ny=80, quality=100, padding = False,
                 error_message=' image resize'):
        (self.nx, self.ny, self.quality, self.error_message, self.padding) = (
            nx, ny, quality, error_message, padding)

    def __call__(self, value):
        if isinstance(value, str) and len(value) == 0:
            return (value, None)
        from PIL import Image
        from io import BytesIO
        try:
            img = Image.open(value.file)
            img.thumbnail((self.nx, self.ny), Image.ANTIALIAS)
            s = BytesIO()
            if self.padding:
                background = Image.new('RGBA', (self.nx, self.ny), (255, 255, 255, 0))
                background.paste(
                    img,
                    ((self.nx - img.size[0]) // 2, (self.ny - img.size[1]) // 2))
                background.save(s, 'JPEG', quality=self.quality)
            else:
                img.save(s, 'JPEG', quality=self.quality)
            s.seek(0)
            value.file = s
        except:
            return (value, self.error_message)
        else:
            return (value, None)


def THUMB(image, nx=120, ny=120, gae=False, name='thumb'):
    if image:
        if not gae:
            request = current.request
            from PIL import Image
            import os
            img = Image.open(os.path.join(request.folder, 'uploads', image))
            img.thumbnail((nx, ny), Image.ANTIALIAS)
            root, ext = os.path.splitext(image)
            thumb = '%s_%s%s' % (root, name, ext)
            img.save(request.folder + 'uploads/' + thumb)
            return thumb
        else:
            return image
