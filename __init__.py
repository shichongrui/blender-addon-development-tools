bl_info = {
  "name": "Addon Development Tools",
  "description": "Tools to help in the development of an addon.",
  "author": "Matthew Sessions",
  "version": (1, 0, 0),
  "blender": (2, 79, 0),
  "location": "Addons > Addon Development Tools > Preferences",
  "category": "Development"
}

#Load eggs
import sys, os, bpy
path_to_watchdog = bpy.utils.script_path_user() + "\\addons\\" + __package__ + "\\modules\\watchdog-0.8.3-py3.6.egg"
path_to_pathtools = bpy.utils.script_path_user() + "\\addons\\" + __package__ + "\\modules\\pathtools-0.1.2-py3.6.egg"

if path_to_watchdog not in sys.path:
  sys.path.append(path_to_watchdog)
if path_to_pathtools not in sys.path:
  sys.path.append(path_to_pathtools)

import shutil, importlib
from bpy.types import AddonPreferences, Operator
from bpy.props import StringProperty, BoolProperty
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

observer = None

# Addon preference allows for selecting an addon to work on shows
# active updates to the current addon in development
class DevelopmentToolsPreferences(AddonPreferences):
  bl_idname = __name__

  error_message = StringProperty(
    name = 'Errors'
  )

  addon_path = StringProperty(
    name = 'Addon Path',
    description = 'Select the folder of the addon you wish to work on',
    subtype = 'DIR_PATH',
  )

  logging_message = StringProperty(
    name = 'Logging Message',
    description = 'The current message to show to the user for logging purposes'
  )

  is_running = BoolProperty(
    default=False
  )

  def draw(self, context):
    layout = self.layout

    if self.error_message:
      layout.label(text=self.error_message, icon="ERROR")

    if self.is_running:
      layout.label(text="Watching " + self.addon_path, icon="CONSOLE")

    if self.logging_message:
       layout.label(text=self.logging_message)

    if self.is_running != True:
      layout.prop(self, 'addon_path')
    
    if self.is_running:
      layout.operator('development_tools.stop')
    else:
      layout.operator('development_tools.start')

# Start the development tools including a file watcher on
# the addon original files
class DevelopmentToolsStart(Operator):
  bl_idname = 'development_tools.start'
  bl_label = 'Start addon development tools'

  def execute(self, context):
    preferences = context.user_preferences.addons[__name__].preferences
    preferences.error_message = ''

    if preferences.addon_path == '':
      preferences.error_message = 'No addon selected'
      return {'CANCELLED'}
    
    try:
      perform_copy(preferences.addon_path)
    except OSError as error:
      print(error)
      preferences.error_message = str(error)
    bpy.ops.wm.addon_refresh()

    abs_path = bpy.path.abspath(preferences.addon_path)

    global observer
    observer = Observer()
    observer.schedule(
      DeveloperToolsEventHandler(), 
      path = abs_path,
      recursive = True
    )
    observer.start()

    preferences.is_running = True
    preferences.logging_message = ''
    
    bpy.ops.wm.addon_expand(module=__name__)
    return {'FINISHED'}

# Stop the development tools and the file watcher
class DevelopmentToolsStop(Operator):
  bl_idname = 'development_tools.stop'
  bl_label = 'Stop addon development tools'

  def execute(self, context):
    preferences = context.user_preferences.addons[__name__].preferences
    global observer
    observer.stop()

    preferences.is_running = False
    preferences.logging_message = ''
    return {'FINISHED'}

# Handle file update events
class DeveloperToolsEventHandler(FileSystemEventHandler):
  def on_any_event(self, event):
    preferences = bpy.context.user_preferences.addons[__name__].preferences
    preferences.logging_message = 'Detected change in ' + event.src_path + '. Syncing...'
    perform_copy(preferences.addon_path)

# enable the in development addon
def enable_addon(addon_path):
  addon_module_name = get_addon_module_name(addon_path)
  bpy.ops.wm.addon_enable(module = addon_module_name)

# disable the in development addon
def disable_addon(addon_path):
  addon_module_name = get_addon_module_name(addon_path)
  if addon_module_name in bpy.context.user_preferences.addons:
    bpy.ops.wm.addon_disable(module = addon_module_name)
  
# determine what the addon module will be called
def get_addon_module_name(addon_path):
  abs_path = bpy.path.abspath(addon_path)
  addon_module_name = abs_path.split('\\')[-2]
  return "__dev__" + addon_module_name

# copy the entire addon directory into the blender addon directory
def copy_addon(addon_path):
  abs_path = bpy.path.abspath(addon_path)
  addon_module_name = get_addon_module_name(addon_path)
  destination = bpy.utils.script_path_user() + "\\addons\\" + addon_module_name

  if os.path.exists(destination):
    shutil.rmtree(destination)
  shutil.copytree(abs_path, destination)

# In order to get blender to pick up the changes to files
# we need to reload all of the addon modules
def reload_addon_modules(addon_path):
  addon_module_name = get_addon_module_name(addon_path)
  for module_name in sys.modules.keys():
    if module_name.startswith(addon_module_name):
      importlib.reload(sys.modules[module_name])

# helper to perform all necessary steps when a change happens
def perform_copy(addon_path):
  disable_addon(addon_path)
  copy_addon(addon_path)
  reload_addon_modules(addon_path)
  enable_addon(addon_path)


def register():
  bpy.utils.register_module(__name__)

# make sure we stop the file watcher when the addon is disabled or removed
def unregister():
  global observer
  if observer != None:
    observer.stop()

  bpy.utils.unregister_module(__name__)