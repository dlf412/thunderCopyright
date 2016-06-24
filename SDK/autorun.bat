@echo off
echo begin patch...

:set "Ymd=%date:~,4%%date:~5,2%%date:~8,2%"
:md thunder_cc_sdk_1.0.0.0_testtool_%ymd%
:md thunder_cc_sdk_1.0.0.0

copy /y vcri\vcri.h thunder_ci_sdk_v1.0.0.0
copy /y release\vcri.dll thunder_ci_sdk_v1.0.0.0
copy /y release\vcri.lib thunder_ci_sdk_v1.0.0.0
copy /y release\json_c.dll thunder_ci_sdk_v1.0.0.0
copy /y release\libcurl.dll thunder_ci_sdk_v1.0.0.0
copy /y release\ssleay32.dll thunder_ci_sdk_v1.0.0.0
copy /y release\libeay32.dll thunder_ci_sdk_v1.0.0.0

copy /y release\json_c.dll thunder_ci_sdk_testtool_v1.0.0.0
copy /y release\libcurl.dll thunder_ci_sdk_testtool_v1.0.0.0
copy /y release\ssleay32.dll thunder_ci_sdk_testtool_v1.0.0.0
copy /y release\libeay32.dll thunder_ci_sdk_testtool_v1.0.0.0
copy /y release\vcri.dll thunder_ci_sdk_testtool_v1.0.0.0
copy /y release\vcri.pdb thunder_ci_sdk_testtool_v1.0.0.0
copy /y debug\vcri.dll thunder_ci_sdk_testtool_v1.0.0.0\vcri_debug.dll
copy /y debug\vcri.pdb thunder_ci_sdk_testtool_v1.0.0.0\vcri_debug.pdb
copy /y release\SDK_TOOL.exe thunder_ci_sdk_testtool_v1.0.0.0

echo finish,remember add CA signiture...
pause