# cpp/CMakeLists.txt -- single build file for the whole C++ side (for now).
cmake_minimum_required(VERSION 3.16)
project(battle_city CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- the SDL2 player ---
add_executable(play app/main.cpp)

target_include_directories(play PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/app)

# SDL2 stack via pkg-config (MSYS2 provides the .pc files).
find_package(PkgConfig REQUIRED)
pkg_check_modules(SDL2       REQUIRED sdl2)
pkg_check_modules(SDL2_IMAGE REQUIRED SDL2_image)
pkg_check_modules(SDL2_MIXER REQUIRED SDL2_mixer)
pkg_check_modules(SDL2_TTF   REQUIRED SDL2_ttf)

target_include_directories(play PRIVATE
    ${SDL2_INCLUDE_DIRS} ${SDL2_IMAGE_INCLUDE_DIRS}
    ${SDL2_MIXER_INCLUDE_DIRS} ${SDL2_TTF_INCLUDE_DIRS})
target_link_directories(play PRIVATE
    ${SDL2_LIBRARY_DIRS} ${SDL2_IMAGE_LIBRARY_DIRS}
    ${SDL2_MIXER_LIBRARY_DIRS} ${SDL2_TTF_LIBRARY_DIRS})
target_link_libraries(play PRIVATE
    ${SDL2_LIBRARIES} ${SDL2_IMAGE_LIBRARIES}
    ${SDL2_MIXER_LIBRARIES} ${SDL2_TTF_LIBRARIES})

target_compile_options(play PRIVATE -Wall -Wextra)