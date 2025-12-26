cmake_minimum_required(VERSION 3.16)

# 从 version.yaml 读取插件版本
set(VERSION_FILE "${CMAKE_CURRENT_SOURCE_DIR}/../../version.yaml")
if(EXISTS "${VERSION_FILE}")
    file(STRINGS "${VERSION_FILE}" VERSION_LINE REGEX "^addon_version:")
    if(VERSION_LINE)
        string(REGEX MATCH "[0-9]+\\.[0-9]+\\.[0-9]+" ADDON_VERSION "${VERSION_LINE}")
        if(NOT ADDON_VERSION)
            set(ADDON_VERSION "0.1.0")
        endif()
    else()
        set(ADDON_VERSION "0.1.0")
    endif()
else()
    set(ADDON_VERSION "0.1.0")
endif()

message(STATUS "Addon version: ${ADDON_VERSION}")
project(fcitx5-nextalk VERSION ${ADDON_VERSION})

# 查找 Fcitx5
find_package(Fcitx5Core 5.0.0 REQUIRED)
find_package(Fcitx5Utils REQUIRED)

# 包含 Fcitx5 宏
include("${FCITX_INSTALL_CMAKECONFIG_DIR}/Fcitx5Utils/Fcitx5CompilerSettings.cmake")

# 设置 C++ 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 添加 Fcitx5 addon
add_library(nextalk MODULE
    src/nextalk.cpp
)

# Keep default "lib" prefix for consistency with other Fcitx5 addons
# Output: libnextalk.so

target_link_libraries(nextalk
    Fcitx5::Core
    Fcitx5::Utils
)

target_include_directories(nextalk PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# 安装 addon 库
install(TARGETS nextalk DESTINATION "${FCITX_INSTALL_ADDONDIR}")

# 生成并安装配置文件
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/src/nextalk.conf.in"
    "${CMAKE_CURRENT_BINARY_DIR}/nextalk.conf"
    @ONLY
)

install(
    FILES "${CMAKE_CURRENT_BINARY_DIR}/nextalk.conf"
    DESTINATION "${FCITX_INSTALL_PKGDATADIR}/addon"
    PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ
)

message(STATUS "Fcitx5 addon dir: ${FCITX_INSTALL_ADDONDIR}")
message(STATUS "Fcitx5 pkgdata dir: ${FCITX_INSTALL_PKGDATADIR}")
