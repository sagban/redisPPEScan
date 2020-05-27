import argparse
import redis
from urllib.parse import urlparse
import imageio
import io
from gearsclient import GearsRemoteBuilder as GearsBuilder
import gearsclient as redisgears
import cv2
import base64
import redisai as redisAI
import numpy as np
import sys
import redisai
if __name__ == '__main__':
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help='Redis URL', type=str, default='redis://127.0.0.1:6379')
    args = parser.parse_args()

    # Set up some vars
    initialized_key = 'ppe:initialized'

    # Set up Redis connection
    url = urlparse(args.url)
    conn = redis.Redis(host=url.hostname, port=url.port)
    if not conn.ping():
        raise Exception('Redis unavailable')

    # Check if this Redis instance had already been initialized
    initialized = conn.exists(initialized_key)
    if initialized:
        print('Discovered evidence of a previous initialization - skipping.')
        exit(0)

    # Load the RedisAI model
    print('Loading model - ', end='')
    with open('models/face_mask_detection.pb', 'rb') as f:
        model = f.read()
        res = conn.execute_command('AI.MODELSET',
                                   'ppe:model',
                                   'TF',
                                   'CPU',
                                   'INPUTS',
                                   'data_1',
                                   'OUTPUTS',
                                   'loc_branch_concat_1/concat',
                                   'cls_branch_concat_1/concat', 'BLOB' ,model)
    # print(res)

    # Load the gear
    print('Loading gear - ', end='')
    with open('gear.py', 'rb') as f:
        gear = f.read()
        res = conn.execute_command('RG.PYEXECUTE', gear)
        print(res)

    # Lastly, set a key that indicates initialization has been performed
    print('Flag initialization as done - ', end='')
    print(conn.set(initialized_key, 'completed!'))
