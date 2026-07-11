cmake_minimum_required(VERSION 3.8)
project(agilex_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/SaveDebugMap.srv"
  "srv/GetChassisPose.srv"
  "srv/NavigateToPose.srv"
  "srv/StartMapping.srv"
  "srv/StopMapping.srv"
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
