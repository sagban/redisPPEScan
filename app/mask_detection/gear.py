
import imageio
import io
from gearsclient import GearsRemoteBuilder as GearsBuilder
import gearsclient as redisgears
import cv2
import base64
import redisai as redisAI
import numpy as np
import sys

framesToDrop = 0

MAX_IMAGES = 1000 # 10

index = {"0": ["n01440764", "no mask"], "1": ["n01443537", "mask"]}



def xlog(*args):
    redisgears.executeCommand('xadd', 'log', '*', 'text', ' '.join(map(str, args)))


def toOneList(l):
    res = []
    for val in l:
        if type(val) is list:
            oneList = toOneList(val)
            for v in oneList:
                res.append(v)
        else:
            res.append(val)
    return res


def addToGraphRunner(x,
              conf_thresh=0.5,
              iou_thresh=0.4,
              target_shape=(260, 260),
              draw_result=True,
              show_result=True):
    try:
        xlog('addToGraphRunner:', 'count=', x['count'])

        # output_info = []
        # height, width, _ = x['img'].shape
        # image_resized = cv2.resize(x['img'], target_shape)
        # image_np = image_resized / 255.0
        # image_exp = np.expand_dims(image_np, axis=0)

        # converting the image to matrix of colors
        data = io.BytesIO(x['img'])
        dataM = imageio.imread(data).astype(dtype='float32')
        newImg = (cv2.resize(dataM, target_shape) / 255.0) - 1

        l = np.asarray(newImg, dtype=np.float32)
        img_ba = bytearray(l.tobytes())

        # converting the matrix color to Tensor
        v1 = redisAI.createTensorFromBlob('FLOAT', [1, 160, 160, 3], img_ba)

        # creating the graph runner, 'g1' is the key in redis on which the graph is located
        graphRunner = redisAI.createModelRunner('ppe:model')
        redisAI.modelRunnerAddInput(graphRunner, 'data_1:0', v1)
        redisAI.modelRunnerAddOutput(graphRunner, 'loc_branch_concat_1/concat:0')
        redisAI.modelRunnerAddOutput(graphRunner, 'cls_branch_concat_1/concat:0')

        # run the graph and translate the result to python list
        res = redisAI.tensorToFlatList(redisAI.modelRunnerRun(graphRunner)[0])

        # extract the animal name
        # res1 = sorted(res, reverse=True)
        ppe = index[str(res[1][0])][1]
        xlog('addToGraphRunner:', 'ppe=', ppe)

        return (ppe, x['img'])
    except:
        xlog('addToGraphRunner: error:', sys.exc_info()[0])

def addToStream(x):
    # save animal name into a new stream
    try:
        redisgears.executeCommand('xadd', 'results', 'MAXLEN', '~', str(MAX_IMAGES), '*', 'image', 'data:image/jpeg;base64,' + base64.b64encode(x[1]).decode('utf8'))
    except:
        xlog('addToStream: error:', sys.exc_info()[0])

def shouldTakeFrame(x):
    try:
        global framesToDrop
        framesToDrop += 1
        xlog('shouldTakeFrame', x['count'], (framesToDrop % 10 == 0))
        return framesToDrop % 10 == 0
    except:
        xlog('shouldTakeFrame: error:', sys.exc_info()[0])

def passAll(x):
    try:
        redisgears.executeCommand('xadd', 'all', 'MAXLEN', '~', str(MAX_IMAGES), '*', 'image', 'data:image/jpeg;base64,' + base64.b64encode(x['img']).decode('utf8'))
    except:
        xlog('passAll: error:', sys.exc_info()[0])

# creating execution plane


gb = GearsBuilder('StreamReader')
gb.foreach(passAll)
gb.filter(shouldTakeFrame)
gb.map(addToGraphRunner)
gb.foreach(addToStream)
gb.register('camera:0')
