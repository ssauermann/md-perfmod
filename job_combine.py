import argparse
import pickle
from collections import namedtuple, defaultdict
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
            time_formats=['%D-%H:%M:%S', '%D-%H:%M', '%D-%H', '%H:%M:%S', '%M:%S', '%M'],
            stdout_args=['output', 'o'],
            stderr_args=['error', 'e'],
            directory_args=[None, 'D'],  # chdir long option does not exist on coolmuc?
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
        # Time formats can contain %d, %H, %M, %S for days, hours, minutes and seconds.
        # The first time format must contain s, m + s, h + m + s or d + h + m + s
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

        def dformat(args, val):
            if val is None:
                return ''  # exclude
            else:
                for ai, arg in enumerate(args):
                    if arg is not None:
                        return m.directive + ' ' + (m.arg_format[ai] % (arg, val)) + '\n'

        ret = '#!/bin/bash -x\n'
        ret += dformat(m.name_args, self.name)
        ret += dformat(m.time_args, Job.str_from_timedelta(self.time, m.time_formats[0]))
        ret += dformat(m.directory_args, self.directory)
        ret += dformat(m.stdout_args, self.stdout)
        ret += dformat(m.stderr_args, self.stderr)

        for key, arg_index, value in self.params:
            if value is None:
                ret += m.directive + ' ' + (m.flag_format[arg_index] % key) + '\n'
            else:
                ret += m.directive + ' ' + (m.arg_format[arg_index] % (key, value)) + '\n'

        return ret

    @staticmethod
    def str_to_timedelta(time_str, formats):
        """
        Converts a string representation to a time delta
        :param time_str: Time string
        :param formats: Time formats
        :return: Time delta
        """

        for f in formats:
            pattern = f.replace('%d', '(?P<d>[0-9]+)')
            pattern = pattern.replace('%H', '(?P<h>[0-9]+)')
            pattern = pattern.replace('%M', '(?P<m>[0-9]+)')
            pattern = pattern.replace('%S', '(?P<s>[0-9]+)')
            match = re.match(pattern, time_str)

            if match is None:
                continue

            def get_group(grp):
                try:
                    return match.group(grp)
                except IndexError:
                    return 0

            days = int(get_group('d'))
            hours = int(get_group('h'))
            minutes = int(get_group('m'))
            seconds = int(get_group('s'))

            return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

        raise ValueError('`%s` is not a supported time format: %s' % (time_str, ', '.join(formats)))

    @staticmethod
    def str_from_timedelta(time_delta, time_format):
        """
        Converts a time delta to a string representation
        :param time_delta: Time delta
        :param time_format: Time format
        :return: Time string
        """

        remaining_time = time_delta
        days = hours = minutes = 0

        remaining_time.total_seconds()

        if '%D' in time_format:
            days = remaining_time.days
            remaining_time -= timedelta(days=days)

        if '%H' in time_format:
            hours = int(remaining_time.total_seconds() / (60 * 60))
            remaining_time -= timedelta(hours=hours)

        if '%M' in time_format:
            minutes = int(remaining_time.total_seconds() / 60)
            remaining_time -= timedelta(minutes=minutes)

        seconds = remaining_time.total_seconds()

        formatted = time_format.replace('%D', '%02d' % days)
        formatted = formatted.replace('%H', '%02d' % hours)
        formatted = formatted.replace('%M', '%02d' % minutes)
        formatted = formatted.replace('%S', '%02d' % seconds)

        return formatted

    @staticmethod
    def sum_times(job_list):
        time = timedelta()
        for job in job_list:
            time += job.time
        return time

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
                    matches = [re.search(regex, line) for regex in manager.arg_regex + manager.flag_regex]

                    match = None
                    arg_index = None
                    # get the first successful match
                    for i, m in enumerate(matches):
                        if m is not None:
                            match = m
                            arg_index = i % len(manager.arg_regex)
                            break

                    # no valid match -> can not continue
                    if match is None:
                        raise RuntimeError('Can not process directive `%s`' % line)

                    # get matching results from capture groups; val is None for flags
                    arg = match.group('arg')
                    try:
                        val = match.group('val')
                    except IndexError:
                        val = None

                    if arg == manager.time_args[arg_index]:
                        time = Job.str_to_timedelta(val, manager.time_formats)
                    elif arg == manager.stdout_args[arg_index]:
                        stdout = val
                    elif arg == manager.stderr_args[arg_index]:
                        stderr = val
                    elif arg == manager.directory_args[arg_index]:
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
                        params.append((arg, arg_index, val))

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
    parser_queue.add_argument('--dispatch', action='store_true', help='Dispatch the combined scripts immediately after'
                                                                      ' creating them')
    parser_queue.add_argument('-d', '--directory', default='scripts', help='Directory to store the combined scripts in'
                                                                           ' [default: %(default)s]')
    parser_queue.add_argument('-t', '--max-time', help='No combined job will have a runtime longer than this value')
    parser_queue.add_argument('-m', '--min-time', help='No combined job will have a runtime with less than this value')
    parser_queue.add_argument('-p', '--parallel', default=1, type=int,
                              help='Tries to distribute the jobs equally to `p` scripts. Scripts that can not be'
                                   ' combined may increase and constraints may reduce the number of created'
                                   ' script files. [default: %(default)i]')
    parser_queue.add_argument('--break-max', action='store_true',
                              help='Break the max_time constraint instead of the min_time constraint if not both can be'
                                   ' fulfilled at the same time.')

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
    time = Job.sum_times(jobs)
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
            c_script += ' 2>%s' % stderr  # pipe stderr
        c_script += '\n\n'

    return c_job, c_script


def partition(jobs, max_time, min_time, parallel, break_max=True):
    assert len(jobs) > 0

    time_format = '%H:%M:%S'

    if max_time is None:
        tmax = timedelta.max
    else:
        tmax = Job.str_to_timedelta(max_time, [time_format])
    if min_time is None:
        tmin = timedelta()
    else:
        tmin = Job.str_to_timedelta(min_time, [time_format])

    if tmax < tmin:
        raise ValueError('Max time has to be larger than min time')

    print('\nPartitioning results for %i combinable scripts:' % len(jobs))

    # greedy balanced partitioning into n groups considering the time constraints
    def do_partition(target_n, previous=-1):
        part = []

        desc_jobs = sorted(jobs, key=lambda x: x.time)

        # create each partition and fill them with the n largest items
        for i in range(target_n):
            part.append([desc_jobs.pop(0)])

        # iterate over the remaining items and fill the largest item into the smallest partition
        for j in desc_jobs:
            smallest_part = min(part, key=lambda x: Job.sum_times(x))
            smallest_part.append(j)

        # validate time constraints
        for p in part:
            time = Job.sum_times(p)
            if time > tmax:
                if target_n >= len(jobs):
                    print('WARNING: Could not fulfill max_time = %s constraint as there exists a single script with a'
                          ' longer time.' % max_time)
                    break
                if previous == target_n + 1 and break_max:  # fluctuating around target_n and target_n + 1
                    print('WARNING: Could not fulfill both time constraints simultaneously.'
                          ' Breaking the max_time = %s constraint.' % max_time)
                    break
                return do_partition(target_n + 1, target_n)  # need more partitions
            elif time < tmin:
                if target_n == 1:
                    print(
                        'WARNING: Could not fulfill min_time = %s constraint as there are not enough combinable scripts'
                        ' to reach this time.' % min_time)
                    break
                if previous == target_n - 1 and not break_max:  # fluctuating around target_n and target_n + 1
                    print('WARNING: Could not fulfill both time constraints simultaneously.'
                          ' Breaking the min_time = %s constraint.' % min_time)
                    break
                return do_partition(target_n - 1, target_n)  # need fewer partitions

        # constraint check successful
        return part

    target_number = min(parallel, len(jobs))
    part_result = do_partition(target_number)
    if len(part_result) > parallel > 1:
        print('WARNING: Could not partition the jobs to less than %i partitions. Try relaxing the max_time'
              ' constraint.' % parallel)
    times = [Job.str_from_timedelta(Job.sum_times(p), time_format) for p in part_result]
    print('%i partitions with times: %s' % (len(part_result), ', '.join(times)))

    return part_result


def queue(args):
    current_jobs = load(args.storage_file)

    dir_counter = 0

    print('Combining scripts...')

    for similar_jobs in current_jobs.values():
        # partition jobs based on constraints
        part = partition(similar_jobs, args.max_time, args.min_time, args.parallel, args.break_max)
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

            if int(args.verbose) >= 1:
                print('Written script to %s' % job.file)
            if args.dispatch:
                if os.system(Job.managers[job.manager].dispatch_command + ' ' + job.file) == 0:
                    if int(args.verbose) >= 1:
                        print('Dispatching successful for: %s' % job.file)
    print('Done combining scripts.')


def add(args):
    current_jobs = load(args.storage_file)

    job = Job.from_file(args.job_file, args.workload_manager)
    os.chmod(job.file, os.stat(job.file).st_mode | 0o111)  # set script executable for everyone
    current_jobs[job].append(job)

    store(args.storage_file, current_jobs)
    print('Added job successfully.')


def status(args):
    jobs = load(args.storage_file)
    n_jobs = sum([len(v) for v in jobs.values()])

    times = []
    for k, v in jobs.items():
        time_format = Job.managers[k.manager].time_formats[0]
        time_sum = Job.sum_times(v)
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
