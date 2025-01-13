from pathlib import Path
from typing import Union,Optional, List
import logging
from dataclasses import dataclass

from pandas import to_datetime

from ruamel.yaml import YAML

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S%z"

@dataclass
class GitConfig():
    """
    A class for storing the git configuration for a package.
    """
    repo_name : Optional[str] = None
    branch : Optional[str] = None
    commit : Optional[str] = None
    commit_time : Optional[str] = None
    commit_hash : Optional[str] = None
    package : Optional[str] = None
    executable : Optional[Union[str,List[str]]] = None

class GitValidatedMixin():
    """
    A mixin for ROS interpreters that validates the git commit
    corresponding to the data being logged and ensures it's
    compatible with the interpreter.
    """

    git_config : Union[GitConfig, List[GitConfig]] = []

    def __init__(self, file_path : Union[str, Path], warn : bool = False, *args, **kwargs):
        if not hasattr(self.__class__, 'git_config'):
            logging.warn(
                f"""
                {self.__class__.__name__} does not have a git_config attribute,
                despite using a GitValidated mixin.
                Cannot validate git state.
                To fix, implement a class attribute git_config of type GitConfig.
            """ )
        try:
            self.validate_git(file_path)
        except Exception as e:
            logging.error(f"""
                Error validating git state for {file_path}.\n
                {e}
            """)
        super().__init__(file_path, *args, **kwargs)

    def validate_git(self, file_path : Union[str, Path]):
        """
        Validates the git information file for the interpreter.
        """

        if isinstance(file_path, str):
            file_path = Path(file_path)

        # look for a file that ends in the right extension
        # and contains the file name with "_git_state"
        putative_gits = file_path.parent.glob('*_git_state*')
        putative_gits = [
            p for p in putative_gits
            if (p.suffix == '.yaml') and not (p.name.startswith('._'))
        ]
        if len(putative_gits) == 0:
            # try the current path just in case
            putative_gits = file_path.glob('_git_state*')
            putative_gits = [
                p for p in putative_gits
                if (p.suffix == '.yaml') and not (p.name.startswith('._'))
            ]
            if len(putative_gits) == 0:
                logging.info(f"""
                    No git state file found for {file_path}.\n
                    Cannot guarantee compatibility with the data.
                """)
                return
        if len(putative_gits) > 1:
            logging.info(f"""
                Multiple git state files found for {file_path}:\n
                {putative_gits}
                Cannot guarantee compatibility with the data.
            """)
        git_file = putative_gits[0]

        # load the git state file
        git_yaml = YAML()
        git_state = git_yaml.load(git_file)

        git_configs = self.__class__.git_config
        if not isinstance(git_configs, list):
            git_configs = [git_configs]

        # Find the executable for this interpreter class,
        # store a list of tuples, one with the data from the
        # .yaml file that matches at least one GitConfig for
        # this class, and one which is the corresponding GitConfig
        config = [
            (
                config_data,
                next(
                    conf
                    for conf in git_configs
                    if conf.package == config_data['package']
                )
            )
            for node_name, config_data in git_state.items()
            if 
                'package' in config_data and
                any(
                    config_data['package'] == conf.package
                    for conf in git_configs
                )
        ]
        
        if len(config) == 0:
            logging.info(f"""
                No git package found for {file_path} with a compatible
                node for a {self.__class__.__name__}.\n
                Cannot guarantee compatibility with the data.
            """)
            return
        
        warn_string = ""
        for c in config:
            new_warn = is_valid_git(*c)
            if len(new_warn):
                warn_string += new_warn+"\n"
        
        if len(warn_string)>0:    
            logging.info(f"""
                At least one invalid or incompatible git state found for
                {file_path} interpreter {self.__class__.__name__}:\n
                {warn_string}
            """)
        

def is_valid_git(config_from_yaml, git_config : GitConfig)->str:
    ret_string = ""
    if to_datetime(
        config_from_yaml['commit_time'],
        format = DATETIME_FORMAT
        ) > to_datetime(
            git_config.commit_time,
            format = DATETIME_FORMAT
        ):
        ret_string += """
            Git commit time is more recent than the last time
            this interpreter's compatibility has been validated
            against it. This may indicate that the interpreter
            will incorrectly analyze the data contained.\n
        """

    executables = git_config.executable
    if not isinstance(executables, list):
        executables = [executables]
    if config_from_yaml['executable'] not in executables:
        ret_string += f"""
            The executable {config_from_yaml['executable']} is not
            one for which this interpreter has been validated.\n
        """

    return ret_string

class GitValidatedUpOneLevelMixin(GitValidatedMixin):
    """ For files one directory removed from the git """

    def validate_git(self, file_path : Union[str, Path]):
        """
        Validates the git information file for the interpreter.
        """

        file_path = Path(file_path).parent
        GitValidatedMixin.validate_git(self, file_path)

        


        

