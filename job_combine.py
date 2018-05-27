import argparse
import pickle
from collections import namedtuple, defaultdict
from datetime import datetime
from datetime import timedelta

import os
import re
from os import path


class Job:
    WorkloadManager = namedtuple('WorkloadManager', 'name directive name_args time_args time_formats stdout_args'
                                                    ' stderr_args directory_args arg_regex flag_regex arg_format'
                                                    ' flag_format')

    managers = {
        'Slurm': WorkloadManager(
            name='Slurm',
            directive='#SBATCH',
            name_args=['job-name', 'J'],
            time_args=['time', 't'],
            time_formats=['%d-%H:%M:%S', '%d-%H:%M', '%d-%H', '%H:%M:%S', '%M:%S', '%M'],
            stdout_args=['output', 'o'],
            stderr_args=['error', 'e'],
            directory_args=['chdir', 'D'],
            arg_regex=['--(?<arg>.+?)=(?<val>.*?)[\ \t]*$', '(?<!-)-(?!-)(?<arg>.+?)[\ \t]+(?<val>.+?)[\ \t]*$'],
            flag_regex=['--(?<arg>[^=\ ]+?)[\ \t]*$', '(?<!-)-(?!-)(?<arg>[^=\ ]+?)[\ \t]*$'],
            arg_format=['--%s=%s', '-%s %s'],
            flag_format=['--%s', '-%s'],
        ),
        'LoadLeveler': WorkloadManager(
            name='LoadLeveler',
            directive='#@',
            name_args=['job_name'],
            time_args=['wall_clock_limit'],
            time_formats=['%H:%M:%S'],
            stdout_args=['output'],
            stderr_args=['error'],
            directory_args=['initialdir'],
            arg_regex=['(?<=[\ \t])(?<arg>.+?)[\ \t]*=[\ \t]*(?<val>.+?)[\ \t]*$'],
            flag_regex=['^#@[\ \t]+(?<arg>[^=\ ]+?)[\ \t]*$'],
            arg_format=['%s = %s'],
            flag_format=['%s'],
        ),
        # Add other workload managers here if needed.
        # Lists have to be of the same length. Use None to fill missing values.
        # Regex expressions are applied to the complete line including the directive
        # Capture groups must be named 'arg' and 'val' for the arg_regex and 'arg' for the flag_regex
    }

    def __init__(self, name, directory, time, stdout, stderr, params, manager):
        self.name = name
        self.directory = directory
        self.time = time
        self.stdout = stdout
        self.stderr = stderr
        self.params = params
        self.manager = manager

    def __hash__(self):
        return hash((self.manager, self.params))

    def __eq__(self, other):
        return (self.manager, self.params) == (other.manager, other.params)

    def __ne__(self, other):
        return not (self == other)

    @staticmethod
    def str_to_timedelta(time_str, formats):
        """
        Converts a string representation to a time delta
        :param time_str: Time string
        :param formats: Time format
        :return: Time delta
        """
        epoch = datetime.utcfromtimestamp(0)
        time = None

        # find the first matching time format
        for f in formats:
            try:
                time = datetime.strptime(time_str, f)
                break
            except ValueError:
                pass

        # no format matched
        if time is None:
            raise ValueError('Not a supported time format: `%s`' % time_str)

        return time - epoch

    @staticmethod
    def str_from_timedelta(time_delta, time_format):
        """
        Converts a time delta to a string representation
        :param time_delta: Time delta
        :param time_format: Time format
        :return: Time string
        """
        epoch = datetime.utcfromtimestamp(0)
        time = epoch + time_delta
        return time.strftime(time_format)

    @classmethod
    def from_file(cls, job_file, workload_manager=None):
        """
        Parses a job file to a Job object
        :param job_file: Path to the job file
        :param workload_manager: Name of the workload manager this script is for
        :return: Job object
        """
        try:
            manager = Job.managers[workload_manager]
        except KeyError:
            raise ValueError("Workload manager not supported: %s" % workload_manager)

        directory = abs_folder(job_file)
        name = None
        time = timedelta()  # zero
        stdout = None
        stderr = None
        params = []

        with open(job_file, 'r') as f:
            for line in f:
                if line.startswith('#!'):  # shebang
                    pass
                elif line.startswith('# '):  # comment, can not be a job directive
                    pass
                elif line.startswith('#'):  # directive

                    # infer workload manager via directive
                    if manager is None:
                        for wm in Job.managers.values():
                            if line.startswith(wm.directive):
                                manager = wm
                                break

                    if not line.startswith(manager.directive):
                        # assume line is a comment as it is no shebang and is not matching the current directive
                        continue

                    # apply all arg and flag regex' to the line
                    matches = (re.search(regex, line) for regex in manager.arg_regex + manager.flag_regex)

                    # get the first successful match
                    match = next((match for match in matches if match is not None), None)

                    # no valid match -> can not continue
                    if match is None:
                        raise RuntimeError('Can not process directive `%s`' % line)

                    # get matching results from capture groups; val is None for flags
                    arg, val = match.group('arg', 'val')

                    if arg in manager.time_args:
                        time = Job.str_to_timedelta(val, manager.time_formats)
                    elif arg in manager.stdout_args:
                        stdout = val
                    elif arg in manager.stderr_args:
                        stderr = val
                    elif arg in manager.directory_args:
                        # working dir could be given relative to job file
                        d = path.expandvars(path.expanduser(arg))  # expand ~/ or env. variables
                        if path.isabs(d):
                            directory = d
                        else:
                            directory = path.join(directory, d)
                    elif arg in manager.name_args:
                        name = val
                    else:
                        # Store argument, value pair to be able to decide which scripts can be combined
                        params.append((arg, val))

                else:  # script lines
                    pass

        # sort parameter list [(arg, val)...] by arg and convert to a tuple
        params = (sorted(params, key=lambda x: x[0]))

        if manager is None:
            raise ValueError('`%s` is not a supported job file' % job_file)

        return cls(name, directory, time, stdout, stderr, params, manager.name)


def read_args():
    parser = argparse.ArgumentParser(description='Combines multiple job files into a single job.')
    subparsers = parser.add_subparsers(help='Select the operation to perform')

    parser_queue = subparsers.add_parser('queue', help='Combines currently stored jobs to as few as possible job files '
                                                       'and dispatches them to the queue of the workload manager')
    parser_add = subparsers.add_parser('add', help='Add a job for combination with the other stored jobs')
    parser_status = subparsers.add_parser('status', help='Displays information about the currently stored jobs and'
                                                         ' which can be combined')
    parser_clear = subparsers.add_parser('clear', help='Removes all currently stored jobs')

    parser_queue.set_defaults(func=queue)
    parser_add.set_defaults(func=add)
    parser_status.set_defaults(func=status)
    parser_clear.set_defaults(func=clear)

    # Arguments for all modes
    parser.add_argument('-s', '--storage-file', default='job_combine.storage',
                        help='Path to the file the added scripts are stored [default: %(default)s]')
    parser.add_argument('-v', '--verbose', action='count', help='Increases verbosity level')

    # Arguments for 'add'
    parser_add.add_argument('job_file', help='Job file containing a single task')
    parser_add.add_argument('-w', '--workload-manager', help='Specifies the type of the job file. Will be inferred from'
                                                             ' the directives in the file, if not set. Valid values are'
                                                             ': [%s]' % (', '.join(Job.managers.keys())))

    # Arguments for 'queue'
    parser_queue.add_argument('-t', '--max-time', help='No combined job will have a runtime longer than this value')
    parser_queue.add_argument('-m', '--min-time', help='No combined job will have a runtime with less than this value')
    parser_queue.add_argument('-p', '--parallel', default=1,
                              help='Tries to distribute the jobs equally to `p` scripts. Scripts that can not be'
                                   ' combined may increase and constraints may reduce the number of created'
                                   ' script files. [default: %(default)i]')

    # Arguments for 'status'

    # Arguments for 'clear'

    mode = parser.parse_args()

    if mode.verbose is None:
        mode.verbose = 0

    mode.func(mode)


def abs_folder(file=__file__):
    return path.dirname(path.realpath(path.expandvars(path.expanduser(file))))


def load(file):
    file_abs = path.join(abs_folder(), file)
    with open(file_abs, 'ab+') as f:
        try:
            f.seek(0)
            return pickle.load(f)
        except EOFError:
            return defaultdict(list)


def store(file, dic):
    file_abs = path.join(abs_folder(), file)
    with open(file_abs, 'wb+') as f:
        pickle.dump(dic, f)


def combine(scripts, stdout, stderr):
    """
    Combines the body of multiple job scripts into a single body where every script
     is executed in a separate sub shell in the same folder as the original script.
    :param scripts: List of (script path, script body) tuples
    :param stdout: File for the std out
    :param stderr:
    :return:
    """
    combined = ''

    for job_file, task in scripts:
        folder = abs_folder(job_file)
        combined += 'cd %s\n' % folder  # cd to folder of original script
        combined += '(%s) 1>%s 2>%s\n' % (task, stdout, stderr)  # execute script in sub-shell and pipe output to files

    return combined


def queue(args):
    current_jobs = load(args.storage_file)

    dir_counter = 0
    for k, v in dic.items():
        params = dict(k)
        combined = combine(v, params['output'], params['error'])  # TODO Time constraint -t
        script_dir = './scripts/%02i' % dir_counter
        dir_counter += 1
        os.makedirs(script_dir, exist_ok=True)
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
    current_jobs = load(args.storage_file)

    job = Job.from_file(args.job_file, args.workload_manager)
    current_jobs[job].append(job)

    store(args.storage_file, current_jobs)
    print('Added new entry')


def status(args):
    jobs = load(args.storage_file)
    n_jobs = sum([len(v) for v in jobs.values()])
    times = [Job.str_from_timedelta(sum(job.time for job in v), k.manager) for k, v in jobs.items()]

    min_combined_jobs = len(jobs)

    print('Stored %i jobs that can be combined to %i tasks with the times [%s].'
          % (n_jobs, min_combined_jobs, ', '.join(times)))

    if int(args.verbose) >= 1:
        print('\n', jobs.items())


def clear(args):
    os.remove(args.storage_file)
    print('Deleted storage file.')


def main():
    read_args()


if __name__ == "__main__":
    main()
