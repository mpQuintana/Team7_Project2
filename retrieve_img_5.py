import argparse
import os
import pickle

import numpy as np
import cv2

from descriptors.feat_hsv_hst import retrieve_best_results as retrieve_best_results_hsv, get_hsv_hist
from data_handler import Data
from dataset_w1_gt import ground_truth_W5, ground_truth_W4
from descriptors.feat_wavelet_hash import retrieve_best_results, get_hash
from descriptors.root_sift import RootSift
from descriptors.sift import Sift
from evaluation import evaluation
from painting_detection import get_painting_rotated
from detect_textbb_2 import get_text_bbox


def reshape(image):
    shape_max = max(image.shape)
    if shape_max > 750:  # some of the images are HUGE
        ratio = 750 / shape_max
        image = cv2.resize(image, (0, 0), fx=ratio, fy=ratio)
    return image


def main(args):
    if args.test:
        query_folder = "query_test_random"
        ground_truth = ground_truth_test
    else:
        query_folder = "w5_devel_random"
        ground_truth = ground_truth_W5

    data = Data(database_dir='w5_BBDD_random', query_dir=query_folder)

    # test_ground_truth(ground_truth=ground_truth, museum_set=museum_set, query_set=query_set)
    eval_array = []

    query_imgs = []
    query_hist = []
    print("computing query features...")
    for im, name in data.query_imgs:
        im = reshape(im)
        query_imgs.append([None, name])
        query_hist.append(get_hsv_hist(im))

    database_hash = {}
    database_imgs = []
    database_hist = []
    print("computing dataset features...")
    for im, name in data.database_imgs:
        x, y, w, h = get_text_bbox(im)
        im[y:h, x:w, :] = 0
        im = reshape(im)
        database_imgs.append([None, name])
        database_hist.append(get_hsv_hist(im))
        database_hash[name] = get_hash(im)

    for [q_image, q_name], q_hist in zip(data.query_imgs, query_hist):
        K = len(data.database_imgs.imgs_files)

        q_image, _ = get_painting_rotated(q_image)  # detect the painting

        scores = retrieve_best_results(q_image, database_imgs, database_hash, K=K)

        scores2 = retrieve_best_results_hsv(q_hist, database_imgs, database_hist, K=K)
        # sort by image name
        scores.sort(key=lambda s: s[0], reverse=False)
        scores2.sort(key=lambda s: s[0], reverse=False)

        # add the scores (assuming we are using cv2.HISTCMP_BHATTACHARYYA, as it outputs the best match as the
        # lowest score)
        combined_scores = [(score[0][0], score[1][1]+score[0][1]) for score in zip(scores, scores2)]

        combined_scores.sort(key=lambda s: s[1], reverse=False)
        combined_scores = combined_scores[:10]
        scores = combined_scores

        if scores[0][1] > 1.11:
            scores = [(-1, 0)]

        print(scores[:3], "    ", ground_truth[q_name])
        eval = evaluation(predicted=[s[0] for s in scores], actual=ground_truth[q_name])
        print(eval)
        eval_array.append(eval)

    global_eval = np.mean(eval_array)
    print("----------------\nEvaluation: " + str(global_eval))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-use_histogram', help='use the hashing method with the histogram based method',
                        action='store_true')
    parser.add_argument('-use_root_sift', help='use root sift',
                        action='store_true')
    parser.add_argument('-test', help='runs the code on the test dataset',
                        action='store_true')
    args = parser.parse_args()
    main(args)

