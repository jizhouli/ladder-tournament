# -*- coding: utf-8 -*-

import base64
import random
from urlparse import urlparse
from StringIO import StringIO

from flask import current_app as app
from qiniu import Auth, PersistentFop, op_save, put_file, BucketManager
from PIL import Image, ImageDraw, ImageFont


def image_for(image_hash, style=None):
    if not image_hash:
        return None

    url = image_hash.split('!')[0]
    up = urlparse(url)
    image_hash = up.path
    if len(image_hash) != 0 and image_hash[0] == '/':
        image_hash = image_hash[1:]

    image_domain = app.config['QINIU_DOMAIN']
    url = '//%s%s' % (image_domain, image_hash)
    if style:
        url = '%s!%s' % (url, style)
    if app.name == 'tutor.apis':
        return 'http:%s' % url
    return url


def init():
    ACCESS_KEY = str(app.config['QINIU_ACCESS_TOKEN'])
    SECRET_KEY = str(app.config['QINIU_SECRET_TOKEN'])
    q = Auth(ACCESS_KEY, SECRET_KEY)
    return q


def qiniu_token():
    q = init()
    uptoken = q.upload_token('hangjia', None, 30000)
    return uptoken


def qiniu_key():
    key = []
    seed = 'abcdefghijklmnopqrstuvwxyz0123456789'
    for i in range(32):
        key.append(random.choice(seed))
    return ''.join(key)


def qiniu_form():
    return {
        'token': qiniu_token(),
        'domain': '%s://%s' % (str(app.config['APP_TRANSPORT']),
                               str(app.config['QINIU_DOMAIN'])),
        'upload_url': str(app.config['QINIU_UPLOAD_URL'])}


def qiniu_upload(key, fpath):
    uptoken = qiniu_token()
    return put_file(uptoken, key, fpath)


def qiniu_saveas(url):
    q = init()

    up = urlparse(url)
    src_path = up.path[1:]
    src_query = up.query
    saved_key = src_path + str(random.randint(20, 100))

    pfop = PersistentFop(q, 'hangjia')
    op = op_save(src_query, 'hangjia', saved_key)
    ops = []
    ops.append(op)
    ret, info = pfop.execute(src_path, ops, 1)
    image_url = '%s://%s/%s' % (up.scheme, up.netloc, saved_key)
    if ret is not None:
        return {'url': image_url}
    else:
        return


def qiniu_delete(key):
    q = init()
    bucket = BucketManager(q)
    return bucket.delete('hangjia', key)


def qiniu_fetch(url):
    q = init()
    bucket = BucketManager(q)

    key = qiniu_key()
    ret, info = bucket.fetch(url, 'hangjia', key)
    if info.status_code == 200:
        return key


from_top = 4


def noise_arcs(draw, image):
    fg_color = app.config['CAPTCHA_FOREGROUND_COLOR']
    size = image.size
    draw.arc([-20, -20, size[0], 20], 0, 295, fill=fg_color)
    draw.line([-20, 20, size[0] + 20, size[1] - 20], fill=fg_color)
    draw.line([-20, 0, size[0] + 20, size[1]], fill=fg_color)
    return draw


def noise_dots(draw, image):
    fg_color = app.config['CAPTCHA_FOREGROUND_COLOR']
    size = image.size
    for p in range(int(size[0] * size[1] * 0.1)):
        draw.point((random.randint(0, size[0]), random.randint(0, size[1])),
                   fill=fg_color)
    return draw


def noise_functions():
    noise_fs = [noise_arcs, noise_dots]
    if noise_fs:
        return noise_fs
    return []


def post_smooth(image):
    try:
        import ImageFilter
    except ImportError:
        from PIL import ImageFilter
    return image.filter(ImageFilter.SMOOTH)


def filter_functions():
    filter_fs = [post_smooth]
    if filter_fs:
        return filter_fs
    return []


def getsize(font, text):
    if hasattr(font, 'getoffset'):
        return [x + y for x, y in zip(font.getsize(text), font.getoffset(text))]
    else:
        return font.getsize(text)


def create_captcha(text):
    font_path = app.config['CAPTCHA_FONT_PATH']
    font_size = app.config['CAPTCHA_FONT_SIZE']
    punctuation = app.config['CAPTCHA_PUNCTUATION']
    foreground_color = app.config['CAPTCHA_FOREGROUND_COLOR']
    letter_rotation = app.config['CAPTCHA_LETTER_ROTATION']

    if font_path.lower().strip().endswith('ttf'):
        font = ImageFont.truetype(font_path, font_size)
    else:
        font = ImageFont.load(font_path)

    size = getsize(font, text)
    size = (size[0] * 2, int(size[1] * 1.4))
    image = Image.new('RGB', size,
                      app.config['CAPTCHA_BACKGROUND_COLOR'])

    xpos = 2

    charlist = []
    for char in text:
        if char in punctuation and len(charlist) >= 1:
            charlist[-1] += char
        else:
            charlist.append(char)

    for char in charlist:
        fgimage = Image.new('RGB', size, foreground_color)
        charimage = Image.new('L', getsize(font, ' %s ' % char), '#000000')
        chardraw = ImageDraw.Draw(charimage)
        chardraw.text((0, 0), ' %s ' % char, font=font, fill='#ffffff')
        if letter_rotation:
            charimage = charimage.rotate(random.randrange(*letter_rotation),
                                         expand=0, resample=Image.BICUBIC)
        charimage = charimage.crop(charimage.getbbox())
        maskimage = Image.new('L', size)

        maskimage.paste(charimage, (xpos, from_top, xpos + charimage.size[0],
                                    from_top + charimage.size[1]))
        size = maskimage.size
        image = Image.composite(fgimage, image, maskimage)
        xpos = xpos + 2 + charimage.size[0]

    image = image.crop((0, 0, xpos + 1, size[1]))
    draw = ImageDraw.Draw(image)

    for f in noise_functions():
        draw = f(draw, image)
    for f in filter_functions():
        image = f(image)

    return image


def generate_base64_code(url):
    import qrcode
    qr_img = qrcode.make(url)
    buf = StringIO()
    qr_img.save(buf, 'PNG')
    value = buf.getvalue()
    return base64.b64encode(value)
