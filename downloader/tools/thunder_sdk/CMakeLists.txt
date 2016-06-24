project(Downloader)
cmake_minimum_required(VERSION 2.8.7)

SET(RELEASE_MODE FALSE)

SET(LIB_TYPE SHARED)
INCLUDE(cross_cmake/cross.cmake)

IF(NOT DEFINED OS_NAME)
	SET(OS_NAME Linux)
ENDIF(NOT DEFINED OS_NAME)

SET(LIBRARY_OUTPUT_PATH ${PROJECT_BINARY_DIR}/lib)
SET(EXECUTABLE_OUTPUT_PATH ${PROJECT_BINARY_DIR}/build/demo/bin)
SET(DEBUG_FLAGS -g -D_DEBUG)
ADD_DEFINITIONS(-DLINUX)

include_directories (
	${PROJECT_SOURCE_DIR}/include
	)

aux_source_directory(./demo _demo_src_files)

set(src_files  ${_demo_src_files})

IF(NOT RELEASE_MODE)
	ADD_DEFINITIONS(-D_DEBUG)
ENDIF(NOT RELEASE_MODE)

IF(RELEASE_MODE)
	ADD_DEFINITIONS(${RELEASE_FLAGS})
ELSE(RELEASE_MODE)
	ADD_DEFINITIONS(${DEBUG_FLAGS})
ENDIF(RELEASE_MODE)

#SET(VERSION_DEFINE -DVERSION_NUM=1 -DBUILD_NUM=20)
ADD_DEFINITIONS(-D_DEBUG)


IF(RELEASE_MODE)
	SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -O0 -Wl,-Map=Downloader.map -g  -Wno-unused -fpermissive -fPIC" )
ELSE(RELEASE_MODE)
	SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS}  -O0 -Wl,-Map=Downloader.map -g  -Wno-unused -fpermissive  -fPIC" )
ENDIF(RELEASE_MODE)


##################################################################################
LINK_DIRECTORIES(
	${PROJECT_SOURCE_DIR}/lib
	${LIBRARY_OUTPUT_PATH})
#add_subdirectory(common)
#add_subdirectory(Package)
#add_subdirectory(QueryResource)

ADD_EXECUTABLE(Downloader ${_demo_src_files})
TARGET_LINK_LIBRARIES(Downloader xl_common) 
TARGET_LINK_LIBRARIES(Downloader embed_thunder) 
