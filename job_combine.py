import argparse
import pickle

import os


def read_args():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-s', '--storage-file', default='sbatch.storage',
                        help='Path to the file the added scripts are stored [default: %(default)s]')
    parser.add_argument('-v', '--verbose', action='count', help='Enables verbose output')

    subparsers = parser.add_subparsers(help='')

    parser_queue = subparsers.add_parser('queue', help='')
    parser_add = subparsers.add_parser('add', help='')
    parser_status = subparsers.add_parser('status', help='')
    parser_clear = subparsers.add_parser('clear', help='')

    parser_queue.set_defaults(func=queue)
    parser_add.set_defaults(func=add)
    parser_status.set_defaults(func=status)
    parser_clear.set_defaults(func=clear)

    parser_add.add_argument('job_file', help='Job file containing a single task')
    parser_queue.add_argument('-t', '--time-limit', help='Max time for a single combined job')

    mode = parser.parse_args()

    if mode.verbose is None:
        mode.verbose = 0

    mode.func(mode)


def load(file):
    with open(file, 'ab+') as f:
        try:
            f.seek(0)
            return pickle.load(f)
        except EOFError:
            return {}


def store(file, dic):
    with open(file, 'wb+') as f:
        pickle.dump(dic, f)


def queue(args):
    print('Dispatched queue')
    # TODO Implement


def add(args):
    dic = load(args.storage_file)

    key_list = []
    task = args.job_file
    with open(args.job_file, 'r') as f:
        for line in f:
            if line.startswith('#SBATCH '):
                param = line.lstrip('#SBATCH --').rstrip('\n').split('=', maxsplit=1)
                param_key = param[0]
                param_val = param[1] if len(param) > 1 else ''
                key_list.append((param_key, param_val))

    key_list.sort(key=lambda x: x[0])
    key = tuple(key_list)

    if key not in dic.keys():
        dic[key] = []
    dic[key].append(task)
    store(args.storage_file, dic)
    print('Added new entry')


def to_slurm_time(time):
    # support only HH:MM:SS
    m, s = divmod(time, 60)
    h, m = divmod(m, 60)
    return "%i:%i:%i" % (h, m, s)


def from_slurm_time(time_str):  # TODO not all valid time formats of slurm scripts covered
    d = 0
    if '-' in time_str:
        d, time_str = time_str.rsplit('-')
    h, m, s = time_str.split(':')
    return int(d) * 24 * 3600 + int(h) * 3600 + int(m) * 60 + int(s)


def status(args):
    dic = load(args.storage_file)
    n_tasks = sum([len(v) for v in dic.values()])
    total_time = 0
    for k, v in dic.items():
        time_str = next(param_value for (param_key, param_value) in k if param_key == 'time')
        time_sec = from_slurm_time(time_str)
        total_time += time_sec * len(v)
    dif_tasks = len(dic)

    total_time_str = to_slurm_time(total_time)
    print('Stored %i tasks with a total time of %s combinable to %i tasks.' % (n_tasks, total_time_str, dif_tasks))
    if int(args.verbose) >= 1:
        l = []
        for k in dic.keys():
            for p, _ in k:
                l.append(p)
        print('\nParameters considered for combining runs:\n', set(l))
    if int(args.verbose) >= 2:
        print('\n', dic)


def clear(args):
    os.remove(args.storage_file)
    print('Deleted storage file.')


def main():
    read_args()


if __name__ == "__main__":
    main()
