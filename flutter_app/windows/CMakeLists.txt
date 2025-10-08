# The Flutter tooling requires that developers have a version of Visual Studio
# installed that includes CMake 3.14 or later. You should not increase this
# version, as doing so will cause the Flutter tooling to not be able to run
# your application.
cmake_minimum_required(VERSION 3.14)

# Project-level configuration.
set(PROJECT_NAME "scandy_desktop")
set(APPLICATION_ID "com.scandy.desktop")

# Use Unicode for all projects.
add_definitions(-DUNICODE -D_UNICODE)

# Define the application target. To change its name, change APPLICATION_ID above
# and update the call to set_target_properties below.
add_executable(${PROJECT_NAME} WIN32)

# Specify the source files.
target_sources(${PROJECT_NAME} PRIVATE
  "runner/main.cpp"
  "runner/flutter_window.cpp"
  "runner/utils.cpp"
  "runner/win32_window.cpp"
  "runner/resource.h"
  "runner/app.rc"
  "runner/app_icon.ico"
)

# Include the Flutter library's headers.
target_include_directories(${PROJECT_NAME} PRIVATE
  "${FLUTTER_INCLUDE_DIR}")

# Link the Flutter library.
target_link_libraries(${PROJECT_NAME} PRIVATE flutter flutter_wrapper_app)

# Enable UWP-style handling of Windows runtime APIs.
target_link_libraries(${PROJECT_NAME} PRIVATE "dwmapi.lib")

# Use the default Windows version.
target_compile_definitions(${PROJECT_NAME} PRIVATE "WIN32_LEAN_AND_MEAN")

# Run the Flutter tool portions of the build. This must not be removed.
set(FLUTTER_TARGET_PLATFORM windows)
include(flutter/generated_plugin_registrant.cmake)
