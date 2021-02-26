from graphdb_matcher import GraphDBMatcher
import spatialfunclib
import math

MAX_SPEED_M_PER_S = 20.0


class MatchGraphDB:
    def __init__(self, graphdb_filename, constraint_length, max_dist):
        self.matcher = GraphDBMatcher(graphdb_filename, constraint_length, max_dist)
        self.constraint_length = constraint_length

    def process_trip(self, trip_directory, trip_filename, output_directory):

        trip_file = open(trip_directory + "/" + trip_filename, 'r')
        raw_observations = [x.strip("\n").split(",")[1:4] for x in trip_file.readlines()]
        trip_file.close()

        V = None
        p = {}

        obs = []
        obs_states = []
        max_prob_p = None

        first_obs_lat, first_obs_lon, first_obs_time = raw_observations[0]

        V, p = self.matcher.step((float(first_obs_lat), float(first_obs_lon)), V, p)

        max_prob_state = max(V, key=lambda x: V[x])
        max_prob_p = p[max_prob_state]

        if len(max_prob_p) == self.constraint_length:
            obs_states.append(max_prob_p[0])

        obs.append((first_obs_lat, first_obs_lon, first_obs_time))

        for i in range(1, len(raw_observations)):
            (prev_lat, prev_lon, prev_time) = raw_observations[i - 1]
            (curr_lat, curr_lon, curr_time) = raw_observations[i]

            prev_time = float(prev_time)
            curr_time = float(curr_time)

            elapsed_time = (curr_time - prev_time)

            distance = spatialfunclib.distance((float(prev_lat), float(prev_lon)), (float(curr_lat), float(curr_lon)))

            if distance > 10.0:
                int_steps = int(math.ceil(distance / 10.0))
                int_step_distance = (distance / float(int_steps))
                int_step_time = (float(elapsed_time) / float(int_steps))

                for j in range(1, int_steps):
                    step_fraction_along = ((j * int_step_distance) / distance)
                    (int_step_lat, int_step_lon) = spatialfunclib.point_along_line(float(prev_lat), float(prev_lon),
                                                                                   float(curr_lat), float(curr_lon),
                                                                                   step_fraction_along)

                    V, p = self.matcher.step((float(int_step_lat), float(int_step_lon)), V, p)

                    max_prob_state = max(V, key=lambda x: V[x])
                    max_prob_p = p[max_prob_state]

                    if len(max_prob_p) == self.constraint_length:
                        obs_states.append(max_prob_p[0])

                    obs.append((int_step_lat, int_step_lon, (float(prev_time) + (float(j) * int_step_time))))

            V, p = self.matcher.step((float(curr_lat), float(curr_lon)), V, p)

            max_prob_state = max(V, key=lambda x: V[x])
            max_prob_p = p[max_prob_state]

            if len(max_prob_p) == self.constraint_length:
                obs_states.append(max_prob_p[0])

            obs.append((curr_lat, curr_lon, curr_time))

        if len(max_prob_p) < self.constraint_length:
            obs_states.extend(max_prob_p)
        else:
            obs_states.extend(max_prob_p[1:])

        # print "obs: " + str(len(obs))
        # print "obs states: " + str(len(obs_states))
        assert (len(obs_states) == len(obs))

        out_file = open(output_directory + "/matched_" + trip_filename, 'w')

        for i in range(0, len(obs)):
            obs_lat, obs_lon, obs_time = obs[i]
            out_file.write(str(obs_lat) + " " + str(obs_lon) + " " + str(obs_time) + " ")

            if obs_states[i] == "unknown":
                out_file.write(str(obs_states[i]) + "\n")
            else:
                in_node_coords, out_node_coords = obs_states[i]
                out_file.write(
                    str(in_node_coords[0]) + " " + str(in_node_coords[1]) + " " + str(out_node_coords[0]) + " " + str(
                        out_node_coords[1]) + "\n")

        out_file.close()


import sys, getopt
import os

# if __name__ == '__main__':
#
#     graphdb_filename = "skeleton_maps/skeleton_map_7m.db"
#     constraint_length = 300
#     max_dist = 350
#     trip_directory = "trips/trips_7m/"
#     output_directory = "trips/matched_trips_7m/"
#
#     opts, args = getopt.getopt(sys.argv[1:], "c:m:d:t:o:h")
#
#     for o, a in opts:
#         if o == "-c":
#             constraint_length = int(a)
#         elif o == "-m":
#             max_dist = int(a)
#         elif o == "-d":
#             graphdb_filename = str(a)
#         elif o == "-t":
#             trip_directory = str(a)
#         elif o == "-o":
#             output_directory = str(a)
#         elif o == "-h":
#             print(
#                 "Usage: python graphdb_matcher_run.py [-c <constraint_length>] [-m <max_dist>] [-d <graphdb_filename>] [-t <trip_directory>] [-o <output_directory>] [-h]")
#             exit()
#
#     print("constraint length: " + str(constraint_length))
#     print("max dist: " + str(max_dist))
#     print("graphdb filename: " + str(graphdb_filename))
#     print("trip directory: " + str(trip_directory))
#     print("output directory: " + str(output_directory))
#
#     match_graphdb = MatchGraphDB(graphdb_filename, constraint_length, max_dist)
#
#     all_trip_files = [x for x in os.listdir(trip_directory) if x.startswith("trip_") and x.endswith(".txt")]
#
#     for i in range(0, len(all_trip_files)):
#         # sys.stdout.write("\rProcessing trip " + str(i + 1) + "/" + str(len(all_trip_files)) + "... ")
#         # sys.stdout.flush()
#         print("\rProcessing trip " + str(i + 1) + "/" + str(len(all_trip_files)) + "... ")
#
#         match_graphdb.process_trip(trip_directory, all_trip_files[i], output_directory)
#
#     # sys.stdout.write("done.\n")
#     # sys.stdout.flush()
#     print("done.\n")












from streetmap import StreetMap
from pylibs import spatialfunclib
import sqlite3
import math


class ProcessMapMatches:
    def __init__(self):
        pass

    def process(self, graphdb_filename, matched_trips_directory, output_db_filename, output_traces_filename):
        all_segment_obs = self.process_all_matched_trips(graphdb_filename, matched_trips_directory, output_db_filename)
        self.coalesce_segments(output_db_filename, output_traces_filename, all_segment_obs)

    def coalesce_segments(self, output_db_filename, output_traces_filename, all_segment_obs):
        self.graphdb = StreetMap()
        self.graphdb.load_graphdb(output_db_filename)

        # sys.stdout.write("Coalescing segments... ")
        # sys.stdout.flush()
        print("Coalescing segments... ")

        while True:
            merge_segments = []

            for segment in list(self.graphdb.segments.values()):
                head_edge_neighbors = list(
                    set(segment.head_edge.in_node.in_nodes + segment.head_edge.in_node.out_nodes))
                tail_edge_neighbors = list(
                    set(segment.tail_edge.out_node.out_nodes + segment.tail_edge.out_node.in_nodes))

                if segment.head_edge.out_node in head_edge_neighbors:
                    head_edge_neighbors.remove(segment.head_edge.out_node)

                if segment.tail_edge.in_node in tail_edge_neighbors:
                    tail_edge_neighbors.remove(segment.tail_edge.in_node)

                if (len(head_edge_neighbors) != 1) and (len(tail_edge_neighbors) == 1):
                    edge_key = (segment.tail_edge.out_node, tail_edge_neighbors[0])

                    if edge_key in self.graphdb.edge_lookup_table:
                        next_edge = self.graphdb.edge_lookup_table[edge_key]
                        next_segment = next_edge.segment  # self.graphdb.segment_lookup_table[next_edge.id]
                        merge_segments.append((segment, next_segment))

            # print "merge segments: " + str(len(merge_segments))
            if len(merge_segments) == 0: break

            for head_segment, tail_segment in merge_segments:
                head_segment.edges.extend(tail_segment.edges)

                for edge in tail_segment.edges:
                    edge.segment = head_segment  # self.graphdb.segment_lookup_table[edge.id] = head_segment

                del self.graphdb.segments[tail_segment.id]

        # sys.stdout.write("done.\n")
        # sys.stdout.flush()
        print("done.\n")

        # sys.stdout.write("Saving traces... ")
        # sys.stdout.flush()
        print("Saving traces... ")

        output_traces_file = open(output_traces_filename, 'w')

        for segment_id in all_segment_obs:
            segment_traces = all_segment_obs[segment_id]

            if len(segment_traces) > 1:
                for segment_trace in segment_traces:
                    for obs in segment_trace:
                        edge_id, obs_lat, obs_lon, obs_time = obs
                        curr_segment_id = self.graphdb.edges[edge_id].segment.id
                        output_traces_file.write(
                            str(curr_segment_id) + "," + str(edge_id) + "," + str(obs_lat) + "," + str(
                                obs_lon) + "," + str(obs_time) + "\n")
                    output_traces_file.write("\n")
        output_traces_file.close()

        # sys.stdout.write("done.\n")
        # sys.stdout.flush()
        print("done.\n")

        # sys.stdout.write("Saving coalesced map... ")
        # sys.stdout.flush()
        print("Saving coalesced map... ")

        try:
            os.remove(output_db_filename)
        except OSError:
            pass

        conn = sqlite3.connect(output_db_filename)
        cur = conn.cursor()

        cur.execute("CREATE TABLE nodes (id INTEGER, latitude FLOAT, longitude FLOAT, weight FLOAT)")
        cur.execute("CREATE TABLE edges (id INTEGER, in_node INTEGER, out_node INTEGER, weight FLOAT)")
        cur.execute("CREATE TABLE segments (id INTEGER, edge_ids TEXT)")
        cur.execute("CREATE TABLE intersections (node_id INTEGER)")
        conn.commit()

        valid_nodes = set()
        valid_intersections = set()

        for segment in list(self.graphdb.segments.values()):
            cur.execute("INSERT INTO segments VALUES (" + str(segment.id) + ",'" + str(
                [edge.id for edge in segment.edges]) + "')")

            segment_weight = min([edge.weight for edge in segment.edges])
            # print map(lambda edge: edge.weight, segment.edges), min(map(lambda edge: edge.weight, segment.edges))

            for edge in segment.edges:
                cur.execute("INSERT INTO edges VALUES (" + str(edge.id) + "," + str(edge.in_node.id) + "," + str(
                    edge.out_node.id) + "," + str(segment_weight) + ")")

                valid_nodes.add(edge.in_node)
                valid_nodes.add(edge.out_node)

        for node in valid_nodes:
            cur.execute("INSERT INTO nodes VALUES (" + str(node.id) + "," + str(node.latitude) + "," + str(
                node.longitude) + "," + str(node.weight) + ")")

            if node.id in self.graphdb.intersections:
                cur.execute("INSERT INTO intersections VALUES (" + str(node.id) + ")")

        conn.commit()
        conn.close()

        # sys.stdout.write("done.\n")
        # sys.stdout.flush()
        print("done.\n")

    def process_all_matched_trips(self, graphdb_filename, matched_trips_directory, output_db_filename):
        self.graphdb = StreetMap()
        self.graphdb.load_graphdb(graphdb_filename)

        all_matched_trip_files = [x for x in os.listdir(matched_trips_directory) if
                                  x.startswith("matched_trip_") and x.endswith(".txt")]

        all_segment_obs = {}  # indexed by segment_id

        for i in range(0, len(all_matched_trip_files)):
            # sys.stdout.write("\rProcessing matched trip " + str(i + 1) + "/" + str(len(all_matched_trip_files)) + "... ")
            # sys.stdout.flush()
            print("\rProcessing matched trip " + str(i + 1) + "/" + str(len(all_matched_trip_files)) + "... ")

            matched_trip_file = open(matched_trips_directory + "/" + all_matched_trip_files[i], 'r')
            matched_trip_records = [x.strip("\n").split(" ") for x in matched_trip_file.readlines()]
            matched_trip_file.close()

            curr_trip_obs = []
            no_obs_time_ranges = []

            for record in matched_trip_records:
                if len(record) < 7:
                    obs_lat, obs_lon, obs_time, unknown_state = record

                    # observation blackout +/- 30 secconds of 'unknown' state observation time
                    no_obs_time_ranges.append((float(obs_time) - 30.0, float(obs_time) + 30.0))

                else:
                    obs_lat, obs_lon, obs_time, state_in_node_lat, state_in_node_lon, state_out_node_lat, state_out_node_lon = record
                    curr_state_edge = self.graphdb.edge_coords_lookup_table[
                        (float(state_in_node_lat), float(state_in_node_lon)), (
                        float(state_out_node_lat), float(state_out_node_lon))]
                    curr_trip_obs.append((curr_state_edge.id, obs_lat, obs_lon, obs_time))

            if len(no_obs_time_ranges) > 0:
                clean_trip_obs = []

                # skip observations that fall in the "no observations" time windows
                for trip_obs in curr_trip_obs:
                    edge_id, obs_lat, obs_lon, obs_time = trip_obs

                    skip_obs = False
                    for no_obs_time_range in no_obs_time_ranges:
                        if no_obs_time_range[0] <= float(obs_time) <= no_obs_time_range[1]:
                            skip_obs = True
                            break

                    if skip_obs is False:
                        clean_trip_obs.append(trip_obs)

                curr_trip_obs = clean_trip_obs

            prev_segment_id = None
            curr_segment_obs = None

            for trip_obs in curr_trip_obs:
                edge_id, obs_lat, obs_lon, obs_time = trip_obs

                curr_segment = self.graphdb.edges[edge_id].segment  # segment_lookup_table[edge_id]

                if curr_segment.id not in all_segment_obs:
                    all_segment_obs[curr_segment.id] = []

                if curr_segment.id != prev_segment_id:
                    if prev_segment_id is not None:
                        all_segment_obs[prev_segment_id].append(curr_segment_obs)
                    curr_segment_obs = []

                curr_segment_obs.append((edge_id, obs_lat, obs_lon, obs_time))
                prev_segment_id = curr_segment.id

        #
        # At this point, we're done processing all map-matched trips
        #
        # sys.stdout.write("done.\n")
        # sys.stdout.flush()
        print("done.\n")

        segment_counter = 1

        # clean up segment-matched traces
        for segment_id in all_segment_obs:
            # sys.stdout.write("\rPost-processing map-matched segment " + str(segment_counter) + "/" + str(len(all_segment_obs)) + "... ")
            # sys.stdout.flush()
            print("\rPost-processing map-matched segment " + str(segment_counter) + "/" + str(
                len(all_segment_obs)) + "... ")

            segment_counter += 1

            good_segment_traces = []

            for trace in all_segment_obs[segment_id]:

                trace_error = 0.0

                for obs in trace:
                    edge_id, obs_lat, obs_lon, obs_time = obs
                    edge = self.graphdb.edges[edge_id]

                    obs_lat = float(obs_lat)
                    obs_lon = float(obs_lon)

                    # sanity check
                    if edge not in self.graphdb.segments[segment_id].edges:
                        print("ERROR!! Edge (" + str(edge_id) + ") not in segment (" + str(segment_id) + ") edge list!")
                        exit()

                    _, _, projected_dist = spatialfunclib.projection_onto_line(edge.in_node.latitude,
                                                                               edge.in_node.longitude,
                                                                               edge.out_node.latitude,
                                                                               edge.out_node.longitude, obs_lat,
                                                                               obs_lon)
                    trace_error += projected_dist ** 2

                trace_rmse = math.sqrt(float(trace_error) / float(len(trace)))

                if trace_rmse <= 10.0:
                    good_segment_traces.append(trace)

            all_segment_obs[segment_id] = good_segment_traces

        # sys.stdout.write("done.\n")
        # sys.stdout.flush()
        print("done.\n")

        # sys.stdout.write("Saving new map... ")
        # sys.stdout.flush()
        print("Saving new map... ")

        try:
            os.remove(output_db_filename)
        except OSError:
            pass

        conn = sqlite3.connect(output_db_filename)
        cur = conn.cursor()

        cur.execute("CREATE TABLE nodes (id INTEGER, latitude FLOAT, longitude FLOAT, weight FLOAT)")
        cur.execute("CREATE TABLE edges (id INTEGER, in_node INTEGER, out_node INTEGER, weight FLOAT)")
        cur.execute("CREATE TABLE segments (id INTEGER, edge_ids TEXT)")
        cur.execute("CREATE TABLE intersections (node_id INTEGER)")
        conn.commit()

        valid_nodes = set()
        valid_intersections = set()

        for segment_id in all_segment_obs:
            num_segment_traces = len(all_segment_obs[segment_id])

            if num_segment_traces > 1:
                segment = self.graphdb.segments[segment_id]

                cur.execute("INSERT INTO segments VALUES (" + str(segment.id) + ",'" + str(
                    [edge.id for edge in segment.edges]) + "')")

                for edge in segment.edges:
                    cur.execute("INSERT INTO edges VALUES (" + str(edge.id) + "," + str(edge.in_node.id) + "," + str(
                        edge.out_node.id) + "," + str(num_segment_traces) + ")")

                    valid_nodes.add(edge.in_node)
                    valid_nodes.add(edge.out_node)

        for node in valid_nodes:
            cur.execute("INSERT INTO nodes VALUES (" + str(node.id) + "," + str(node.latitude) + "," + str(
                node.longitude) + "," + str(node.weight) + ")")

            if node.id in self.graphdb.intersections:
                cur.execute("INSERT INTO intersections VALUES (" + str(node.id) + ")")

        conn.commit()
        conn.close()

        # sys.stdout.write("done.\n")
        # sys.stdout.flush()
        print("done.\n")

        return all_segment_obs


import sys, getopt
import os

if __name__ == '__main__':
    graphdb_filename = "skeleton_maps/skeleton_map_7m.db"
    matched_trips_directory = "trips/matched_trips_7m/"
    output_filename = "skeleton_maps/skeleton_map_7m_mm1.db"

    opts, args = getopt.getopt(sys.argv[1:], "d:t:o:h")

    for o, a in opts:
        if o == "-d":
            graphdb_filename = str(a)
        elif o == "-t":
            matched_trips_directory = str(a)
        elif o == "-o":
            output_filename = str(a)
        elif o == "-h":
            print(
                "Usage: python process_map_matches.py [-d <graphdb_filename>] [-t <matched_trips_directory>] [-o <output_filename>] [-h]")
            exit()

    print("graphdb filename: " + str(graphdb_filename))
    print("matched trips directory: " + str(matched_trips_directory))
    print("output filename: " + str(output_filename))

    p = ProcessMapMatches()
    p.process(graphdb_filename, matched_trips_directory, output_filename, output_filename.replace(".db", "_traces.txt"))