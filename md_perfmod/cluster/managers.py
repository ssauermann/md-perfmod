"""Collection of workload managers used on clusters"""
from collections import namedtuple

WorkloadManager = namedtuple('WorkloadManager',
                             'name dispatch_command directive name_args time_args time_formats stdout_args'
                             ' stderr_args directory_args arg_regex flag_regex arg_format flag_format')

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
