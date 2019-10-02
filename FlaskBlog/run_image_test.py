import cv2
import numpy as np
import time
from estimator_test import TfPoseEstimator

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' or any('0', '1', '2')

import warnings
warnings.filterwarnings("ignore")
warnings.simplefilter(action='ignore', category=FutureWarning)

def read_imgfile(path, width, height):
    val_image = cv2.imread(path, cv2.IMREAD_COLOR)
    if val_image is None: 
        return False
    if width is not None and height is not None:
        val_image = cv2.resize(val_image, (width, height))
    return val_image

def generate_pose_image(image_filename):
    # estimate human poses from a single image !

    w, h = map(int, '432x368'.split('x'))
    # w, h = map(int, '640x480'.split('x'))
    # w, h = map(int, '320x240'.split('x'))
    
    # image = read_imgfile(args.image, w, h)
    image = read_imgfile(image_filename, None, None)
    if image is None or image is False: 
        return False

    # e = TfPoseEstimator('graph_opt_mobilenet_thin.pb', target_size=(w, h))
    e = TfPoseEstimator('graph_opt_cmu.pb', target_size=(w, h))

    pose = np.zeros_like(image)
    # image = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    t = time.time()
    humans = e.inference(image, scales=[None])
    elapsed = time.time() - t

    # print('\nPose Generation time (1-image): {:.3f}s\n'.format(elapsed))
    pose = TfPoseEstimator.draw_humans(pose, humans, imgcopy=False)

    cv2.imshow('tf-pose-estimation result pose', pose)
    cv2.imwrite('pose.jpg', pose)
    cv2.waitKey()
    cv2.destroyAllWindows()

    del(e)
    
    # If no pose detected, return False
    if np.array_equal(np.zeros_like(pose), pose):
        return False
    return True