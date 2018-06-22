from setuptools import setup, find_packages

setup(
    name='md-perfmod',
    version='0.1',
    packages=find_packages(),
    url='https://github.com/ssauermann/md-perfmod',
    license='MIT',
    author='Sascha Sauermann',
    author_email='saschasauermann@gmx.de',
    description='Tools for benchmarking md simulations as well as modeling and visualizing the performance thereof.',
    # scripts=['bin/script'],
    entry_points={
        'console_scripts': [
            'job-combine = job_combine.job_combine:main',
            'csv2extrap = md_perfmod.csv2extrap:main',
        ],
    },
)
