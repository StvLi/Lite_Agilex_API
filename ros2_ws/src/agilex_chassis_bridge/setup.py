from setuptools import find_packages, setup

package_name = "agilex_chassis_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/rviz", ["rviz/chassis_map.rviz"]),
    ],
    install_requires=["setuptools", "PyYAML", "requests", "websockets", "Pillow", "numpy"],
    zip_safe=True,
    maintainer="stvli",
    maintainer_email="stvli@example.com",
    description="ROS2 bridge for AgileX chassis HTTP/WS API.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "chassis_bridge = agilex_chassis_bridge.chassis_bridge_node:main",
        ],
    },
)
