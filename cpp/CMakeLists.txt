cmake_minimum_required(VERSION 3.24)
project(ElementChessCpp VERSION 0.1.0 LANGUAGES CXX)

option(EC_BUILD_CLIENT "Build the SFML graphical client" OFF)
option(EC_BUILD_TESTS "Build unit tests" ON)

add_library(elementchess_core
    src/EventBus.cpp
    src/Matchmaker.cpp
)
target_include_directories(elementchess_core PUBLIC include)
target_compile_features(elementchess_core PUBLIC cxx_std_17)

if(MSVC)
    target_compile_options(elementchess_core PRIVATE /W4 /permissive-)
else()
    target_compile_options(elementchess_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(EC_BUILD_CLIENT)
    find_package(SFML 3.1 COMPONENTS Graphics Window System Audio REQUIRED)
    add_executable(elementchess_client src/main.cpp)
    target_link_libraries(elementchess_client PRIVATE
        elementchess_core SFML::Graphics SFML::Window SFML::System SFML::Audio)
    target_compile_features(elementchess_client PRIVATE cxx_std_17)
endif()

if(EC_BUILD_TESTS)
    enable_testing()
    add_executable(elementchess_core_tests tests/core_tests.cpp)
    target_link_libraries(elementchess_core_tests PRIVATE elementchess_core)
    add_test(NAME elementchess_core_tests COMMAND elementchess_core_tests)
endif()
