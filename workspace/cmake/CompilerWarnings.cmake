include(CheckCXXCompilerFlag)

function(target_enable_benchmark_warnings target)
  if(IS_DIRECTORY /usr/local/include)
    target_include_directories(${target} SYSTEM PRIVATE /usr/local/include)
  endif()

  target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Werror)

  set(optional_warning_flags
      -Wconversion
      -Wsign-conversion
      -Wshadow
      -Wformat=2
      -Wnull-dereference
      -Wdouble-promotion
      -Wcast-align
      -Wcast-qual
      -Wold-style-cast
      -Woverloaded-virtual
      -Wnon-virtual-dtor
      -Wredundant-decls
      -Wundef
      -Wimplicit-fallthrough
      -Wduplicated-cond
      -Wduplicated-branches
      -Wlogical-op
      -Wuseless-cast)

  foreach(flag IN LISTS optional_warning_flags)
    string(MAKE_C_IDENTIFIER "TB_CXX_SUPPORTS_${flag}" flag_var)
    check_cxx_compiler_flag("${flag}" "${flag_var}")
    if(${flag_var})
      target_compile_options(${target} PRIVATE "${flag}")
    endif()
  endforeach()
endfunction()
