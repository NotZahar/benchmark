cmake_minimum_required(VERSION 3.28)

project("zmq_capnproto")
set(ZMQ_PUBLISHER "${PROJECT_NAME}_publisher")
set(ZMQ_SUBSCRIBER "${PROJECT_NAME}_subscriber")

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)
pkg_check_modules(ZMQ REQUIRED libzmq)

find_package(CapnProto REQUIRED)

find_program(CAPNP_EXECUTABLE capnp)

set(CAPNP_GEN_DIR ${CMAKE_CURRENT_BINARY_DIR})
set(CAPNP_HDR ${CAPNP_GEN_DIR}/Payload.capnp.h)
set(CAPNP_SRC ${CAPNP_GEN_DIR}/Payload.capnp.c++)

add_custom_command(
    OUTPUT ${CAPNP_HDR} ${CAPNP_SRC}
    COMMAND ${CAPNP_EXECUTABLE} compile -oc++:${CAPNP_GEN_DIR} --src-prefix=${CMAKE_CURRENT_SOURCE_DIR}/proto ${CMAKE_CURRENT_SOURCE_DIR}/proto/Payload.capnp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/proto/Payload.capnp
    COMMENT "Generating Cap'n Proto C++ code"
)

add_custom_target(generate_capnp ALL DEPENDS ${CAPNP_HDR} ${CAPNP_SRC})

add_executable(${ZMQ_PUBLISHER} src/publisher.cc ${CAPNP_SRC})
add_executable(${ZMQ_SUBSCRIBER} src/subscriber.cc ${CAPNP_SRC})

add_dependencies(${ZMQ_PUBLISHER} generate_capnp)
add_dependencies(${ZMQ_SUBSCRIBER} generate_capnp)

foreach(TARGET ${ZMQ_PUBLISHER} ${ZMQ_SUBSCRIBER})
    target_include_directories(${TARGET} PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CAPNP_GEN_DIR}
        ${ZMQ_INCLUDE_DIRS}
        ${CAPNP_INCLUDE_DIRS}
    )

    target_link_libraries(${TARGET} PRIVATE
        ${ZMQ_LIBRARIES}
        yaml-cpp
        ${CAPNP_LIBRARIES}
    )

    set(EXTRA_COMPILER_FLAGS -Wall -Wextra -Wconversion -Wshadow -Wpedantic -Werror)
    target_compile_options(${TARGET} PRIVATE ${EXTRA_COMPILER_FLAGS})
endforeach()
