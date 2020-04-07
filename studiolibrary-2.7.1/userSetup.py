# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
This file is loaded automatically by Maya at startup
It sets up the Toolkit context and prepares the tk-maya engine.
"""

import os
import sgtk
import maya.OpenMaya as OpenMaya
import maya.cmds
import maya.mel


logger = sgtk.LogManager.get_logger(__name__)


def CleanOldShelf():
    name='Custom'
    if maya.cmds.shelfLayout(name, ex=1):
        if maya.cmds.shelfLayout(name, q=1, ca=1):
            for each in maya.cmds.shelfLayout(name, q=1, ca=1):
                maya.cmds.deleteUI(each)

def InstallStudioLibraryPlugin():
    """Dragging and dropping this file into the scene executes the file."""

    srcPath = os.path.join(os.environ.get("STUDIO_LIBRARY_PATH"), 'src')
    iconPath = os.path.join(srcPath, 'studiolibrary', 'resource', 'icons', 'icon.png')

    srcPath = os.path.normpath(srcPath)
    iconPath = os.path.normpath(iconPath)

    if not os.path.exists(iconPath):
        raise IOError('Cannot find ' + iconPath)

    for path in sys.path:
        if os.path.exists(path + '/studiolibrary/__init__.py'):
            maya.cmds.warning('Studio Library is already installed at ' + path)

    command = '''
# -----------------------------------
# Studio Library
# www.studiolibrary.com
# -----------------------------------

import os
import sys
    
if not os.path.exists(r'{path}'):
    raise IOError(r'The source path "{path}" does not exist!')
    
if r'{path}' not in sys.path:
    sys.path.insert(0, r'{path}')
    
import studiolibrary
studiolibrary.main()
'''.format(path=srcPath)
    
    CleanOldShelf()

    shelf = maya.mel.eval('$gShelfTopLevel=$gShelfTopLevel')
    parent = maya.cmds.tabLayout(shelf, query=True, selectTab=True)

    maya.cmds.shelfButton(
        command=command,
        annotation='Studio Library',
        sourceType='Python',
        image=iconPath,
        image1=iconPath,
        parent=parent
    )

    OpenMaya.MGlobal.displayInfo("\n// Studio Library has been added to current shelf.")


# Fire up Toolkit and the environment engine when there's time.
maya.cmds.evalDeferred("InstallStudioLibraryPlugin()")
