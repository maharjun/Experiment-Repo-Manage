from setuptools import setup, find_packages
setup(
    name="RepoManagement",
    version="0.1.1",
    packages=['RepoManagement'],
    author="Arjun Rao",
    author_email="arjun210493@gmail.com",
    description="This is an Example Package",
    license="MIT",
    keywords="Experiment Repository Management",
    install_requires=['colorama','pyyaml','gitpython','colorclass','terminaltables'],
    entry_points={
        'console_scripts':[
            'rmanager = RepoManagement.RManager:run_console_main'
        ]
    }
)
