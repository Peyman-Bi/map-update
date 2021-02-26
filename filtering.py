import pandas as pd
from shapely import wkb
from shapely.geometry import LineString
import geopandas as gp
import hashlib
import datetime
from itertools import tee
import numpy as np
import os, csv

METERS_PER_DEGREE_LATITUDE = 111070.34306591158
METERS_PER_DEGREE_LONGITUDE = 83044.98918812413


def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def time_preprocess(trip, time_threshold=20):
    filtered_trip = []
    counter = 0
    for org, dest in pairwise(trip):
        delta = (dest[3]-org[3]).seconds
        filtered_trip.append(org)
        counter += 1
        if delta > time_threshold:
            break
        if counter == len(trip)-1:
            filtered_trip.append(dest)
    return filtered_trip


def thresh_determiner(obj_list, thresh_percent=0.95, n_bins=100):
    bin_values, edges = np.histogram(obj_list, bins=n_bins)
    bin_cum = np.cumsum(bin_values)
    bin_cum = bin_cum / bin_cum[-1]
    threshold = int(edges[np.argmin(abs(bin_cum - thresh_percent)) + 1])
    return threshold


def dist_measure(x, y):
    return np.sqrt(((x[0]-y[0])*METERS_PER_DEGREE_LONGITUDE)**2 + ((x[1]-y[1])*METERS_PER_DEGREE_LATITUDE)**2)


def spd_measure(x, y):
    return np.sqrt(((x[0]-y[0])*METERS_PER_DEGREE_LONGITUDE)**2 + ((x[1]-y[1])*METERS_PER_DEGREE_LATITUDE)**2)/max((y[3]-x[3]).seconds, 1)


def dist_preprocess(trip, max_dist_threshold=170, min_dist_threshold=5):
    filtered_trip = []
    while len(trip) > 1:
        org = trip.pop(0)
        delta = dist_measure(org, trip[0])
        if delta < min_dist_threshold:
            _ = trip.pop(0)
            trip.insert(0, org)
            continue
        filtered_trip.append(org)
        if delta > max_dist_threshold:
            break
        if len(trip) == 1:
            filtered_trip.append(trip.pop())
    return filtered_trip


def spd_preprocess(trip, max_spd_threshold=26, min_spd_threshold=2):
    #note: this function just filter data based on avergae speed between two points, not based on the point gps point speed
    filtered_trip = []
    counter = 0
    for org, dest in pairwise(trip):
        delta = spd_measure(org, dest)
        filtered_trip.append(org)
        counter += 1
        if delta > max_spd_threshold or delta < min_spd_threshold:
            break
        if counter == len(trip)-1:
            filtered_trip.append(dest)
    return filtered_trip


def preprocess(trip, **kwargs):
    temp_trip = time_preprocess(
        trip,
        kwargs['time_threshold'] if 'time_threshold' in kwargs else 20
    )
    temp_trip = dist_preprocess(
        temp_trip,
        kwargs['max_dist_threshold'] if 'max_dist_threshold' in kwargs else 170,
        kwargs['min_dist_threshold'] if 'min_dist_threshold' in kwargs else 5
    )
    temp_trip = spd_preprocess(
        temp_trip,
        kwargs['max_spd_threshold'] if 'max_spd_threshold' in kwargs else 26,
        kwargs['min_spd_threshold'] if 'min_spd_threshold' in kwargs else 2
    )
    return temp_trip


def modify_data(file_path, boundary, route_mapping, **kwargs):
    data = pd.read_parquet(file_path)
    trajectories = []
    temp_trip = []
    print(file_path)
    last_index = len(route_mapping)

    for i in range(len(data['device_id'])):
        point = wkb.loads(data.iloc[i]['location'], hex=True)
        if boundary['west'] < point.x < boundary['east'] and boundary['south'] < point.y < boundary['north']:
            temp_trip.append([
                point.x,
                point.y,
                data.iloc[i]['altitude'],
                datetime.datetime.fromtimestamp(int(data.iloc[i]['timestamp']) / 1000),
                data.iloc[i]['bearing'],
                data.iloc[i]['speed']
            ])
        else:
            continue

        if data.iloc[i]['route_slug'] != data.iloc[i+1]['route_slug']:
            if data.iloc[i]['route_slug'] in route_mapping.keys():
                route_id = route_mapping[data.iloc[i]['route_slug']]
            else:
                route_mapping[data.iloc[i]['route_slug']] = last_index
                route_id = last_index
                last_index += 1
            temp_trip = sorted(temp_trip, key=lambda x: x[2])
            temp_trip = preprocess(temp_trip, **kwargs)
            if len(temp_trip) > 1:
                trajectories.append(
                    (
                        # np.int64(int(hashlib.md5(data.iloc[i]['route_slug'].encode('utf-8')).hexdigest(), 16) % (10**9)),
                        route_id,
                        # sorted(temp_trip, key=lambda x: x[2])
                        temp_trip
                    )
                )
                temp_trip = []
    if len(trajectories) == 0:
        print('No bounded points')
    return trajectories, route_mapping


def load_data(file_path, boundary, file_dist):
    if os.path.exists(file_path) is not True:
        print('Path does not exists!')
        return
    prefix = ''.join(str(int(value)) for value in [
        boundary['west'], boundary['east'], boundary['south'], boundary['north']
    ])
    route_mapping = {}
    for dir_name in [x for x in os.listdir(file_path) if os.path.isdir(os.path.join(file_path, x)) and not x.startswith('.')]:
        if not os.path.exists(file_dist + '/' + prefix):
            os.makedirs(file_dist + '/' + prefix)
        files = sorted(os.listdir(os.path.join(file_path, dir_name)))
        for file in files:
            if not file.endswith('.parquet'):
                continue
            trajectories, route_mapping = modify_data(os.path.join(file_path, dir_name, file), boundary, route_mapping)
            if not trajectories:
                continue
            file_name = file_dist + '/' + prefix + '/' + file.split('.snappy')[0]+'.csv'
            with open(file_name, 'w') as csv_file:
                csv_writer = csv.writer(csv_file, delimiter=',', lineterminator='\n')
                csv_writer.writerow(['route_id', 'longitude', 'latitude', 'altitude', 'timestamp', 'bearing', 'speed'])
                for trajectory in trajectories:
                    for point in trajectory[1]:
                        csv_writer.writerow([trajectory[0]]+point)
    return file_dist


def make_trajs(file_path):
    if os.path.exists(file_path) is not True:
        print('Path does not exists!')
        return
    trajectories = []
    for dir_name in [x for x in os.listdir(file_path) if os.path.isdir(os.path.join(file_path, x)) and not x.startswith('.')]:
        files = sorted(os.listdir(os.path.join(file_path, dir_name)))
        for file in files:
            if not file.endswith('.csv'):
                continue
            data = pd.read_csv(os.path.join(file_path, dir_name, file), sep=',', header=0, engine='python')
            altitudes = []
            line = []
            bearings = []
            speeds = []
            for i in range(len(data)-1):
                point = data.iloc[i]
                line.append((point['longitude'], point['latitude']))
                altitudes.append(str(point['altitude']))
                bearings.append(str(point['bearing']))
                speeds.append(str(point['speed']))
                if point['route_id'] != data.iloc[i+1]['route_id']:
                    traj_line = LineString(line)
                    trajectories.append((point['route_id'], traj_line, ','.join(altitudes), ','.join(bearings), ','.join(speeds)))
                    line = []
                    bearings = []
                    speeds = []
    return trajectories


def trajToShape(source_path, dist_path):
    trajectories = make_trajs(source_path)
    df = pd.DataFrame(trajectories, columns=['id', 'geometry', 'latitude', 'bearing', 'speed'])
    df = gp.GeoDataFrame(df, geometry='geometry')
    df.to_file(dist_path, driver='ESRI Shapefile')