cmake_minimum_required(VERSION 3.16)
project(WordPet LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets Network Sql)

qt_add_executable(WordPet WIN32
    src/main.cpp
    src/petwindow.cpp
    src/vocabularywindow.cpp
    src/database.cpp
    src/clipboardmonitor.cpp
    src/dictapi.cpp
)

target_link_libraries(WordPet PRIVATE Qt6::Widgets Qt6::Network Qt6::Sql)

# Create data directory
file(MAKE_DIRECTORY ${CMAKE_SOURCE_DIR}/data)