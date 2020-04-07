# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Before App Launch Hook

This hook is executed prior to application launch and is useful if you need
to set environment variables or run scripts as part of the app initialization.
"""

import os
import sys
import shutil
import imp


import sgtk
from sgtk.util.zip import unzip_file


class BeforeAppLaunch(sgtk.Hook):
    """
    Hook to set up the system prior to app launch.
    """

    def execute(
        self, app_path, app_args, version, engine_name, software_entity=None, **kwargs
    ):
        """
        The execute function of the hook will be called prior to starting the required application

        :param app_path: (str) The path of the application executable
        :param app_args: (str) Any arguments the application may require
        :param version: (str) version of the application being run if set in the
            "versions" settings of the Launcher instance, otherwise None
        :param engine_name (str) The name of the engine associated with the
            software about to be launched.
        :param software_entity: (dict) If set, this is the Software entity that is
            associated with this launch command.
        """

        if engine_name == "tk-maya":
            ### Load Maya Environments
            tank.util.append_path_to_env_var("MAYA_PLUG_IN_PATH", "/sg/maya_plugins1:/sg/maya_plugins2")
            tank.util.append_path_to_env_var("MAYA_UI_LANGUAGE", "zh_CN")
            print(version)
            #QtGui.QMessageBox.information(None, "Hello", str(version))

            # you can set environment variables like this:
            # os.environ["MAYA_PLUG_IN_PATH"] = "/sg/maya_plugins1:/sg/maya_plugins2"
            # os.environ["MAYA_UI_LANGUAGE"] = zh_CN"

            
        # Check that we have a software entity, and that it has some plugins.
        if software_entity is not None and software_entity["sg_software_plugins"]:
            # Store a handy reference to the Shotgun API
            self.sg = self.parent.shotgun

            # Get the root folder where the plugins will be downloaded to.
            plugin_root_folder = self.get_plugin_root(software_entity)
            # Make sure the plugin folder is created.
            self.parent.ensure_folder_exists(plugin_root_folder)
            self.logger.debug("Plugin root folder: %s" % plugin_root_folder)

            # We should have a list of software plugins stored on the Software entity.
            # However we need to do an additional SG find to get the payload field for each.
            plugin_filters = [ ["id", "is", plugin["id"]] for plugin in software_entity["sg_software_plugins"]]
            filters = [
                {
                    "filter_operator": "any",
                    "filters": plugin_filters
                }
            ]

            software_plugins = self.sg.find("CustomNonProjectEntity06", filters, ["sg_payload","code"])
            self.logger.debug("software_plugins: %s" % software_plugins)

            # Now loop over the plugins and download them and setup them up.
            for software_plugin in software_plugins:
                plugin_version_folder = self.download_plugin(software_plugin, plugin_root_folder)

                if plugin_version_folder is not None:
                    self.run_plugin_setup(
                        plugin_version_folder,
                        software_plugin,
                        app_path,
                        app_args,
                        version,
                        engine_name,
                        software_entity,
                        **kwargs
                    )

    def get_plugin_root(self, software_entity):
        # Get a location to save the plugins to
        plugin_root_folder = os.environ.get("SOFTWARE_PLUGIN_ROOT")
        if plugin_root_folder is None:
            # If no root folder was provided via an environment variable attempt to get a folder in the user dir.
            plugin_root_folder = os.path.join(self.parent.site_cache_location,
                                              "plugins",
                                              software_entity["code"])
        return plugin_root_folder

    def run_plugin_setup(
            self,
            plugin_version_folder,
            software_plugin,
            app_path,
            app_args,
            version,
            engine_name,
            software_entity,
            **kwargs
    ):
        # We expect to find a sg_setup.py file in the root of the plugin folder
        # with an execute method accepting software_plugin, app_path, app_args,
        # version, engine_name, software_entity, **kwargs.
        # Each plugin is responsible for ensuring it is setup in the correct way,
        # and that logic lives in the sg_setup.py

        setup_file = os.path.join(plugin_version_folder, "sg_setup.py")
        if not os.path.isfile(setup_file):
            self.logger.warning("Plugin '%s' does not contain a sg_setup.py"
                                " and so won't be setup." % software_plugin["code"])
            return

        # Import the sg_setup.py and run the execute method inside it.
        # If you're using Python 3 then you will want to use importlib.util instead
        setup = imp.load_source(software_plugin["code"] + '_sg_setup', setup_file)
        setup.execute(
            plugin_version_folder,
            software_plugin,
            app_path,
            app_args,
            version,
            engine_name,
            software_entity,
            **kwargs
        )

    def download_plugin(self, software_plugin, plugin_root_folder):
        if software_plugin["sg_payload"] is None:
            # There is no payload on the plugin to download, so skip.
            self.logger.debug("Skipping software plugin"
                              ": %s %s as there is no payload" % (software_plugin["id"],
                                                                  software_plugin["code"]))
            return

        # Get/Create folder specific to the software where we can store the plugins.
        software_folder = os.path.join(plugin_root_folder,
                                      software_plugin["code"])
        self.parent.ensure_folder_exists(software_folder)

        # Check if we have already downloaded this version.
        version_folder = os.path.join(software_folder,
                                      str(software_plugin["sg_payload"]["id"]))
        if os.path.exists(version_folder):
            # We've already downloaded this version.
            return version_folder

        # Download the payload zip
        version_temp_download_location = version_folder + ".tmp.zip"
        self.sg.download_attachment(software_plugin["sg_payload"], file_path=version_temp_download_location)
        self.logger.debug("Downloaded zip to %s" % version_temp_download_location)

        # Unzip it into a temp folder
        version_temp_unzip_location = version_folder + ".tmp"
        unzip_file(version_temp_download_location, version_temp_unzip_location)
        self.logger.debug("Unzipped it to %s" % version_temp_unzip_location)

        try:
            # We expect the zip to contain a single folder, so let find it and rename it to the version id.
            folders = os.listdir(version_temp_unzip_location)
            # Mac adds a hidden folder which we don't want to copy.
            folders.remove("__MACOSX")
            if len(folders) == 1:
                unzipped_folder = os.path.join(version_temp_unzip_location,folders[0])
                os.rename(unzipped_folder, version_folder)
            else:
                self.logger.warning("Unzipped plugin didn't contain a single folder, folders: %s" % folders)
                return
        finally:
            sgtk.util.filesystem.safe_delete_folder(version_temp_unzip_location)
            sgtk.util.filesystem.safe_delete_file(version_temp_download_location)

        return version_folder
