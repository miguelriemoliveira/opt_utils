#!/usr/bin/env python

import sys
import os.path
import argparse
import json
import numpy as np
import cv2

from functools import partial

from OptimizationUtils import utilities
from OptimizationUtils.OptimizationUtils import Optimizer

from OptimizationUtils.tf import TFTree, Transform


def load_data(jsonfile, sensor_filter=None, collection_filter=None):
    """Load data from a JSON file.

    Parameters
    ----------
    jsonfile: str
        Path to the JSON file that contains the data.
    sensor_filter: callable, optional
        Used to filter the data by de name of the sensor.
        For example: `lambda name: name == 'sensor_name'` will remove
        all information and data associated with this a sensor which
        name is 'sensor_name'.
    collection_filter: callable, optional
        Used to filter the data by collection number.
        For example: `lambda idx: idx != 0 ` will remove the collection with
        index 0.

    Returns
    -------
    sensors: dict
        Sensors metadata.
    collections: list of dicts
        List of collections ordered by index.
    config: dict
        Calibration configuration.
    """

    try:
        with open(jsonfile, 'r') as f:
            dataset = json.load(f)
    except IOError as e:
        print(str(e))
        sys.exit(1)

    # Sensors metadata.
    # Contains information such as their links, topics, intrinsics (if camera), etc..
    sensors = dataset['sensors']

    # A collection is a list of data. The capture order is maintained in the list.
    collections = [x for _, x in sorted(dataset['collections'].items())]

    # Filter the sensors and collection by sensor name
    if sensor_filter is not None:
        sensors = dict(filter(sensor_filter, sensors.items()))
        for c in collections:
            c['data'] = dict(filter(sensor_filter, c['data'].items()))
            c['labels'] = dict(filter(sensor_filter, c['data'].items()))

    if collection_filter is not None:
        collections = [x for idx, x in enumerate(collections) if not collection_filter(idx)]

    # Image data is not stored in the JSON file for practical reasons. Mainly, too much data.
    # Instead, the image is stored in a compressed format and its name is in the collection.
    for collection in collections:
        for sensor_name in collection['data'].keys():
            if sensors[sensor_name]['msg_type'] != 'Image':
                continue  # we are only interested in images, remember?

            filename = os.path.dirname(jsonfile) + '/' + collection['data'][sensor_name]['data_file']
            collection['data'][sensor_name]['data'] = cv2.imread(filename)

    return sensors, collections, dataset['calibration_config']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-json", "--json_file", help="JSON file containing input dataset.", type=str, required=True)

    args = vars(ap.parse_args())

    # Sensor information and calibration data is saved in a json file.
    # The dataset is organized as a collection of data.
    sensors, collections, config = load_data(args['json_file'])

    # The best way to keep track of all transformation pairs is to a have a
    # transformation tree similar to what ROS offers (github.com/safijari/tiny_tf).
    for collection in collections:
        tree = TFTree()
        for _, tf in collection['transforms'].items():
            param = tf['trans'] + tf['quat']
            tree.add_transform(tf['parent'], tf['child'], Transform(*param))

        collection['tf_tree'] = tree

    # parameters = models['parameters']
    # collections = models['collections']
    # sensors = models['sensors']
    # pattern = models['pattern']
    # config = models['config']

    pattern = config['calibration_pattern']
    # The actual comparison
    for idx, collection in enumerate(collections):

        tree = collection['tf_tree']

        # chessboard to root transformation
        tree.add_transform(pattern['parent_link'], pattern['link'], Transform(*parameters['pattern']))
        rTc = tree.lookup_transform(pattern['link'], config['world_link']).matrix

        # TODO MIGUEL's tests. To delete after solving the problem

        # lets print the transform pool
        print("all the transforms:\n'" + str(collection['transforms'].keys()))

        parent = 'ee_link'
        child = 'chessboard_link'

        # Eurico's approach (first the child, then the parent) TODO Eurico, please confirm
        T1a = tree.lookup_transform(child, parent).matrix
        # T1a = tree.lookup_transform(parent, child).matrix
        print('\nT1a (using Euricos approach) =\n' + str(T1a))

        # Miguel's approach (first the parent, then the child)
        T1b = utilities.getTransform(parent, child, collection['transforms'])
        print('\nT1b (using Miguels approach)=\n' + str(T1b))

        tranform_key = parent + '-' + child
        print("\nFrom collection['transforms'] =\n" + str(collection['transforms'][tranform_key]))
        trans = collection['transforms'][tranform_key]['trans']
        quat = collection['transforms'][tranform_key]['quat']

        T1c = utilities.translationQuaternionToTransform(trans, quat)
        print('\nT1c (extracted directly from dictionary)=\n' + str(T1c))

        exit(0)
        # --------------------------------------------------------

        for sensor_name, labels in collection['labels'].items():
            if not labels['detected']:
                continue

            xform = Transform(*parameters[sensor_name])
            tree.add_transform(sensors[sensor_name]['calibration_parent'],
                               sensors[sensor_name]['calibration_child'],
                               xform)

            # sensor to root transformation
            rTs = tree.lookup_transform(sensors[sensor_name]['camera_info']['header']['frame_id'],
                                        config['world_link']).matrix

            # convert chessboard corners from pixels to sensor coordinates.
            K = np.ndarray((3, 3), dtype=np.float, buffer=np.array(sensors[sensor_name]['camera_info']['K']))
            D = np.ndarray((5, 1), dtype=np.float, buffer=np.array(sensors[sensor_name]['camera_info']['D']))

            corners = np.zeros((len(labels['idxs']), 1, 2), dtype=np.float)
            for idx, point in enumerate(labels['idxs']):
                corners[idx, 0, 0] = point['x']
                corners[idx, 0, 1] = point['y']

            ret, rvecs, tvecs = cv2.solvePnP(pattern['grid'], corners, K, D)
            sTc = utilities.traslationRodriguesToTransform(tvecs, rvecs)

            rTs = np.dot(rTs, sTc)

            w = pattern['dimension'][0]
            h = pattern['dimension'][1] - 1

            hcp = pattern['hgrid']
            p = np.stack((hcp[0], hcp[w - 1], hcp[w * h], hcp[h * w + w - 1])).T

            error = np.apply_along_axis(np.linalg.norm, 0,
                                        np.dot(rTs, p) - np.dot(rTc, p))

            residual.extend(error.tolist())

    return residual




if __name__ == '__main__':
    main()