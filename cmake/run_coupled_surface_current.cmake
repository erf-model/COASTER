# Regression check for passing REMORA's surface current to ERF (driver.couple_currents).
#
# The current reaches ERF through the ocean->atmosphere exchange as two lanes, Uoce and
# Voce, east and north on ERF's layout, and ERF takes its surface stress from the wind
# relative to it. Upwelling starts at rest and the wind sets the ocean moving, so after a
# few exchanges the current is small but not zero.
#
#   current   - couple_currents on: the run completes, the ocean->atmosphere exchange
#               plotfile carries Uoce and Voce, and they are not all zero
#   rest      - the same run without it: ERF's final state must differ from the current
#               run's, or the current never reached ERF's surface layer
#   one_way   - couple_currents without two-way coupling must stop at start-up
#   erf_only  - erf.use_coupled_currents without the driver option must stop at start-up,
#               rather than at the first exchange with no current to apply

foreach(_req ERF_REMORA_DRIVER_EXE ERF_REMORA_SOURCE_DIR ERF_REMORA_INPUT_FILE
             FEXTREMA_EXE FCOMPARE_EXE)
  if(NOT DEFINED ${_req})
    message(FATAL_ERROR "${_req} is required")
  endif()
endforeach()
if(NOT DEFINED ERF_REMORA_MAX_STEP)
  set(ERF_REMORA_MAX_STEP "4")
endif()
foreach(_exe "${ERF_REMORA_DRIVER_EXE}" "${FEXTREMA_EXE}" "${FCOMPARE_EXE}")
  if(NOT EXISTS "${_exe}")
    message(FATAL_ERROR "Missing executable: ${_exe}")
  endif()
endforeach()

set(_input_file "${ERF_REMORA_SOURCE_DIR}/${ERF_REMORA_INPUT_FILE}")
if(NOT EXISTS "${_input_file}")
  message(FATAL_ERROR "Missing deck: ${_input_file}")
endif()
get_filename_component(_input_name "${ERF_REMORA_INPUT_FILE}" NAME)
get_filename_component(_deck_dir "${_input_file}" DIRECTORY)

set(_work_dir "${CMAKE_CURRENT_BINARY_DIR}/coupled_surface_current")
file(REMOVE_RECURSE "${_work_dir}")
file(MAKE_DIRECTORY "${_work_dir}")

# The deck's FILE= includes resolve against the working directory
foreach(_fname "${_input_name}" "inputs_ERF" "inputs_REMORA" "input_sounding_for_ERF")
  if(NOT EXISTS "${_deck_dir}/${_fname}")
    message(FATAL_ERROR "Missing deck dependency: ${_deck_dir}/${_fname}")
  endif()
  file(COPY "${_deck_dir}/${_fname}" DESTINATION "${_work_dir}")
endforeach()

# One ocean step per atmosphere step, so every step is an exchange
set(_common_args
  "max_step=${ERF_REMORA_MAX_STEP}"
  "erf.fixed_dt=1"
  "remora.fixed_dt=1"
  "remora.ndtfast=1"
  "erf.plot_int_1=${ERF_REMORA_MAX_STEP}"
  "remora.plot_int=-1"
  "erf.check_int=-1"
  "remora.check_int=-1"
)
if(DEFINED ERF_REMORA_RRTMGP_DIR AND NOT "${ERF_REMORA_RRTMGP_DIR}" STREQUAL "")
  list(APPEND _common_args "erf.rrtmgp_file_path=${ERF_REMORA_RRTMGP_DIR}")
else()
  list(APPEND _common_args "erf.radiation_model=None")
endif()

# Run the deck in its own subdirectory. _expect is "pass", or a regular expression the
# log of a run that must fail has to match.
function(_run_case _tag _expect)
  set(_dir "${_work_dir}/${_tag}")
  file(MAKE_DIRECTORY "${_dir}")
  foreach(_fname "${_input_name}" "inputs_ERF" "inputs_REMORA" "input_sounding_for_ERF")
    file(COPY "${_work_dir}/${_fname}" DESTINATION "${_dir}")
  endforeach()
  set(_log "${_dir}/run.log")
  execute_process(
    COMMAND "${ERF_REMORA_DRIVER_EXE}" "${_dir}/${_input_name}" ${_common_args} ${ARGN}
    WORKING_DIRECTORY "${_dir}"
    OUTPUT_FILE "${_log}"
    ERROR_FILE "${_log}"
    RESULT_VARIABLE _result
  )
  file(READ "${_log}" _log_contents)
  if(_expect STREQUAL "pass")
    if(NOT _result EQUAL 0)
      message(FATAL_ERROR "Run '${_tag}' failed with exit code ${_result}\nLog: ${_log}\n${_log_contents}")
    endif()
  else()
    if(_result EQUAL 0)
      message(FATAL_ERROR "Run '${_tag}' completed but must stop.\nLog: ${_log}")
    endif()
    if(NOT _log_contents MATCHES "${_expect}")
      message(FATAL_ERROR
        "Run '${_tag}' stopped, but not with the expected message (${_expect}).\n"
        "Log: ${_log}\n${_log_contents}")
    endif()
  endif()
endfunction()

# Largest |min| or |max| of a variable in a plotfile
function(_max_abs _plotfile _var _out)
  execute_process(
    COMMAND "${FEXTREMA_EXE}" "${_plotfile}"
    OUTPUT_VARIABLE _ext
    ERROR_VARIABLE _ext_err
    RESULT_VARIABLE _ext_result
  )
  if(NOT _ext_result EQUAL 0)
    message(FATAL_ERROR "fextrema failed on ${_plotfile}\n${_ext}${_ext_err}")
  endif()
  if(NOT _ext MATCHES "${_var}[ \t]+([0-9.eE+-]+)[ \t]+([0-9.eE+-]+)")
    message(FATAL_ERROR "No ${_var} in ${_plotfile}:\n${_ext}")
  endif()
  set(_lo "${CMAKE_MATCH_1}")
  set(_hi "${CMAKE_MATCH_2}")
  string(REGEX REPLACE "^-" "" _lo "${_lo}")
  string(REGEX REPLACE "^-" "" _hi "${_hi}")
  # CMake compares numbers in floating point
  if(_lo GREATER _hi)
    set(${_out} "${_lo}" PARENT_SCOPE)
  else()
    set(${_out} "${_hi}" PARENT_SCOPE)
  endif()
endfunction()

function(_last_plotfile _dir _prefix _out)
  file(GLOB _plots "${_dir}/${_prefix}?????")
  if(NOT _plots)
    message(FATAL_ERROR "No ${_prefix} plotfile in ${_dir}")
  endif()
  list(SORT _plots)
  list(GET _plots -1 _last)
  set(${_out} "${_last}" PARENT_SCOPE)
endfunction()

# ---- current: the lanes exist and carry a current ---------------------------
_run_case("current" "pass" "driver.couple_currents=true" "driver.plot_int_exchange=1")
_last_plotfile("${_work_dir}/current" "exchange_o2a" _o2a_last)
_max_abs("${_o2a_last}" "Uoce" _uoce_max)
_max_abs("${_o2a_last}" "Voce" _voce_max)
if(_uoce_max EQUAL 0 AND _voce_max EQUAL 0)
  message(FATAL_ERROR
    "Uoce and Voce are zero everywhere in ${_o2a_last}. The wind has driven the ocean "
    "for ${ERF_REMORA_MAX_STEP} steps, so REMORA's surface current never reached the "
    "exchange.")
endif()

# ---- rest: without the current, ERF must end somewhere else -----------------
_run_case("rest" "pass")
_last_plotfile("${_work_dir}/current" "erfplt" _erf_current)
_last_plotfile("${_work_dir}/rest" "erfplt" _erf_rest)
execute_process(
  COMMAND "${FCOMPARE_EXE}" "${_erf_current}" "${_erf_rest}"
  OUTPUT_VARIABLE _cmp_out
  ERROR_VARIABLE _cmp_err
  RESULT_VARIABLE _cmp_result
)
if(_cmp_result EQUAL 0)
  message(FATAL_ERROR
    "ERF's state with the coupled current matches the run without it exactly. "
    "The current was exchanged (Uoce up to ${_uoce_max} m/s) but never changed ERF's "
    "surface stress.\n${_cmp_out}${_cmp_err}")
endif()

# ---- misconfiguration stops at start-up -------------------------------------
_run_case("one_way" "needs driver.coupling_direction = two_way"
          "driver.couple_currents=true" "driver.coupling_direction=ERFtoREMORA")
_run_case("erf_only" "Set driver.couple_currents = true"
          "erf.use_coupled_currents=1")

message(STATUS
  "Coupled surface current reached ERF: max |Uoce| ${_uoce_max}, max |Voce| ${_voce_max} m/s")
