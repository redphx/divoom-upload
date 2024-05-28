import time
import os
import glob
from Crypto.Cipher import AES
import random
import requests
import json
import time
import subprocess
from PIL import Image
from PIL import GifImagePlugin
import shutil


import pkg_resources
pkg_resources.get_distribution("Pillow").version

TYPE_PIC = 0
TYPE_ANI = 1
TYPE_MULTI_PIC = 2
TYPE_MULTI_ANI = 3

AES_SECRET_KEY = '78hrey23y28ogs89'
AES_IV = '1234567890123456'

UPLOAD_URL = 'http://f.divoom-gz.com/upload.php'

USER_EMAIL = ''
USER_PASSWORD = ''  # MD5 password

USER_INFO = {}

def generate_random_data(width, height):
    data = []
    for w in range(0, width):
        for h in range(0, height):
            r = random.randrange(255)
            g = random.randrange(255)
            b = random.randrange(255)
            data.append(r)
            data.append(g)
            data.append(b)
    return data


def encrypt_data(data):
    cipher = AES.new(AES_SECRET_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(data)


def login():
    global USER_INFO

    data = {
        'Token': int(time.time()),
        'Email': USER_EMAIL,
        'Password': USER_PASSWORD,
        'TimeZone': '+7',
    }

    r = requests.post('http://app.divoom-gz.com/UserLogin', json=data)
    USER_INFO = r.json()


def pixel_bean_to_file(pixel_bean):
    encrypted = ''

    if pixel_bean['type'] == TYPE_PIC:
        data = bytearray(pixel_bean['data'])
        encrypted = chr(8) + encrypt_data(data)
    elif pixel_bean['type'] == TYPE_MULTI_ANI:
        frames = bytearray()
        for frame in pixel_bean['data']:
            arr = bytearray(frame)
            while len(arr) < 3072:
                arr.append(chr(0))

            frames += arr

        header = chr(9) + chr(len(frames) & 0xFF) + chr(pixel_bean['speed'] >> 8 & 0xFF) + chr(pixel_bean['speed'] & 0xFF)
        encrypted = header + encrypt_data(frames)

    with open('shareURL', 'w') as f:
        f.write(encrypted)

def upload_to_gallery(name):
    files = {'upFile': open('shareURL', 'rb')}
    headers = {'User-Agent': 'Aurabox/2.0.43 (iPad; iOS 13.3; Scale/2.00)'}

    r = requests.post(UPLOAD_URL, files=files, headers=headers)
    print(r.text)
    file_id = r.json()['FileId']

    data = {
        'Token': USER_INFO['Token'],
        'UserId': USER_INFO['UserId'],
        'Version': 5,
        'FileId': file_id,
        'FileSize': 1,
        'FileType': 1,
        'FileMD5': '0',
        'FileName': name,
        'Classify': 1,
    }
    r = requests.post('http://app.divoom-gz.com/GalleryUploadV2', json=data, headers=headers)
    print(r.json())


def chunk(seq, size):
    return [seq[i:i+size] for i in range(0, len(seq), size)]


def parse_image(img_file):
    pixel_bean = {
        'width': 16,
        'height': 16,
    }

    data = []
    im = Image.open(img_file)

    if '.gif' in img_file.lower():
        pixel_bean['type'] = TYPE_MULTI_ANI

        shutil.rmtree('frames')
        os.mkdir('frames')

        '''
        '-dither', 'Riemersma',
        '-colors', '16',
        '''
        subprocess.call(['convert', img_file,
            '-coalesce',
            '-background', 'black',
            '-alpha', 'remove',
            '-alpha', 'off',
            '-gravity', 'center',
            '-filter', 'point',
            '-define', 'filter:blur=0',
            '-interpolate', 'NearestNeighbor',
            '-scale', '32x32',
            '-extent', '32x32',
            'frames/%05d.png'])

        speed = im.info['duration']
        speed = min(500, speed)
        speed = max(50, speed)
        print('Speed: %d' % speed)
        pixel_bean['speed'] = speed

        for filename in sorted(glob.glob('frames/*')):
            frame_im = Image.open(filename)
            frame_im = frame_im.convert('RGB')

            frame_data = []
            for y in range(0, 32):
                for x in range(0, 32):
                    '''
                    if x > im.width or y > im.height:
                        frame_data.append(0)
                        frame_data.append(0)
                        frame_data.append(0)
                        continue
                    '''
                    r, g, b = frame_im.getpixel((x, y))
                    frame_data.append(r)
                    frame_data.append(g)
                    frame_data.append(b)

            data.append(frame_data)
    else:
        pixel_bean['type'] = TYPE_PIC
        im = im.convert('RGB')
        for y in range(0, im.height):
            for x in range(0, im.width):
                r, g, b = im.getpixel((x, y))
                data.append(r)
                data.append(g)
                data.append(b)

    pixel_bean['data'] = data

    return pixel_bean


UPLOAD = True

if UPLOAD:
  login()

for filename in glob.glob('input/*'):
  head_tail = os.path.split(filename)
  name = head_tail[1].split('.')[0]
  print(name)

  pixel_bean = parse_image(filename)
  pixel_bean_to_file(pixel_bean)

  if UPLOAD:
    upload_to_gallery(name)
    # os.rename(filename, 'done/' + head_tail[1])
    time.sleep(5)


# shutil.rmtree('frames')
