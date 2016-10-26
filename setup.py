from setuptools import setup


setup(
    name='tornado-profile-client',
    version='1.0.0',
    description='CLI client for tornado-profile',
    long_description=open('README.md').read(),
    py_modules=['tornado_profile_client'],
    install_requires=[line.strip()
                      for line in open('requirements.txt').readlines()
                      if line.strip() and not line.startswith('#')],
    entry_points={
        'console_scripts': [
            'tornado-profile-client = tornado_profile_client:main',
        ],
    }
)
