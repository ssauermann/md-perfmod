import argparse
import pickle
from collections import namedtuple

from os import path, makedirs


class Job:
    WorkloadManager = namedtuple('WorkloadManager', 'name directive name_args time_args time_formats stdout_args'
                                                    ' stderr_args directory_args')

    managers = {
        'Slurm': WorkloadManager(
            name='Slurm',
            directive='#SBATCH',
            name_args=['--job-name=(?<val>.*)', '-J\s+(?<val>.*)'],
            time_args=['--time=(?<val>.*)', '-t\s+(?<val>.*)'],
            time_formats=['%d-%H:%M:%S', '%d-%H:%M', '%d-%H', '%H:%M:%S', '%M:%S', '%M'],
            stdout_args=['--output=(?<val>.*)', '-o\s+(?<val>.*)'],
            stderr_args=['--error=(?<val>.*)', '-e\s+(?<val>.*)'],
            directory_args=['--chdir=(?<val>.*)', '-D\s+(?<val>.*)'],
        ),
        'LoadLeveler': WorkloadManager(
            name='LoadLeveler',
            directive='#@',
            name_args=['job_name\s*=\s*(?<val>.*)'],
            time_args=['wall_clock_limit\s*=\s*(?<val>.*)'],
            time_formats=['%H:%M:%S'],
            stdout_args=['output\s*=\s*(?<val>.*)'],
            stderr_args=['error\s*=\s*(?<val>.*)'],
            directory_args=['initialdir\s*=\s*(?<val>.*)'],
        ),
        # Add other workload managers here if needed
    }

    def __init__(self, directory, time, stdout, stderr, params):
        self.directory = directory
        self.time = time
        self.stdout = stdout
        self.stderr = stderr
        self.params = params

    @classmethod
    def from_file(cls, job_file, workload_manager=None):
        directory = abs_folder(job_file)
        # TODO


def read_args():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-s', '--storage-file', default='job_combine.storage',
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

def abs_folder(file = __file__):
    return path.dirname(path.realpath(path.expandvars(path.expanduser(file))))

def load(file):
    file_abs = path.join(abs_folder(), file)
    with open(file_abs, 'ab+') as f:
        try:
            f.seek(0)
            return pickle.load(f)
        except EOFError:
            return {}


def store(file, dic):
    file_abs = path.join(abs_folder(), file)
    with open(file_abs, 'wb+') as f:
        pickle.dump(dic, f)


def combine(scripts, stdout, stderr):
    combined = ''

    for job_file, task in scripts:
        folder = abs_folder(job_file)
        combined += 'cd %s\n' % folder # cd to folder of original script
        combined += '(%s) 1>%s 2>%s\n' % (task, stdout, stderr) # execute script in sub-shell and pipe output to files

    return combined


def queue(args):
    dic = load(args.storage_file)

    dir_counter = 0
    for k, v in dic.items():
        params = dict(k)
        combined = combine(v, params['output'], params['error'])  # TODO Time constraint -t
        script_dir = './scripts/%02i' % dir_counter
        dir_counter += 1
        makedirs(script_dir, exist_ok=True)
        with open('%s/submit.job' % script_dir, 'w+') as job:
            # print header
            job.write('#!/bin/bash -x\n')
            for p in params.items():
                print(p)
                if p[1] is None:
                    job.write('#SBATCH --%s\n' % p[0])
                elif p[0] == 'time':
                    time = to_slurm_time(from_slurm_time(p[1]) * len(v))
                    job.write('#SBATCH --time=%s\n' % time)
                else:
                    job.write('#SBATCH --%s=%s\n' % p)

            # print scripts
            job.write(combined)

        # TODO Call sbatch for script_dir/submit.job' % hash(k)
    print('Dispatched queue')


def add(args):
    dic = load(args.storage_file)

    key_list = []
    task = ''
    with open(args.job_file, 'r') as f:
        for line in f:
            if line.startswith('#SBATCH '):
                param = line.lstrip('#SBATCH --').rstrip('\n').split('=', maxsplit=1)
                param_key = param[0]
                param_val = param[1] if len(param) > 1 else ''
                key_list.append((param_key, param_val))
            elif not line.startswith('#'):
                task += line

    key_list.sort(key=lambda x: x[0])
    key = tuple(key_list)

    if key not in dic.keys():
        dic[key] = []
    dic[key].append((os.path.abspath(args.job_file), task))
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
    total_time_str = to_slurm_time(total_time)

    dif_tasks = len(dic)

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
