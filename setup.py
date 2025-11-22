from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'av_recorder'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('av_recorder/launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Nathan Tsoi',
    maintainer_email='nathan@vertile.com',
    description='AV Recorder',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'bag_recorder = av_recorder.bag_recorder:main',
        ],
    },
)
