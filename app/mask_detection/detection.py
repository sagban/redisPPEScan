from redisai import Client
from ml2rt import load_model, load_script
# from skimage import io
import argparse
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
from urllib.parse import urlparse
import base64
from utils.anchor_generator import generate_anchors
from utils.anchor_decode import decode_bbox
from utils.nms import single_class_non_max_suppression

conf_thresh = 0.5
iou_thresh = 0.4
target_shape = (260, 260)

MAX_IMAGES = 50  # 5
# anchor configuration
feature_map_sizes = [[33, 33], [17, 17], [9, 9], [5, 5], [3, 3]]
anchor_sizes = [[0.04, 0.056], [0.08, 0.11], [0.16, 0.22], [0.32, 0.45], [0.64, 0.72]]
anchor_ratios = [[1, 0.62, 0.42]] * 5

# generate anchors
anchors = generate_anchors(feature_map_sizes, anchor_sizes, anchor_ratios)

# for inference , the batch size is 1, the model output shape is [1, N, 4],
# so we expand dim for anchors to [1, anchor_num, 4]
anchors_exp = np.expand_dims(anchors, axis=0)

device = 'cpu'
parser = argparse.ArgumentParser()
parser.add_argument('-u', '--url', help='Redis URL', type=str, default='redis://127.0.0.1:6379')
args = parser.parse_args()
url = urlparse(args.url)
con = Client(host=url.hostname, port=url.port)

tf_model_path = 'models/face_mask_detection.pb'
img_path = 'models/img01.jpg'
id2class = {0: 'Mask', 1: 'NoMask'}


def pre_processing(img):
    # img = 'data:image/jpeg;base64,' + base64.b64encode(img).decode('utf8')
    img = Image.open(BytesIO(img))
    img = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2RGB)
    height, width, _ = img.shape
    image_resized = cv2.resize(img, target_shape)
    image_np = image_resized / 255.0
    image_exp = np.expand_dims(image_np, axis=0).astype(np.float32)
    return image_exp, height, width


def post_processing(image, height, width, y_bboxes_output, y_cls_output, draw_result=True):
    output_info = []

    y_bboxes = decode_bbox(anchors_exp, y_bboxes_output)[0]
    y_cls = y_cls_output[0]
    # To speed up, do single class NMS, not multiple classes NMS.
    bbox_max_scores = np.max(y_cls, axis=1)
    bbox_max_score_classes = np.argmax(y_cls, axis=1)
    # keep_idx is the alive bounding box after nms.
    keep_idxs = single_class_non_max_suppression(y_bboxes,
                                                 bbox_max_scores,
                                                 conf_thresh=conf_thresh,
                                                 iou_thresh=iou_thresh,
                                                 )

    # print(keep_idxs, 'keepid')
    for idx in keep_idxs:
        conf = float(bbox_max_scores[idx])
        class_id = bbox_max_score_classes[idx]
        bbox = y_bboxes[idx]
        # clip the coordinate, avoid the value exceed the image boundary.
        xmin = max(0, int(bbox[0] * width))
        ymin = max(0, int(bbox[1] * height))
        xmax = min(int(bbox[2] * width), width)
        ymax = min(int(bbox[3] * height), height)

        if draw_result:
            if class_id == 0:
                color = (0, 255, 0)
            else:
                color = (255, 0, 0)

            image = Image.open(BytesIO(image))
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            cv2.rectangle(image, (xmin, ymin), (xmax, ymax), color, 2)
            cv2.putText(image, "%s: %.2f" % (id2class[class_id], conf), (xmin + 2, ymin - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            image = Image.fromarray(image)
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            image = buffered.getvalue()
            # Image.fromarray(image).show()
        output_info.append([id2class[class_id], image])

    return output_info


def readStream():
    stream = con.execute_command('xread', 'block', 50000, 'streams', 'camera:0', '$')
    image = stream[0][1][0][1][b'img']
    # image = base64.b64decode(image)
    processed_image, height, width = pre_processing(image)
    con.tensorset('image', processed_image)
    _ = con.modelrun('ppe_model', 'image', ['out1', 'out2'])
    y_bboxes_output = con.tensorget('out1')
    y_cls_output = con.tensorget('out2')
    output = post_processing(image, height, width, y_bboxes_output, y_cls_output)
    try:
        addToStream(output[0])
    except:
        print("No prediction")
    # print(results)

    # print(bbox_max_score_classes)
    # print(len(bbox_max_score_classes))
    readStream()


def addToStream(output):

    try:
        im = 'data:image/jpeg;base64,' + base64.b64encode(output[1]).decode('utf8')
        con.execute_command('xadd', 'results', 'MAXLEN', '~', str(MAX_IMAGES), '*', 'class', output[0], 'img', im)
        print("OK")
    except:
        print("Not added")


if __name__ == "__main__":
    tf_model = load_model(tf_model_path)
    out1 = con.modelset(
        'ppe_model', 'tf', device,
        inputs=['data_1'], outputs=['loc_branch_concat_1/concat', 'cls_branch_concat_1/concat'], data=tf_model)
    readStream()

