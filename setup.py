from setuptools import setup, find_packages

setup(
    name='md-perfmod',
    version='0.2',
    packages=find_packages(),
    url='https://github.com/ssauermann/md-perfmod',
    license='MIT',
    author='Sascha Sauermann',
    author_email='saschasauermann@gmx.de',
    description='Tools for benchmarking md simulations as well as modeling and visualizing the performance thereof.',
    # scripts=['bin/script'],
    entry_points={
        'console_scripts': [
            'csv2extrap = md_perfmod.csv2extrap:main',
            'csv2model = md_perfmod.csv2model:main',
        ],
    },
)
