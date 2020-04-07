import sys
import os
import sgtk

def execute(
    plugin_path,
    software_plugin,
    app_path,
    app_args,
    version,
    engine_name,
    software_entity,
    **kwargs
):
    # There may be a better way of doing this, but you can't use
    # `__file__` in the `userSetup.py` so we are getting the current
    # plugin location here and setting it in an env var so that the
    # `userSetup.py` can access it when it runs.
    os.environ["STUDIO_LIBRARY_PATH"] = plugin_path
    
    # Append the root plugin path to the PYTHONPATH env var
    # so that the userSetup.py file will be run when Maya 
    # launches.
    sgtk.util.append_path_to_env_var("PYTHONPATH", plugin_path)