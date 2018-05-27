import argparse
import pickle
from collections import namedtuple, defaultdict
from datetime import datetime
from datetime import timedelta
from difflib import SequenceMatcher

import os
import re
from os import path


class Job:
    WorkloadManager = namedtuple('WorkloadManager',
                                 'name dispatch_command directive name_args time_args time_formats stdout_args'
                                 ' stderr_args directory_args arg_regex flag_regex arg_format'
                                 ' flag_format')

    managers = {
        'Slurm': WorkloadManager(
            name='Slurm',
            dispatch_command='sbatch',
            directive='#SBATCH',
            name_args=['job-name', 'J'],
            time_args=['time', 't'],
            time_formats=[
                # '%d-%H:%M:%S', '%d-%H:%M', '%d-%H', # TODO Date does not work with the value zero
                '%H:%M:%S', '%M:%S', '%M'
            ],
            stdout_args=['output', 'o'],
            stderr_args=['error', 'e'],
            directory_args=['chdir', 'D'],
            arg_regex=['--(?P<arg>.+?)=(?P<val>.*?)[\ \t]*$', '(?<!-)-(?!-)(?P<arg>.+?)[\ \t]+(?P<val>.+?)[\ \t]*$'],
            flag_regex=['--(?P<arg>[^=\ ]+?)[\ \t]*$', '(?<!-)-(?!-)(?P<arg>[^=\ ]+?)[\ \t]*$'],
            arg_format=['--%s=%s', '-%s %s'],
            flag_format=['--%s', '-%s'],
        ),
        'LoadLeveler': WorkloadManager(
            name='LoadLeveler',
            dispatch_command='llsubmit',
            directive='#@',
            name_args=['job_name'],
            time_args=['wall_clock_limit'],
            time_formats=['%H:%M:%S'],
            stdout_args=['output'],
            stderr_args=['error'],
            directory_args=['initialdir'],
            arg_regex=['(?<=[\ \t])(?P<arg>.+?)[\ \t]*=[\ \t]*(?P<val>.+?)[\ \t]*$'],
            flag_regex=['^#@[\ \t]+(?P<arg>[^=\ ]+?)[\ \t]*$'],
            arg_format=['%s = %s'],
            flag_format=['%s'],
        ),
        # Add other workload managers here if needed.
        # Lists have to be of the same length. Use None to fill missing values.
        # Regex expressions are applied to the complete line including the directive
        # Capture groups must be named 'arg' and 'val' for the arg_regex and 'arg' for the flag_regex
    }

    def __init__(self, file, name, directory, time, stdout, stderr, params, manager):
        self.file = file
        self.name = name
        self.directory = directory
        self.time = time
        self.stdout = stdout
        self.stderr = stderr
        self.params = tuple(sorted(params, key=lambda x: x[0]))
        self.manager = manager

    def __hash__(self):
        return hash((self.manager, self.params))

    def __eq__(self, other):
        return (self.manager, self.params) == (other.manager, other.params)

    def __ne__(self, other):
        return not (self == other)

    def to_string(self):
        m = Job.managers[self.manager]

        def dformat(arg, val, can_be_flag=False):
            if val is None:
                if can_be_flag:
                    return m.directive + ' ' + (m.flag_format[0] % arg) + '\n'
                else:
                    return ''  # exclude
            else:
                return m.directive + ' ' + (m.arg_format[0] % (arg, val)) + '\n'

        ret = '#!/bin/bash -x\n'
        ret += dformat(m.name_args[0], self.name)
        ret += dformat(m.time_args[0], Job.str_from_timedelta(self.time, m.time_formats[0]))
        ret += dformat(m.directory_args[0], self.directory)
        ret += dformat(m.stdout_args[0], self.stdout)
        ret += dformat(m.stderr_args[0], self.stderr)

        for key, value in self.params:
            ret += dformat(key, value, can_be_flag=True)

        return ret

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
        if workload_manager is not None:
            try:
                manager = Job.managers[workload_manager]
                print('Using workload manager: %s' % manager.name)
            except KeyError:
                raise ValueError('Workload manager not supported: %s' % workload_manager)
        else:
            manager = None

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
                                print('Inferred workload manager: %s' % manager.name)
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
                    arg = match.group('arg')
                    try:
                        val = match.group('val')
                    except IndexError:
                        val = None

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

        if manager is None:
            raise ValueError('`%s` is not a supported job file' % job_file)

        return cls(abs_path(job_file), name, directory, time, stdout, stderr, params, manager.name)


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
    parser_queue.add_argument('--no-dispatch', action='store_true', help='Only create the combined scripts but do not'
                                                                         ' dispatch them to the queue')
    parser_queue.add_argument('-d', '--directory', default='scripts', help='Directory to store the combined scripts in'
                                                                           ' [default: %(default)s]')
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
    return path.dirname(abs_path(file))


def abs_path(file):
    return path.realpath(path.expandvars(path.expanduser(file)))


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


def combine(jobs):
    assert len(jobs) > 0

    # all scripts have params and manager in common or they would not be combinable
    params = jobs[0].params
    manager = jobs[0].manager

    # properties of the combined job
    time = timedelta()
    for job in jobs:
        time += job.time
    stdout = 'job.out'
    stderr = 'job.err'

    # find longest common substring of the names
    best_match = jobs[0].name
    for job in jobs:
        match = SequenceMatcher(None, job.name, best_match) \
            .find_longest_match(0, len(job.name), 0, len(best_match))
        best_match = jobs[0].name[match.a:match.a + match.size]
    name = best_match if best_match.strip() != '' else 'Job'

    c_job = Job(None, name, None, time, stdout, stderr, params, manager)

    # create script for combined job that calls every original script in its working directory
    c_script = ''
    for job in jobs:
        c_script += 'cd "%s"\n' % job.directory  # change to working directory
        c_script += '"%s"' % job.file  # execute script (file path is absolute)
        if job.stdout is not None:
            c_script += ' >%s' % stdout  # pipe stdout
        if job.stderr is not None:
            c_script += ' 2>%s' % stderr # pipe stderr
        c_script += '\n\n'

    return c_job, c_script


def partition(jobs, tmax, tmin, n):
    # TODO implement
    return [jobs]


def queue(args):
    current_jobs = load(args.storage_file)

    dir_counter = 0

    for similar_jobs in current_jobs.values():
        # partition jobs based on constraints
        part = partition(similar_jobs, args.max_time, args.min_time, args.parallel)
        # combine scripts in same partition
        combined = map(combine, part)

        # create separate sub folder for each script and write them to files
        for job, script in combined:
            script_dir = abs_path(path.join(args.directory, '%02i' % dir_counter))
            dir_counter += 1
            os.makedirs(script_dir, exist_ok=True)

            job.file = path.join(script_dir, 'submit.job')
            job.directory = script_dir

            # write directives and combined script to file
            with open(job.file, 'w+') as f:
                f.write(job.to_string())
                f.write('\n')
                f.write(script)

            if not args.no_dispatch:
                # TODO dispatch script
                # os.system(Job.managers[job.manager].dispatch_command)
                pass


def add(args):
    current_jobs = load(args.storage_file)

    job = Job.from_file(args.job_file, args.workload_manager)
    current_jobs[job].append(job)

    store(args.storage_file, current_jobs)
    print('Added new entry')


def status(args):
    jobs = load(args.storage_file)
    n_jobs = sum([len(v) for v in jobs.values()])

    times = []
    for k, v in jobs.items():
        time_format = Job.managers[k.manager].time_formats[0]
        time_sum = timedelta()
        for job in v:
            time_sum += job.time
        times.append(Job.str_from_timedelta(time_sum, time_format))

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
