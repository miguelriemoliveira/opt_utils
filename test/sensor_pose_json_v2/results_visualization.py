#!/usr/bin/env python
"""
Reads a set of data and labels from a group of sensors in a json file and calibrates the poses of these sensors.
"""

# -------------------------------------------------------------------------------
# --- IMPORTS
# -------------------------------------------------------------------------------
import json
import OptimizationUtils.utilities as utilities
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
from numpy.linalg import inv
import argparse
import cv2

# -------------------------------------------------------------------------------
# --- FUNCTIONS
# -------------------------------------------------------------------------------


def detect_pose(obj_pts, corners, camera_matrix, distortion_vector):
    ret, rvecs, tvecs = cv2.solvePnP(obj_pts, corners, camera_matrix, distortion_vector)
    if ret:
        return cv2.Rodrigues(rvecs)[0], tvecs, corners


def matlab_stereo(data_model, sensor1, sensor2, collection_key_):

    # Intrinsics matrix:

    K_1_model = np.zeros((3, 3), np.float32)
    K_2_model = np.zeros((3, 3), np.float32)

    K_1_model[0, :] = data_model['K'][sensor1][0:3]
    K_1_model[1, :] = data_model['K'][sensor1][3:6]
    K_1_model[2, :] = data_model['K'][sensor1][6:9]

    K_2_model[0, :] = data_model['K'][sensor2][0:3]
    K_2_model[1, :] = data_model['K'][sensor2][3:6]
    K_2_model[2, :] = data_model['K'][sensor2][6:9]

    print("K_" + str(sensor1) + "_model:\n")
    print(K_1_model)
    print("\nK_" + str(sensor2) + "_model:\n")
    print(K_2_model)

    # Transforms from each sensor to chessboard:

    string_sensor_1 = str(sensor1 + "_optical")
    string_sensor_2 = str(sensor2 + "_optical")

    s1_T_chessboard_model_rot = utilities.rodriguesToMatrix(
        data_model['collections'][collection_key_]['transforms'][string_sensor_1]['rodr'])
    s1_T_chessboard_model_trans = data_model['collections'][collection_key_]['transforms'][string_sensor_1]['trans']
    s2_T_chessboard_model_rot = utilities.rodriguesToMatrix(
        data_model['collections'][collection_key_]['transforms'][string_sensor_2]['rodr'])
    s2_T_chessboard_model_trans = data_model['collections'][collection_key_]['transforms'][string_sensor_2]['trans']

    s1_T_chessboard_model = np.zeros((3, 3), np.float32)
    s2_T_chessboard_model = np.zeros((3, 3), np.float32)

    for i in range(0, 2):
        s1_T_chessboard_model[:, i] = s1_T_chessboard_model_rot[:, i]
        s2_T_chessboard_model[:, i] = s2_T_chessboard_model_rot[:, i]
    for ii in range(0, 3):
        s1_T_chessboard_model[ii, 2] = s1_T_chessboard_model_trans[ii]
        s2_T_chessboard_model[ii, 2] = s2_T_chessboard_model_trans[ii]

    # print("\n\nTESTE(tf s2 to chess matlab:\n")
    # print(s1_T_chessboard_model)

    A_model = np.dot(K_2_model, s2_T_chessboard_model)
    B_model = np.dot(A_model, inv(s1_T_chessboard_model))
    homography_matrix_model = np.dot(B_model, inv(K_1_model))

    return homography_matrix_model


if __name__ == "__main__":

    # ---------------------------------------
    # --- Parse command line argument
    # ---------------------------------------
    ap = argparse.ArgumentParser()
    ap.add_argument("-test_dataset", "--json_file_dataset_test",
                    help="Json file containing the dataset that will be used to test all calibration approaches results.",
                    type=str, required=True)
    ap.add_argument("-json_opt_left", "--json_file_opt_left",
                    help="Json file containing input dataset from optimization procedure, using the top_left_camera to set the chessboard first guess.", type=str, required=True)
    ap.add_argument("-json_opt_right", "--json_file_opt_right",
                    help="Json file containing input dataset from optimization procedure, using the top_right_camera to set the chessboard first guess.", type=str, required=True)
    ap.add_argument("-json_stereo", "--json_file_stereo",
                    help="Json file containing input dataset from opencv stereo calibration.", type=str, required=True)
    # ap.add_argument("-json_calibcam", "--json_file_calibcam",
    #                 help="Json file containing input dataset from opencv calibrate camera func.", type=str, required=True)
    ap.add_argument("-json_kalibr", "--json_file_kalibr",
                    help="Json file containing input dataset from kalibr calibration system.", type=str, required=True)

    ap.add_argument("-fs", "--first_sensor", help="First Sensor: his evaluation points will be projected to the second "
                                                  "sensor data.", type=str, required=True)
    ap.add_argument("-ss", "--second_sensor", help="Second Sensor: his evaluation points will be compared with the "
                                                   "projected ones from the first sensor.", type=str, required=True)

    args = vars(ap.parse_args())
    print("\nArgument list=" + str(args) + '\n')

    # ---------------------------------------
    # --- INITIALIZATION Read data from file and read sensors that will be compared
    # ---------------------------------------
    """ Loads a json file containing the chessboards poses for each collection"""
    f_td = open(args['json_file_dataset_test'], 'r')
    f_l = open(args['json_file_opt_left'], 'r')
    f_r = open(args['json_file_opt_right'], 'r')
    # ff = open(args['json_file_calibcam'], 'r')
    fff = open(args['json_file_stereo'], 'r')
    ffff = open(args['json_file_kalibr'], 'r')
    data_test = json.load(f_td)
    data_opt_left = json.load(f_l)
    data_opt_right = json.load(f_r)
    # data_cc = json.load(ff)
    data_stereo = json.load(fff)
    data_kalibr = json.load(ffff)

    sensor_1 = args['first_sensor']
    sensor_2 = args['second_sensor']
    # collection = str(args['collection_choosed'])
    input_sensors = {'first_sensor': sensor_1, 'second_sensor': sensor_2}
    # input_datas = {'data_test': data_test, 'data_opt_left': data_opt_left, 'data_opt_right': data_opt_right, 'data_stereo': data_stereo, 'data_cc': data_cc, 'data_kalibr': data_kalibr}
    input_datas = {'data_test': data_test, 'data_opt_left': data_opt_left, 'data_opt_right': data_opt_right, 'data_stereo': data_stereo, 'data_kalibr': data_kalibr}

    n_sensors = 0
    for sensor_key in data_test['sensors'].keys():
        n_sensors += 1

    for i_sensor_key, i_sensor in input_sensors.items():
        a = 0
        for sensor_key, sensor in data_test['sensors'].items():
            a += 1
            if i_sensor == sensor['_name']:
                break
            elif a == n_sensors:
                print("ERROR: " + i_sensor + " doesn't exist on the input sensors list from the test dataset json file.")
                exit(0)

    n_collections = 0
    for collection_key in data_test['collections'].items():
        n_collections += 1


    num_x = int(data_test['calibration_config']['calibration_pattern']['dimension']['x'])
    num_y = int(data_test['calibration_config']['calibration_pattern']['dimension']['y'])
    n_points = num_x * num_y
    chess_size = float(data_test['calibration_config']['calibration_pattern']['size'])

    # ---------------------------------------
    # --- FILTER only te two cameras of interest  (this is not strictly necessary)
    # ---------------------------------------
    for data_key, data in input_datas.items():
        for sensor_key, sensor in data['sensors'].items():
            if sensor_1 == sensor['_name']:
                continue
            elif sensor_2 == sensor['_name']:
                continue
            else:
                del data['sensors'][sensor_key]

    n_cams = 0

    for sensor_key, sensor in data_test['sensors'].items():
        if sensor['msg_type'] == "Image":
            n_cams += 1

    # Intrinsic matrixes and Distortion parameteres:
    for data_key, data in input_datas.items():
        K_1 = np.zeros((3, 3), np.float32)
        K_2 = np.zeros((3, 3), np.float32)
        D_1 = np.zeros((5, 1), np.float32)
        D_2 = np.zeros((5, 1), np.float32)

        K_1[0, :] = data['sensors'][sensor_1]['camera_info']['K'][0:3]
        K_1[1, :] = data['sensors'][sensor_1]['camera_info']['K'][3:6]
        K_1[2, :] = data['sensors'][sensor_1]['camera_info']['K'][6:9]

        D_1[:, 0] = data['sensors'][sensor_1]['camera_info']['D'][0:5]

        K_2[0, :] = data['sensors'][sensor_2]['camera_info']['K'][0:3]
        K_2[1, :] = data['sensors'][sensor_2]['camera_info']['K'][3:6]
        K_2[2, :] = data['sensors'][sensor_2]['camera_info']['K'][6:9]

        D_2[:, 0] = data['sensors'][sensor_2]['camera_info']['D'][0:5]

        if data_key == 'data_opt_left':
            K_1_opt_left = K_1
            K_2_opt_left = K_2
            D_1_opt_left = D_1
            D_2_opt_left = D_2
        elif data_key == 'data_opt_right':
            K_1_opt_right = K_1
            K_2_opt_right = K_2
            D_1_opt_right = D_1
            D_2_opt_right = D_2
        elif data_key == 'data_stereo':
            K_1_stereo = K_1
            K_2_stereo = K_2
            D_1_stereo = D_1
            D_2_stereo = D_2
        # elif data_key == 'data_cc':
        #     K_1_cc = K_1
        #     K_2_cc = K_2
        #     D_1_cc = D_1
        #     D_2_cc = D_2
        elif data_key == 'data_kalibr':
            K_1_kalibr = K_1
            K_2_kalibr = K_2
            D_1_kalibr = D_1
            D_2_kalibr = D_2

    tf_sensors_1t2 = str(sensor_1 + '-' + sensor_2)
    tf_sensors_2t1 = str(sensor_2 + '-' + sensor_1)

    points_opt_left = np.zeros((2, 0), np.float32)
    points_opt_right = np.zeros((2, 0), np.float32)
    points_stereo = np.zeros((2, 0), np.float32)
    # points_cc = np.zeros((2, 0), np.float32)
    points_kalibr = np.zeros((2, 0), np.float32)

    accepted_collections = 0
    leg = []

    # for collection_key, collection in data_test['collections'].items():
    keys = [int(key) for key in data_test['collections'].keys()]  # get keys as integers
    keys.sort()  # sort integer keys
    sorted_keys = [str(key) for key in keys]  # convert back to string from sorted integers

    for collection_key in sorted_keys:
        collection = data_test['collections'][collection_key]
        if not (collection['labels'][sensor_2]['detected'] and collection['labels'][sensor_1]['detected']):
            continue
        else:
            # -------------------------------------------------------------------
            # ------ Image Points
            # -------------------------------------------------------------------
            img_points_1 = np.ones((n_points, 2), np.float32)
            img_points_2 = np.ones((n_points, 2), np.float32)

            for idx, point in enumerate(data_test['collections'][collection_key]['labels'][sensor_2]['idxs']):
                img_points_2[idx, 0] = point['x']
                img_points_2[idx, 1] = point['y']

            for idx, point in enumerate(data_test['collections'][collection_key]['labels'][sensor_1]['idxs']):
                img_points_1[idx, 0] = point['x']
                img_points_1[idx, 1] = point['y']

            # -------------------------------------------------------------------
            # ------ Object Points
            # -------------------------------------------------------------------
            factor = round(1.)
            object_points = np.zeros((n_points, 3), np.float32)
            step_x = num_x * chess_size / (num_x * factor)
            step_y = num_y * chess_size / (num_y * factor)

            counter = 0

            for idx_y in range(0, int(num_y * factor)):
                y = idx_y * step_y
                for idx_x in range(0, int(num_x * factor)):
                    x = idx_x * step_x
                    object_points[counter, 0] = x
                    object_points[counter, 1] = y
                    object_points[counter, 2] = 0
                    counter += 1

            for data_key, data in input_datas.items():
                if data_key == 'data_opt_left':  # ---------------------OPTIMIZATION (LEFT CAMERA)---------------------

                    # Finding transform from sensor 1 to chessboard:
                    ret, rvecs, tvecs = cv2.solvePnP(object_points, img_points_1, K_1_opt_left, D_1_opt_left)
                    if not ret:
                        print ("ERROR: Chessboard wasn't found on collection" + str(collection_key))
                        exit(0)
                    s1_T_chess_h_opt_left = np.zeros((4, 4), np.float32)
                    s1_T_chess_h_opt_left[3, 3] = 1
                    s1_T_chess_h_opt_left[0:3, 3] = tvecs[:, 0]
                    s1_T_chess_h_opt_left[0:3, 0:3] = utilities.rodriguesToMatrix(rvecs)

                    selected_collection_key_opt_left = data_opt_left['collections'].keys()[0]

                    root_T_s2 = utilities.getAggregateTransform(
                        data_opt_left['sensors'][sensor_2]['chain'], data_opt_left['collections'][selected_collection_key_opt_left]['transforms'])

                    root_T_s1 = utilities.getAggregateTransform(
                        data_opt_left['sensors'][sensor_1]['chain'],
                        data_opt_left['collections'][selected_collection_key_opt_left]['transforms'])

                    s2_T_s1_h_opt_left = np.dot(inv(root_T_s2), root_T_s1)
                    s1_T_s2_h_opt_left = inv(s2_T_s1_h_opt_left)

                    s2_T_chess_h_opt_left = np.dot(s2_T_s1_h_opt_left, s1_T_chess_h_opt_left)

                    s1_T_chess_opt_left = np.zeros((3, 3), np.float32)
                    s2_T_chess_opt_left = np.zeros((3, 3), np.float32)

                    for c in range(0, 2):
                        for l in range(0, 3):
                            s1_T_chess_opt_left[l, c] = s1_T_chess_h_opt_left[l, c]
                            s2_T_chess_opt_left[l, c] = s2_T_chess_h_opt_left[l, c]

                    s1_T_chess_opt_left[:, 2] = s1_T_chess_h_opt_left[0:3, 3]
                    s2_T_chess_opt_left[:, 2] = s2_T_chess_h_opt_left[0:3, 3]


                elif data_key == 'data_opt_right': # ---------------OPTIMIZATION (RIGHT CAMERA)------------------------

                    # Finding transform from sensor 1 to chessboard:
                    ret, rvecs, tvecs = cv2.solvePnP(object_points, img_points_1, K_1_opt_right, D_1_opt_right)
                    if not ret:
                        print ("ERROR: Chessboard wasn't found on collection" + str(collection_key))
                        exit(0)
                    s1_T_chess_h_opt_right = np.zeros((4, 4), np.float32)
                    s1_T_chess_h_opt_right[3, 3] = 1
                    s1_T_chess_h_opt_right[0:3, 3] = tvecs[:, 0]
                    s1_T_chess_h_opt_right[0:3, 0:3] = utilities.rodriguesToMatrix(rvecs)

                    selected_collection_key_opt_right = data_opt_right['collections'].keys()[0]

                    root_T_s2 = utilities.getAggregateTransform(
                        data_opt_right['sensors'][sensor_2]['chain'], data_opt_right['collections'][selected_collection_key_opt_right]['transforms'])

                    root_T_s1 = utilities.getAggregateTransform(
                        data_opt_right['sensors'][sensor_1]['chain'],
                        data_opt_right['collections'][selected_collection_key_opt_right]['transforms'])

                    s2_T_s1_h_opt_right = np.dot(inv(root_T_s2), root_T_s1)
                    s1_T_s2_h_opt_right = inv(s2_T_s1_h_opt_right)

                    s2_T_chess_h_opt_right = np.dot(s2_T_s1_h_opt_right, s1_T_chess_h_opt_right)

                    s1_T_chess_opt_right = np.zeros((3, 3), np.float32)
                    s2_T_chess_opt_right = np.zeros((3, 3), np.float32)

                    for c in range(0, 2):
                        for l in range(0, 3):
                            s1_T_chess_opt_right[l, c] = s1_T_chess_h_opt_right[l, c]
                            s2_T_chess_opt_right[l, c] = s2_T_chess_h_opt_right[l, c]

                    s1_T_chess_opt_right[:, 2] = s1_T_chess_h_opt_right[0:3, 3]
                    s2_T_chess_opt_right[:, 2] = s2_T_chess_h_opt_right[0:3, 3]

                elif data_key == 'data_stereo':  # ---------------------------STEREO-----------------------------------

                    # Finding transform from sensor 1 to chessboard:
                    ret, rvecs, tvecs = cv2.solvePnP(object_points, img_points_1, K_1_stereo, D_1_stereo)
                    if not ret:
                        print ("ERROR: Chessboard wasn't found on collection" + str(collection_key))
                        exit(0)
                    s1_T_chess_h_stereo = np.zeros((4, 4), np.float32)
                    s1_T_chess_h_stereo[3, 3] = 1
                    s1_T_chess_h_stereo[0:3, 3] = tvecs[:, 0]
                    s1_T_chess_h_stereo[0:3, 0:3] = utilities.rodriguesToMatrix(rvecs)

                    selected_collection_key_stereo = data_stereo['collections'].keys()[0]

                    for tf_key, tf in data_stereo['collections'][selected_collection_key_stereo]['transforms'].items():
                        if tf_key == tf_sensors_1t2:
                            s1_T_s2_h_stereo = utilities.translationQuaternionToTransform(tf['trans'], tf['quat'])
                        elif tf_key == tf_sensors_2t1:
                            s1_T_s2_h_stereo = inv(utilities.translationQuaternionToTransform(tf['trans'], tf['quat']))

                    s2_T_chess_h_stereo = np.dot(inv(s1_T_s2_h_stereo), s1_T_chess_h_stereo)

                    s1_T_chess_stereo = np.zeros((3, 3), np.float32)
                    s2_T_chess_stereo = np.zeros((3, 3), np.float32)

                    for c in range(0, 2):
                        for l in range(0, 3):
                            s1_T_chess_stereo[l, c] = s1_T_chess_h_stereo[l, c]
                            s2_T_chess_stereo[l, c] = s2_T_chess_h_stereo[l, c]

                    s1_T_chess_stereo[:, 2] = s1_T_chess_h_stereo[0:3, 3]
                    s2_T_chess_stereo[:, 2] = s2_T_chess_h_stereo[0:3, 3]

                # elif data_key == 'data_cc':  # ---------------------------CAMERA CALIB----------------------------------
                #
                #     # Finding transform from sensor 1 to chessboard:
                #     ret, rvecs, tvecs = cv2.solvePnP(object_points, img_points_1, K_1_cc, D_1_cc)
                #     if not ret:
                #         print ("ERROR: Chessboard wasn't found on collection" + str(collection_key))
                #         exit(0)
                #     s1_T_chess_h_cc = np.zeros((4, 4), np.float32)
                #     s1_T_chess_h_cc[3, 3] = 1
                #     s1_T_chess_h_cc[0:3, 3] = tvecs[:, 0]
                #     s1_T_chess_h_cc[0:3, 0:3] = utilities.rodriguesToMatrix(rvecs)
                #
                #     s2_T_chess_h_cc = utilities.translationQuaternionToTransform(
                #         data_cc['chessboards']['collections'][collection_key][sensor_2]['trans'],
                #         data_cc['chessboards']['collections'][collection_key][sensor_2]['quat'])
                #
                #     s1_T_chess_cc = np.zeros((3, 3), np.float32)
                #
                #     s2_T_chess_cc = np.zeros((3, 3), np.float32)
                #
                #     for c in range(0, 2):
                #         for l in range(0, 3):
                #             s1_T_chess_cc[l, c] = s1_T_chess_h_cc[l, c]
                #             s2_T_chess_cc[l, c] = s2_T_chess_h_cc[l, c]
                #
                #     s1_T_chess_cc[:, 2] = s1_T_chess_h_cc[0:3, 3]
                #     s2_T_chess_cc[:, 2] = s2_T_chess_h_cc[0:3, 3]

                elif data_key == 'data_kalibr':  # ---------------------------KALIBR-----------------------------------

                    # Finding transform from sensor 1 to chessboard:
                    ret, rvecs, tvecs = cv2.solvePnP(object_points, img_points_1, K_1_kalibr, D_1_kalibr)
                    if not ret:
                        print ("ERROR: Chessboard wasn't found on collection" + str(collection_key))
                        exit(0)
                    s1_T_chess_h_kalibr = np.zeros((4, 4), np.float32)
                    s1_T_chess_h_kalibr[3, 3] = 1
                    s1_T_chess_h_kalibr[0:3, 3] = tvecs[:, 0]
                    s1_T_chess_h_kalibr[0:3, 0:3] = utilities.rodriguesToMatrix(rvecs)

                    # selected_collection_key_kalibr = data_kalibr['collections'].keys()[0]
                    selected_collection_key_kalibr = '0'

                    for tf_key, tf in data_kalibr['collections'][selected_collection_key_kalibr]['transforms'].items():
                        if tf_key == tf_sensors_1t2:
                            s1_T_s2_h_kalibr = utilities.translationQuaternionToTransform(tf['trans'], tf['quat'])
                        elif tf_key == tf_sensors_2t1:
                            s1_T_s2_h_kalibr = inv(utilities.translationQuaternionToTransform(tf['trans'], tf['quat']))

                    s2_T_chess_h_kalibr = np.dot(inv(s1_T_s2_h_kalibr), s1_T_chess_h_kalibr)

                    s1_T_chess_kalibr = np.zeros((3, 3), np.float32)
                    s2_T_chess_kalibr = np.zeros((3, 3), np.float32)

                    for c in range(0, 2):
                        for l in range(0, 3):
                            s1_T_chess_kalibr[l, c] = s1_T_chess_h_kalibr[l, c]
                            s2_T_chess_kalibr[l, c] = s2_T_chess_h_kalibr[l, c]

                    s1_T_chess_kalibr[:, 2] = s1_T_chess_h_kalibr[0:3, 3]
                    s2_T_chess_kalibr[:, 2] = s2_T_chess_h_kalibr[0:3, 3]
            # -------------------------------------------------------------------
            # ------ PRINTING TFS MATRIXES
            # -------------------------------------------------------------------
            print("\n Transform s1 T chess: (OPT_LEFT)")
            print(s1_T_chess_opt_left)
            print("\n Transform s1 T chess: (OPT_RIGHT)")
            print(s1_T_chess_opt_right)
            print("\n Transform s1 T chess: (STEREO)")
            print(s1_T_chess_stereo)
            # print("\n Transform s1 T chess: (CC)")
            # print(s1_T_chess_cc)
            print("\n Transform s1 T chess: (KALIBR)")
            print(s1_T_chess_kalibr)

            print("\n Transform s2 T chess: (OPT_LEFT)")
            print(s2_T_chess_opt_left)
            print("\n Transform s2 T chess: (OPT_RIGHT)")
            print(s2_T_chess_opt_right)
            print("\n Transform s2 T chess: (STEREO)")
            print(s2_T_chess_stereo)
            # print("\n Transform s2 T chess: (CC)")
            # print(s2_T_chess_cc)
            print("\n Transform s2 T chess: (KALIBR)")
            print(s2_T_chess_kalibr)

            print("\n s1 T s2 h: (OPT_LEFT)")
            print(s1_T_s2_h_opt_left)
            print("\n s1 T s2 h: (OPT_RIGHT)")
            print(s1_T_s2_h_opt_right)
            print("\n s1 T s2 h: (STEREO)")
            print(s1_T_s2_h_stereo)
            print("\n s1 T s2 h: (KALIBR)")
            print(s1_T_s2_h_kalibr)

            # -------------------------------------------------------------------
            # ------ BUILDING HOMOGRAPHY MATRIXES
            # -------------------------------------------------------------------

            A1 = np.dot(K_2_opt_left, s2_T_chess_opt_left)
            B1 = np.dot(A1, inv(s1_T_chess_opt_left))
            C1 = np.dot(B1, inv(K_1_opt_left))
            homography_matrix_opt_left = C1

            A2 = np.dot(K_2_opt_right, s2_T_chess_opt_right)
            B2 = np.dot(A2, inv(s1_T_chess_opt_right))
            C2 = np.dot(B2, inv(K_1_opt_right))
            homography_matrix_opt_right = C2

            # A3 = np.dot(K_2_cc, s2_T_chess_cc)
            # B3 = np.dot(A3, inv(s1_T_chess_cc))
            # C3 = np.dot(B3, inv(K_1_cc))
            # homography_matrix_cc = C3

            A4 = np.dot(K_2_stereo, s2_T_chess_stereo)
            B4 = np.dot(A4, inv(s1_T_chess_stereo))
            C4 = np.dot(B4, inv(K_1_stereo))
            homography_matrix_stereo = C4

            A5 = np.dot(K_2_kalibr, s2_T_chess_kalibr)
            B5 = np.dot(A5, inv(s1_T_chess_kalibr))
            C5 = np.dot(B5, inv(K_1_kalibr))
            homography_matrix_kalibr = C5

            print("\n K_1: (OPT_LEFT)")
            print(K_1_opt_left)
            print("\n K_1: (OPT_RIGHT)")
            print(K_1_opt_right)
            print("\n K_1: (STEREO)")
            print(K_1_stereo)
            # print("\n K_1: (CC)")
            # print(K_1_cc)
            print("\n K_1: (KALIBR)")
            print(K_1_kalibr)

            print("\n K_2: (OPT_LEFT)")
            print(K_2_opt_left)
            print("\n K_2: (OPT_RIGHT)")
            print(K_2_opt_right)
            print("\n K_2: (STEREO)")
            print(K_2_stereo)
            # print("\n K_2: (CC)")
            # print(K_2_cc)
            print("\n K_2: (KALIBR)")
            print(K_2_kalibr)

            print("\n Homography matrix: (OPT_LEFT)")
            print(homography_matrix_opt_left)
            print("\n Homography matrix: (OPT_RIGHT)")
            print(homography_matrix_opt_right)
            print("\n Homography matrix: (STEREO)")
            print(homography_matrix_stereo)
            # print("\n Homography matrix: (CC)")
            # print(homography_matrix_cc)
            print("\n Homography matrix: (KALIBR)")
            print(homography_matrix_kalibr)

            # -------------------------------------------------------------------
            # ------ Points to compute the difference
            # -------------------------------------------------------------------

            idx_s1_gt = np.ones((3, n_points), np.float32)
            idx_s2_gt = np.ones((3, n_points), np.float32)

            for idx, point in enumerate(data_test['collections'][collection_key]['labels'][sensor_2]['idxs']):
                idx_s2_gt[0, idx] = point['x']
                idx_s2_gt[1, idx] = point['y']

            for idx, point in enumerate(data_test['collections'][collection_key]['labels'][sensor_1]['idxs']):
                idx_s1_gt[0, idx] = point['x']
                idx_s1_gt[1, idx] = point['y']

            # -------------------------------------------------------------------
            # ------ COMPARISON BETWEEN THE ERROR OF ALL CALIBRATION PROCEDURES
            # -------------------------------------------------------------------

            # OPTIMIZATION_LEFT:
            s_idx_s2_proj_opt_left = np.dot(homography_matrix_opt_left, idx_s1_gt)
            soma_opt_left = 0
            for i in range(0, n_points):
                soma_opt_left += s_idx_s2_proj_opt_left[2, i]
            media_opt_left = soma_opt_left / n_points
            s_opt_left = 1 / media_opt_left
            idx_s2_proj_opt_left = s_opt_left * s_idx_s2_proj_opt_left  # (*s_opt)

            # OPTIMIZATION_RIGHT:
            s_idx_s2_proj_opt_right = np.dot(homography_matrix_opt_right, idx_s1_gt)
            soma_opt_right = 0
            for ii in range(0, n_points):
                soma_opt_right += s_idx_s2_proj_opt_right[2, ii]
            media_opt_right = soma_opt_right / n_points
            s_opt_right = 1 / media_opt_right
            idx_s2_proj_opt_right = s_opt_right * s_idx_s2_proj_opt_right  # (*s_opt)

            # STEREO CALIBRATION:
            s_idx_s2_proj_stereo = np.dot(homography_matrix_stereo, idx_s1_gt)
            soma_stereo = 0
            for iii in range(0, n_points):
                soma_stereo += s_idx_s2_proj_stereo[2, iii]
            media_stereo = soma_stereo / n_points
            s_stereo = 1 / media_stereo
            idx_s2_proj_stereo = s_stereo * s_idx_s2_proj_stereo  # s_stereo *

            # CAMERA CALIBRATION:
            # s_idx_s2_proj_cc = np.dot(homography_matrix_cc, idx_s1_gt)
            # soma_cc = 0
            # for iv in range(0, n_points):
            #     soma_cc += s_idx_s2_proj_stereo[2, iv]
            # media_cc = soma_cc / n_points
            # s_cc = 1 / media_cc
            # idx_s2_proj_cc = s_cc * s_idx_s2_proj_cc  # s_cc *

            # KALIBR CALIBRATION:
            s_idx_s2_proj_kalibr = np.dot(homography_matrix_kalibr, idx_s1_gt)
            soma_kalibr = 0
            for v in range(0, n_points):
                soma_kalibr += s_idx_s2_proj_kalibr[2, v]
            media_kalibr = soma_kalibr / n_points
            s_kalibr = 1 / media_kalibr
            idx_s2_proj_kalibr = s_kalibr * s_idx_s2_proj_kalibr  # s_kalibr *

            print("\n re-projected idx (without s): (OPT_LEFT)")
            print(s_idx_s2_proj_opt_left[:, 0:3])
            print("\n re-projected idx (without s): (OPT_RIGHT)")
            print(s_idx_s2_proj_opt_right[:, 0:3])
            print("\n re-projected idx (without s): (STEREO)")
            print(s_idx_s2_proj_stereo[:, 0:3])
            # print("\n re-projected idx (without s): (CC)")
            # print(s_idx_s2_proj_cc[:, 0:3])
            print("\n re-projected idx (without s): (KALIBR)")
            print(s_idx_s2_proj_kalibr[:, 0:3])
            # -------------------------------------------------------------------
            # ------ ERROR!!!

            points_opt_left_ = idx_s2_proj_opt_left[0:2, :] - idx_s2_gt[0:2, :]
            points_opt_right_ = idx_s2_proj_opt_right[0:2, :] - idx_s2_gt[0:2, :]
            points_stereo_ = idx_s2_proj_stereo[0:2, :] - idx_s2_gt[0:2, :]
            # points_cc_ = idx_s2_proj_cc[0:2, :] - idx_s2_gt[0:2, :]
            points_kalibr_ = idx_s2_proj_kalibr[0:2, :] - idx_s2_gt[0:2, :]
            # -------------------------------------------------------------------

            x_max_opt_left = np.amax(np.abs(points_opt_left_[0, :]))
            y_max_opt_left = np.amax(np.abs(points_opt_left_[1, :]))
            x_max_opt_right = np.amax(np.abs(points_opt_right_[0, :]))
            y_max_opt_right = np.amax(np.abs(points_opt_right_[1, :]))
            x_max_stereo = np.amax(np.abs(points_stereo_[0, :]))
            y_max_stereo = np.amax(np.abs(points_stereo_[1, :]))
            # x_max_cc = np.amax(np.abs(points_cc_[0, :]))
            # y_max_cc = np.amax(np.abs(points_cc_[1, :]))
            x_max_kalibr = np.amax(np.abs(points_kalibr_[0, :]))
            y_max_kalibr = np.amax(np.abs(points_kalibr_[1, :]))

            print('\nCOLLECTION:')
            print(collection_key)
            print ("\nx_max_opt_left: " + str(x_max_opt_left))
            print ("\ny_max_opt_left: " + str(y_max_opt_left))
            print ("\nx_max_opt_right: " + str(x_max_opt_right))
            print ("\ny_max_opt_right: " + str(y_max_opt_right))
            print ("\nx_max_stereo: " + str(x_max_stereo))
            print ("\ny_max_stereo: " + str(y_max_stereo))
            # print ("\nx_max_cc: " + str(x_max_cc))data_opt_left
            # print ("\ny_max_cc: " + str(y_max_cc))
            print ("\nx_max_kalibr: " + str(x_max_kalibr))
            print ("\ny_max_kalibr: " + str(y_max_kalibr))

            accepted_collections += 1
            leg.append(str(collection_key))

            for n in range(0, n_points+1):
                points_opt_left = np.append(points_opt_left, points_opt_left_[:, n:n+1], 1)
                points_opt_right = np.append(points_opt_right, points_opt_right_[:, n:n+1], 1)
                points_stereo = np.append(points_stereo, points_stereo_[:, n:n+1], 1)
                # points_cc = np.append(points_cc, points_cc_[:, n:n+1], 1)
                points_kalibr = np.append(points_kalibr, points_kalibr_[:, n:n + 1], 1)

    total_points = n_points * accepted_collections
    print('\nTotal studied points (for each procedure): ')
    print(total_points)

    avg_error_x_opt_left = np.sum(np.abs(points_opt_left[0, :]))/total_points
    avg_error_y_opt_left = np.sum(np.abs(points_opt_left[1, :])) / total_points
    avg_error_x_opt_right = np.sum(np.abs(points_opt_right[0, :])) / total_points
    avg_error_y_opt_right = np.sum(np.abs(points_opt_right[1, :])) / total_points
    avg_error_x_stereo = np.sum(np.abs(points_stereo[0, :])) / total_points
    avg_error_y_stereo = np.sum(np.abs(points_stereo[1, :])) / total_points
    # avg_error_x_cc = np.sum(np.abs(points_cc[0, :])) / total_points
    # avg_error_y_cc = np.sum(np.abs(points_cc[1, :])) / total_points
    avg_error_x_kalibr = np.sum(np.abs(points_kalibr[0, :])) / total_points
    avg_error_y_kalibr = np.sum(np.abs(points_kalibr[1, :])) / total_points

    standard_deviation_opt_left = np.std(points_opt_left)
    standard_deviation_ax2_opt_left = np.std(points_opt_left, axis=1)
    standard_deviation_opt_right = np.std(points_opt_right)
    standard_deviation_ax2_opt_right = np.std(points_opt_right, axis=1)
    standard_deviation_stereo = np.std(points_stereo)
    standard_deviation_ax2_stereo = np.std(points_stereo, axis=1)
    # standard_deviation_cc = np.std(points_cc)
    # standard_deviation_ax2_cc = np.std(points_cc, axis=1)
    standard_deviation_kalibr = np.std(points_kalibr)
    standard_deviation_ax2_kalibr = np.std(points_kalibr, axis=1)

    print("\nAVERAGE ERROR (our optimization left):")
    print("x = " + str(avg_error_x_opt_left) + " pix ;  y = " + str(avg_error_y_opt_left) + " pix")
    print("\nAVERAGE ERROR (our optimization right):")
    print("x = " + str(avg_error_x_opt_right) + " pix ;  y = " + str(avg_error_y_opt_right) + " pix")
    print("\nAVERAGE ERROR (openCV stereo calibration):")
    print("x = " + str(avg_error_x_stereo) + " pix ;   y = " + str(avg_error_y_stereo) + " pix")
    # print("\nAVERAGE ERROR (openCV calibrate camera):")
    # print("x = " + str(avg_error_x_cc) + " pix ;   y = " + str(avg_error_y_cc) + " pix")
    print("\nAVERAGE ERROR (kalibr):")
    print("x = " + str(avg_error_x_kalibr) + " pix ;   y = " + str(avg_error_y_kalibr) + " pix")
    print("\nSTANDARD DEVIATION (our optimization left):")
    print("std = " + str(standard_deviation_opt_left))
    print("\nSTANDARD DEVIATION per axis (our optimization left):")
    print("std = " + str(standard_deviation_ax2_opt_left))
    print("\nSTANDARD DEVIATION (our optimization right):")
    print("std = " + str(standard_deviation_opt_right))
    print("\nSTANDARD DEVIATION per axis (our optimization right):")
    print("std = " + str(standard_deviation_ax2_opt_right))
    print("\nSTANDARD DEVIATION (openCV stereo calibration):")
    print("std = " + str(standard_deviation_stereo))
    print("\nSTANDARD DEVIATION per axis (openCV stereo calibration):")
    print("std = " + str(standard_deviation_ax2_stereo))
    # print("\nSTANDARD DEVIATION (openCV calibrate camera):")
    # print("std = " + str(standard_deviation_cc))
    # print("\nSTANDARD DEVIATION per axis (openCV calibrate camera):")
    # print("std = " + str(standard_deviation_ax2_cc))
    print("\nSTANDARD DEVIATION (openCV kalibr calibration):")
    print("std = " + str(standard_deviation_kalibr))
    print("\nSTANDARD DEVIATION per axis (openCV kalibr calibration):")
    print("std = " + str(standard_deviation_ax2_kalibr))

    # -------------------------------------------------------------------
    # ------ SEE THE DIFFERENCE IN A SCATTER PLOT
    # -------------------------------------------------------------------
    colors = cm.tab20b(np.linspace(0, 1, (points_opt_left.shape[1]/n_points)))

    fig, ax = plt.subplots()
    plt.xlabel('x error (pixels)')
    plt.ylabel('y error (pixels)')

    plt.grid(True, color='k', linestyle='--', linewidth=0.1)
    string = "Difference between the image pts and the reprojected pts"
    plt.title(string)
    # x_max = np.amax(np.absolute([points_opt_left[0, :], points_opt_right[0, :], points_stereo[0, :], points_cc[0, :], points_kalibr[0, :]]))
    # y_max = np.amax(np.absolute([points_opt_left[1, :], points_opt_right[1, :], points_stereo[1, :], points_cc[1, :], points_kalibr[1, :]]))
    x_max = np.amax(np.absolute(
        [points_opt_left[0, :], points_opt_right[0, :], points_stereo[0, :], points_kalibr[0, :]]))
    y_max = np.amax(np.absolute(
        [points_opt_left[1, :], points_opt_right[1, :], points_stereo[1, :], points_kalibr[1, :]]))
    delta = 0.5
    ax.set_xlim(-22, x_max+delta)
    ax.set_ylim(-18, y_max+delta)
    # print '\nCOLORS:\n'
    # print(colors)
    scatter_points = []

    for c in range(0, accepted_collections):
        l1 = plt.scatter(points_opt_left[0, (c * n_points):((c + 1) * n_points)],
                         points_opt_left[1, (c * n_points):((c + 1) * n_points)], marker='X', color=colors[c])
        l2 = plt.scatter(points_opt_right[0, (c * n_points):((c + 1) * n_points)],
                         points_opt_right[1, (c * n_points):((c + 1) * n_points)], marker='P', color=colors[c])
        l3 = plt.scatter(points_stereo[0, (c * n_points):((c + 1) * n_points)],
                         points_stereo[1, (c * n_points):((c + 1) * n_points)], marker='v', color=colors[c])
        # l4 = plt.scatter(points_cc[0, (c * n_points):((c + 1) * n_points)],
        #                  points_cc[1, (c * n_points):((c + 1) * n_points)], marker='o', color=colors[c])
        l5 = plt.scatter(points_kalibr[0, (c * n_points):((c + 1) * n_points)],
                         points_kalibr[1, (c * n_points):((c + 1) * n_points)], marker='d', color=colors[c])

        # scatter_points.append([l1, l2, l3, l4, l5])
        scatter_points.append([l1, l2, l3, l5])

    # legend1 = plt.legend(scatter_points[0], ["proposed approach (left cam)", "proposed approach (right cam)", "OpenCV stereo calibration",
    #                                          "OpenCV calibrate camera", "kalibr2 calibration"], loc="upper left", shadow=True)

    legend1 = plt.legend(scatter_points[0],
                         ["proposed approach (left cam)", "proposed approach (right cam)", "OpenCV stereo calibration",
                          "kalibr2 calibration"], loc="upper left", shadow=True)

    plt.legend([l[0] for l in scatter_points], leg, loc=4, title="Collections", shadow=True)
    plt.gca().add_artist(legend1)

    plt.show()
