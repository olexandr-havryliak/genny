# /bin/python
# You may need to pip install some of the imports below if you don't have them already

import argparse
import itertools
import os
import re
import subprocess
import sys
import threading
import pandas

import matplotlib.pyplot as plot

default_metrics_path = 'build/WorkloadOutput/CedarMetrics'

def parse_args():
    parser = argparse.ArgumentParser(
        prog='test_result_summary.py',
        description='''
This script analyzes the genny perf results and draws graph.''',

        epilog='''
Please feel free to update this script to handle your metris or to adjust the output to something
you consider more useful.''')
    parser.add_argument(
        '-a',
        '--actorRegex',
        help="""An optional regex to apply to filter out processing results for certain actors.
        The results for ExampleActor will be stored in something like
        '.../WorkloadOutput/CedarMetrics/ExampleActor.ftdc. Your regex should assume it is working
        with just the actor name: "ExampleActor" in this case.""")

    parser.add_argument(
        '-o',
        '--outputGraphName',
        default='graph.png',
        help="""File name for the graph""")

    return parser.parse_args()

def parse_actor_regex(args):
    actor_regex = re.compile('.*')  # Match all actors by default.
    if args.actorRegex is not None:
        try:
            actor_regex = re.compile(args.actorRegex)
        except:
            print("Unable to translate provided regex: ", args.actorRegex)
            raise

    return actor_regex

def path_to_string(path_component_array):
    return os.path.sep.join(path_component_array)

def find_ftdc_files(metrics_path):
    ls_results = [path_to_string(metrics_path + [file])
                  for file in os.listdir(path_to_string(metrics_path))]
    return [path_str
            for path_str in ls_results if os.path.isfile(path_str) and path_str.endswith(".ftdc")]

def replace_suffix(string, suffixTarget, newSuffix):
    assert string.endswith(suffixTarget)
    suffix_start = string.rfind(suffixTarget)
    return string[0:suffix_start] + newSuffix

def convert_to_csv(actor_file):
    tmp_file_location = replace_suffix(actor_file, ".ftdc", ".csv")
    if (os.path.exists(tmp_file_location)):
        return tmp_file_location

    sub_result = subprocess.run(
        ["./build/curator/curator", "ftdc", "export", "csv", "--input", actor_file, "--output", tmp_file_location])
    assert sub_result.returncode == 0
    return tmp_file_location

def extract_actor_name(actor_file):
    return actor_file[actor_file.rfind('/') + 1:actor_file.rfind('.')]

def main():
    args = parse_args()
    actor_regex = parse_actor_regex(args)

    metrics_path = default_metrics_path.split(os.path.sep)
    result_ftdc_files = find_ftdc_files(metrics_path)

    if result_ftdc_files == []:
        raise AssertionError("No results found for graph")

    df = {}
    events_per_sec_total = {}
    events_per_sec_dur = {}
    summary = pandas.DataFrame()
    interval_size = 10**9 #nanosecond to seconds
    plot.figure(figsize=(20, 12))

    for actor_file in result_ftdc_files:
        actor_name = extract_actor_name(actor_file)
        if actor_regex.match(actor_name) is None:
            continue
        try:
            tmp_file = convert_to_csv(actor_file)
            df[actor_name] = pandas.read_csv(tmp_file)
            # for graph we need timers.total
            df[actor_name]['interval_total'] = df[actor_name]['timers.total'] // interval_size
            events_per_sec_total[actor_name] = df[actor_name].groupby('interval_total').size()
            plot.plot(events_per_sec_total[actor_name].index, events_per_sec_total[actor_name].values,label=actor_name)
            # for summary we need timers.dur
            df[actor_name]['interval_dur'] = df[actor_name]['timers.dur'] // interval_size
            events_per_sec_dur[actor_name] = df[actor_name].groupby('interval_dur').size()
            summary[actor_name] = events_per_sec_dur[actor_name].describe()
        except pandas.errors.EmptyDataError:
            continue

    #transpose index and columns for summary
    summary = summary.transpose()
    summary.rename(columns={'count': 'duration(seconds)', 'mean': 'mean(events/sec)','std': 'std(events/sec)','max': 'max(events/sec)', 'min': 'min(events/sec)'}, inplace=True)
    print(summary)

    #draw the graph
    plot.xlabel('Time seconds')
    plot.ylabel('Events/sec')
    plot.legend()
    plot.grid(True)
    plot.tight_layout()
    graph_path = path_to_string(metrics_path + [args.outputGraphName])
    plot.savefig(graph_path)

if __name__ == "__main__":
    main()
