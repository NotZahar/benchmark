cmake_minimum_required(VERSION 3.28)

project("zmq_protobuf")
set(ZMQ_PUBLISHER "${PROJECT_NAME}_publisher")
set(ZMQ_SUBSCRIBER "${PROJECT_NAME}_subscriber")

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)
pkg_check_modules(ZMQ REQUIRED libzmq)

find_package(Protobuf REQUIRED)

set(PROTO_FILE "${CMAKE_CURRENT_SOURCE_DIR}/proto/Payload.proto")
set(PROTO_GEN_DIR "${CMAKE_CURRENT_BINARY_DIR}/proto")
set(PROTO_HDR "${PROTO_GEN_DIR}/Payload.pb.h")
set(PROTO_SRC "${PROTO_GEN_DIR}/Payload.pb.cc")

add_custom_command(
  OUTPUT ${PROTO_HDR} ${PROTO_SRC}
  COMMAND ${CMAKE_COMMAND} -E make_directory ${PROTO_GEN_DIR}
  COMMAND ${Protobuf_PROTOC_EXECUTABLE} --cpp_out=${PROTO_GEN_DIR} -I
          ${CMAKE_CURRENT_SOURCE_DIR}/proto ${PROTO_FILE}
  DEPENDS ${PROTO_FILE}
  COMMENT "Generating Protobuf C++ sources")

add_executable(${ZMQ_PUBLISHER})
target_sources(${ZMQ_PUBLISHER} PRIVATE src/publisher.cc ${PROTO_SRC}
                                        ${PROTO_HDR})

add_executable(${ZMQ_SUBSCRIBER})
target_sources(${ZMQ_SUBSCRIBER} PRIVATE src/subscriber.cc ${PROTO_SRC}
                                         ${PROTO_HDR})

target_include_directories(
  ${ZMQ_PUBLISHER}
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
         ${PROTO_GEN_DIR} ${ZMQ_INCLUDE_DIRS} ${Protobuf_INCLUDE_DIRS})

target_include_directories(
  ${ZMQ_SUBSCRIBER}
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
         ${PROTO_GEN_DIR} ${ZMQ_INCLUDE_DIRS} ${Protobuf_INCLUDE_DIRS})

if(TARGET protobuf::libprotobuf)
  target_link_libraries(${ZMQ_PUBLISHER} PUBLIC ${ZMQ_LIBRARIES} yaml-cpp
                                                protobuf::libprotobuf)
  target_link_libraries(${ZMQ_SUBSCRIBER} PUBLIC ${ZMQ_LIBRARIES} yaml-cpp
                                                 protobuf::libprotobuf)
else()
  target_link_libraries(${ZMQ_PUBLISHER} PUBLIC ${ZMQ_LIBRARIES} yaml-cpp
                                                ${Protobuf_LIBRARIES})
  target_link_libraries(${ZMQ_SUBSCRIBER} PUBLIC ${ZMQ_LIBRARIES} yaml-cpp
                                                 ${Protobuf_LIBRARIES})
endif()

set(EXTRA_COMPILER_FLAGS -Wall -Wextra -Wconversion -Wshadow -Wpedantic -Werror)
target_compile_options(${ZMQ_PUBLISHER} PRIVATE ${EXTRA_COMPILER_FLAGS})
target_compile_options(${ZMQ_SUBSCRIBER} PRIVATE ${EXTRA_COMPILER_FLAGS})
