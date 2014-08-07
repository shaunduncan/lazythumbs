import lazythumbs
from setuptools import setup, find_packages

setup(
    name='lazythumbs',
    version=lazythumbs.__version__,
    description='render-on-request image manipulation for django',
    author='Nathaniel K Smith',
    author_email='nathanielksmith@gmail.com',
    license='BSD',
    url='https://github.com/coxmediagroup/lazythumbs',
    packages=find_packages(exclude=['tests', 'tests.*']),
    platforms='any',
    install_requires=["Django", "Pillow"],
    zip_safe=False,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Multimedia :: Graphics',
        'Framework :: Django',
    ],
)

