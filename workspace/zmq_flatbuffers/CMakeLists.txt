cmake_minimum_required(VERSION 3.28)

project("zmq_flatbuffers")
set(ZMQ_PUBLISHER "${PROJECT_NAME}_publisher")
set(ZMQ_SUBSCRIBER "${PROJECT_NAME}_subscriber")
include("${CMAKE_CURRENT_SOURCE_DIR}/../cmake/CompilerWarnings.cmake")

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)
pkg_check_modules(ZMQ REQUIRED libzmq)

find_program(FLATC flatc REQUIRED)
set(FBS_FILE "${CMAKE_CURRENT_SOURCE_DIR}/flat/Payload.fbs")
set(FBS_GENERATED "${CMAKE_CURRENT_BINARY_DIR}/flat/Payload_generated.h")
add_custom_command(
  OUTPUT ${FBS_GENERATED}
  COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_BINARY_DIR}/flat
  COMMAND ${FLATC} --cpp -o ${CMAKE_CURRENT_BINARY_DIR}/flat ${FBS_FILE}
  DEPENDS ${FBS_FILE}
  COMMENT "Generating FlatBuffers C++ headers")

add_executable(${ZMQ_PUBLISHER})
target_sources(${ZMQ_PUBLISHER} PRIVATE src/publisher.cc ${FBS_GENERATED})

add_executable(${ZMQ_SUBSCRIBER})
target_sources(${ZMQ_SUBSCRIBER} PRIVATE src/subscriber.cc ${FBS_GENERATED})

target_include_directories(
  ${ZMQ_PUBLISHER} PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
                          ${CMAKE_CURRENT_BINARY_DIR} ${ZMQ_INCLUDE_DIRS})
target_include_directories(
  ${ZMQ_SUBSCRIBER}
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
         ${CMAKE_CURRENT_BINARY_DIR} ${ZMQ_INCLUDE_DIRS})

target_link_libraries(${ZMQ_PUBLISHER} PUBLIC ${ZMQ_LIBRARIES} yaml-cpp)
target_link_libraries(${ZMQ_SUBSCRIBER} PUBLIC ${ZMQ_LIBRARIES} yaml-cpp)

target_enable_benchmark_warnings(${ZMQ_PUBLISHER})
target_enable_benchmark_warnings(${ZMQ_SUBSCRIBER})
